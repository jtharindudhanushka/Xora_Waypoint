"""Read-only loader views. Rules and quantities come from the published plan (BR-24..31)."""

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import COLOMBO, Clock, ensure_utc
from app.core.errors import ForbiddenError, NotFoundError
from app.models import Order, Plan, PlanAck, PlanVersion, Trip, User, Vehicle
from app.modules.loading.models import SHORTFALL_REASONS, Hold, Shortfall
from app.modules.loading.schemas import (
    DockChange,
    DockDay,
    DockDetail,
    DockHold,
    DockLine,
    DockTrip,
    DockVersion,
)
from app.modules.sync.models import Event


def _latest(db: Session, plan_id: uuid.UUID) -> PlanVersion | None:
    return db.scalar(
        select(PlanVersion)
        .where(PlanVersion.plan_id == plan_id, PlanVersion.status == "published")
        .order_by(PlanVersion.number.desc())
        .limit(1)
    )


def _version(db: Session, version: PlanVersion, user: User) -> DockVersion:
    acked = db.get(PlanAck, (version.id, user.id)) is not None
    return DockVersion(
        id=version.id,
        number=version.number,
        published_at=ensure_utc(version.published_at) if version.published_at else None,
        acknowledged=acked,
        needs_acknowledgement=version.parent_version_id is not None and not acked,  # BR-31
        change_reason=version.change_reason,
    )


def _hold(db: Session, trip: Trip) -> Hold | None:
    return db.scalar(select(Hold).where(Hold.trip_id == trip.id, Hold.status == "active"))


def _summary(db: Session, trip: Trip, user: User) -> DockTrip:
    vehicle = db.get(Vehicle, trip.vehicle_code)
    assert vehicle is not None
    held = _hold(db, trip) is not None
    loaded = (
        db.scalar(
            select(Event.event_id)
            .where(Event.type == "trip_loaded", Event.entity_id == str(trip.id))
            .limit(1)
        )
        is not None
    )
    return DockTrip(
        id=trip.id,
        vehicle=trip.vehicle_code,
        vehicle_type=vehicle.type,
        temperature=vehicle.temp,
        trip_no=trip.trip_no,
        district=trip.district,
        departure=trip.planned_depart,
        stops=len(trip.stops),
        cases=sum(o.planned_cases for s in trip.stops for o in s.orders),
        volume_m3=float(trip.volume_m3),
        weight_kg=float(trip.weight_kg),
        volume_cap_m3=float(vehicle.volume_cap_m3),
        weight_cap_kg=float(vehicle.weight_cap_kg),
        load_status="on_hold" if held else "loaded" if loaded else "planned",  # BR-54
        on_hold=held,
        version=_version(db, trip.version, user),
    )


def day(db: Session, clock: Clock, user: User, operating_date: date | None) -> DockDay:
    operating_date = operating_date or clock.local_now().date()
    plan = db.scalar(
        select(Plan).where(Plan.depot == user.depot, Plan.operating_date == operating_date)
    )
    version = _latest(db, plan.id) if plan else None
    trips = (
        sorted(
            version.trips,
            key=lambda t: (
                t.planned_depart is None,
                str(t.planned_depart),
                t.vehicle_code,
                t.trip_no,
            ),
        )
        if version
        else []
    )
    return DockDay(
        date=operating_date,
        depot=user.depot or "",
        dock=user.dock,
        version=_version(db, version, user) if version else None,
        trips=[_summary(db, t, user) for t in trips],
        server_time=clock.now(),
    )  # BR-25, BR-55: only the authenticated depot, ordered by departure.


def _portions(
    db: Session, version: PlanVersion
) -> dict[tuple[str, int, uuid.UUID], tuple[Trip, Order, int, bool]]:
    result = {}
    for trip in version.trips:
        for stop in trip.stops:
            for line in stop.orders:
                order = db.get(Order, line.order_id)
                assert order is not None
                result[(trip.vehicle_code, trip.trip_no, order.id)] = (
                    trip,
                    order,
                    line.planned_cases,
                    line.top_up_of_order_id is not None,
                )
    return result


def detail(db: Session, clock: Clock, user: User, identifier: uuid.UUID) -> DockDetail:
    original = db.get(Trip, identifier)
    if original is None:
        raise NotFoundError("TRIP_NOT_FOUND", "Unknown loading trip")
    if original.version.plan.depot != user.depot:
        raise ForbiddenError("OUT_OF_SCOPE", "This trip is not on your dock", rule_id="BR-55")
    version = _latest(db, original.version.plan_id)
    if version is None:
        raise NotFoundError("PLAN_NOT_PUBLISHED", "No published load for this trip")
    trip = next(
        (
            t
            for t in version.trips
            if (t.vehicle_code, t.trip_no) == (original.vehicle_code, original.trip_no)
        ),
        None,
    )
    if trip is None:
        raise NotFoundError("TRIP_REMOVED", "This trip was removed from the latest plan")
    lines = []
    for stop in sorted(trip.stops, key=lambda s: s.seq, reverse=True):  # BR-24
        for line in stop.orders:
            order = db.get(Order, line.order_id)
            assert order is not None
            lines.append(
                DockLine(
                    order_id=order.id,
                    order_ref=order.ref,
                    outlet_code=stop.outlet_code,
                    stop_seq=stop.seq,
                    cases=line.planned_cases,
                    temperature=order.temp_requirement,
                    weight_kg=round(
                        float(order.weight_kg) * line.planned_cases / max(order.units, 1), 1
                    ),
                    top_up=line.top_up_of_order_id is not None,
                )
            )
    parent = db.get(PlanVersion, version.parent_version_id) if version.parent_version_id else None
    changes = []
    if parent and _version(db, version, user).needs_acknowledgement:
        before, after = _portions(db, parent), _portions(db, version)
        affected = {line.order_id for line in lines}
        for key in sorted(before.keys() | after.keys(), key=lambda k: (k[0], k[1], str(k[2]))):
            old, new = before.get(key), after.get(key)
            old_qty, new_qty = old[2] if old else 0, new[2] if new else 0
            if old_qty == new_qty or (key[0] != trip.vehicle_code and key[2] not in affected):
                continue
            source = new or old
            assert source is not None
            target, order, _, topup = source
            changes.append(
                DockChange(
                    vehicle=target.vehicle_code,
                    trip_no=target.trip_no,
                    departure=target.planned_depart,
                    order_id=order.id,
                    order_ref=order.ref,
                    outlet_code=order.outlet_code,
                    before=old_qty,
                    after=new_qty,
                    top_up=topup,
                )
            )  # BR-30, BR-31: include linked portions on other trips, and removals.
    active = _hold(db, trip)
    hold = None
    now = clock.now()
    if active:
        sf = db.get(Shortfall, active.shortfall_id)
        assert sf is not None
        order = db.get(Order, sf.order_id)
        assert order is not None
        source_trip = db.get(Trip, sf.trip_id)
        assert source_trip is not None
        planned = sum(
            o.planned_cases for s in source_trip.stops for o in s.orders if o.order_id == order.id
        )
        depart = (
            datetime.combine(version.plan.operating_date, trip.planned_depart, COLOMBO)
            if trip.planned_depart
            else None
        )
        hold = DockHold(
            id=active.id,
            shortfall_id=sf.id,
            order_id=order.id,
            order_ref=order.ref,
            outlet_code=order.outlet_code,
            kind=sf.kind,
            qty=sf.qty,
            planned_cases=planned,
            reason=sf.reason,
            reported_at=ensure_utc(sf.event_time),
            waiting_seconds=max(0, int((now - ensure_utc(sf.event_time)).total_seconds())),
            to_departure_minutes=int((depart - now).total_seconds() // 60) if depart else None,
        )  # BR-27: active hold is visible until the existing sync service releases it.
    return DockDetail(
        **_summary(db, trip, user).model_dump(),
        load_list=lines,
        hold=hold,
        previous_version=parent.number if parent else None,
        previous_departure=next(
            (
                t.planned_depart
                for t in parent.trips
                if (t.vehicle_code, t.trip_no) == (trip.vehicle_code, trip.trip_no)
            ),
            None,
        )
        if parent
        else None,
        changes=changes,
        shortfall_reasons=list(SHORTFALL_REASONS),
        server_time=now,
    )
