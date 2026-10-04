"""Read side for field devices: the published plan for a vehicle on an operating day.

Field apps only ever see the **published** version (ADR-0003); drafts stay with dispatch.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock, ensure_utc
from app.core.errors import NotFoundError
from app.modules.auth.models import User
from app.modules.catalog.models import Outlet, OutletProfile, Product, Vehicle
from app.modules.loading.models import Hold, RepairOption, Shortfall
from app.modules.orders.models import DriverNote, Order
from app.modules.planning.models import Plan, PlanAck, PlanVersion, Stop, StopOrder, Trip
from app.modules.sync.models import Event
from app.modules.sync.schemas import (
    KnownShortfallOut,
    OrderLineView,
    StopOrderView,
    StopView,
    TripView,
    VehicleTodayOut,
    VersionView,
)


def operating_date(clock: Clock, requested: date | None) -> date:
    return requested or clock.local_now().date()


def published_version(db: Session, depot: str, day: date) -> PlanVersion | None:
    return db.scalar(
        select(PlanVersion)
        .join(Plan, PlanVersion.plan_id == Plan.id)
        .where(Plan.depot == depot, Plan.operating_date == day, PlanVersion.status == "published")
        .order_by(PlanVersion.number.desc())
        .limit(1)
    )


def current_version_for(db: Session, version: PlanVersion) -> PlanVersion | None:
    """The version that is published now for the same plan as `version`."""
    return db.scalar(
        select(PlanVersion)
        .where(PlanVersion.plan_id == version.plan_id, PlanVersion.status == "published")
        .order_by(PlanVersion.number.desc())
        .limit(1)
    )


def equivalent_stop(version: PlanVersion, stop: Stop, vehicle_code: str) -> Stop | None:
    """The same vehicle's stop at the same outlet in another version, if any."""
    for trip in version.trips:
        if trip.vehicle_code != vehicle_code:
            continue
        for candidate in trip.stops:
            if candidate.outlet_code == stop.outlet_code:
                return candidate
    return None


def _ack(db: Session, version_id: uuid.UUID, user: User) -> PlanAck | None:
    return db.get(PlanAck, (version_id, user.id))


def _last_event(db: Session, stop_ids: list[str], kind: str) -> dict[str, Event]:
    rows = db.scalars(
        select(Event)
        .where(Event.type == kind, Event.entity_type == "stop", Event.entity_id.in_(stop_ids))
        .order_by(Event.event_time)
    )
    return {row.entity_id: row for row in rows}


def vehicle_today(
    db: Session, clock: Clock, user: User, vehicle: Vehicle, day: date
) -> VehicleTodayOut:
    version = published_version(db, vehicle.depot, day)
    trips: list[TripView] = []
    version_view: VersionView | None = None
    if version is not None:
        ack = _ack(db, version.id, user)
        version_view = VersionView(
            id=version.id,
            number=version.number,
            published_at=ensure_utc(version.published_at) if version.published_at else None,
            change_reason=version.change_reason,
            acknowledged=ack is not None,
            acked_at=ensure_utc(ack.acked_at) if ack else None,
        )
        mine = sorted(
            (t for t in version.trips if t.vehicle_code == vehicle.code), key=lambda t: t.trip_no
        )
        trips = [_trip_view(db, version, trip, day) for trip in mine]
    return VehicleTodayOut(
        vehicle_code=vehicle.code,
        vehicle_type=vehicle.type,
        vehicle_temp=vehicle.temp,
        operating_date=day,
        server_time=clock.now(),
        version=version_view,
        trips=trips,
    )


def _trip_view(db: Session, version: PlanVersion, trip: Trip, day: date) -> TripView:
    hold = db.scalar(select(Hold).where(Hold.trip_id == trip.id, Hold.status == "active"))
    stop_ids = [str(s.id) for s in trip.stops]
    arrivals = _last_event(db, stop_ids, "arrived")
    outcomes = _last_event(db, stop_ids, "outcome_recorded")
    trip_ids = [t.id for t in version.trips]
    shortfalls = {
        s.order_id: s
        for s in db.scalars(
            select(Shortfall)
            .join(Hold, Hold.shortfall_id == Shortfall.id)
            .where(Hold.trip_id.in_(trip_ids))
            # BR-34: B re-picks the full quantity; its historical shortage is not outstanding.
            .where(
                Shortfall.id.not_in(
                    select(RepairOption.shortfall_id).where(
                        RepairOption.label == "B", RepairOption.applied_at.is_not(None)
                    )
                )
            )
            .order_by(Shortfall.event_time)
        )
    }
    stops = []
    for stop in trip.stops:
        outlet = db.get(Outlet, stop.outlet_code)
        assert outlet is not None
        profile = db.get(OutletProfile, stop.outlet_code)
        note = db.scalar(
            select(DriverNote)
            .where(DriverNote.outlet_code == stop.outlet_code, DriverNote.for_date == day)
            .order_by(DriverNote.sent_at.desc())
            .limit(1)
        )
        arrived = arrivals.get(str(stop.id))
        outcome = outcomes.get(str(stop.id))
        stops.append(
            StopView(
                id=stop.id,
                seq=stop.seq,
                outlet_code=stop.outlet_code,
                district=outlet.district,
                status=stop.status,
                plan_arrival=stop.plan_arrival,
                likely_from=stop.likely_from,
                likely_to=stop.likely_to,
                at_risk=stop.at_risk,
                window_open=outlet.window_open,
                window_close=outlet.window_close,
                dock_type=outlet.dock_type,
                parking_constraint=outlet.parking_constraint,
                mall_window_open=outlet.mall_window_open,
                mall_window_close=outlet.mall_window_close,
                access_note=profile.access_note if profile else None,
                contact_name=profile.contact_name if profile else None,
                store_note=note.text if note else None,
                store_note_at=ensure_utc(note.sent_at) if note else None,
                arrived_at=_event_time(arrived),
                outcome=str(outcome.payload.get("outcome")) if outcome else None,
                orders=[_order_view(db, so, shortfalls) for so in stop.orders],
            )
        )
    return TripView(
        id=trip.id,
        trip_no=trip.trip_no,
        lane=trip.lane,
        brand=trip.brand,
        district=trip.district,
        planned_depart=trip.planned_depart,
        plan_minutes=trip.plan_minutes,
        weight_kg=float(trip.weight_kg),
        volume_m3=float(trip.volume_m3),
        on_hold=hold is not None,
        hold_shortfall_id=hold.shortfall_id if hold else None,
        stops=stops,
    )


def _event_time(event: Event | None) -> datetime | None:
    return ensure_utc(event.event_time) if event else None


def _order_view(
    db: Session, stop_order: StopOrder, shortfalls: dict[uuid.UUID, Shortfall]
) -> StopOrderView:
    order = db.get(Order, stop_order.order_id)
    assert order is not None
    top_up = db.get(Order, stop_order.top_up_of_order_id) if stop_order.top_up_of_order_id else None
    lines = []
    for line in order.lines:
        product = db.get(Product, line.product_id)
        lines.append(
            OrderLineView(
                product_id=line.product_id,
                name=product.name if product else line.product_id,
                qty=line.qty_ordered,
            )
        )
    shortfall = None if top_up else shortfalls.get(order.id)
    return StopOrderView(
        order_id=order.id,
        order_ref=order.ref,
        temp_requirement=order.temp_requirement,
        planned_cases=stop_order.planned_cases,
        weight_kg=float(order.weight_kg),
        volume_m3=float(order.volume_m3),
        top_up_of_order_ref=top_up.ref if top_up else None,
        lines=lines,
        known_shortfall=KnownShortfallOut(
            shortfall_id=shortfall.id,
            kind=shortfall.kind,
            qty=shortfall.qty,
            reason=shortfall.reason,
        )
        if shortfall
        else None,
    )


def require_vehicle(db: Session, code: str) -> Vehicle:
    vehicle = db.get(Vehicle, code)
    if vehicle is None:
        raise NotFoundError("VEHICLE_NOT_FOUND", f"No vehicle {code}")
    return vehicle
