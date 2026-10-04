"""POST /sync: apply a device's outbox in order (docs/07 › Server side).

Each event commits on its own, so one bad event never blocks the batch. The same `event_id`
is accepted once (BR-36). Conflicts never overwrite: the event is stored and an `issues` row
is opened for dispatch (BR-52, BR-53). Events are append-only; projections carry state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock, ensure_utc
from app.core.errors import DomainError, ForbiddenError, NotFoundError
from app.modules.auth.models import User
from app.modules.loading.models import SHORTFALL_REASONS, Hold, Shortfall
from app.modules.ops.models import ExceptionItem
from app.modules.orders.models import Order
from app.modules.planning.models import Plan, PlanAck, PlanVersion, Stop, Trip
from app.modules.receipts.models import Issue, Receipt
from app.modules.stream.broker import Audience
from app.modules.sync import views
from app.modules.sync.models import Event
from app.modules.sync.schemas import SyncEventIn, SyncIn, SyncOut, SyncResultOut

OUTCOMES = ("delivered", "partial", "failed")


@dataclass
class Outbound:
    """SSE messages to publish once the event's transaction has committed."""

    messages: list[tuple[str, dict[str, Any], Audience | None]] = field(default_factory=list)

    def add(self, event: str, data: dict[str, Any], audience: Audience | None = None) -> None:
        self.messages.append((event, data, audience))


@dataclass
class Applied:
    conflict_id: uuid.UUID | None = None


def _dispatch(depot: str) -> Audience:
    return lambda s: s.get("role") == "dispatcher" and s.get("depot") == depot


def _dispatch_and_loaders(depot: str) -> Audience:
    return lambda s: s.get("role") in ("dispatcher", "loader") and s.get("depot") == depot


def process(db: Session, clock: Clock, user: User, body: SyncIn, out: Outbound) -> SyncOut:
    ordered = sorted(
        enumerate(body.events), key=lambda pair: (pair[1].seq is None, pair[1].seq or 0, pair[0])
    )
    results = [_one(db, clock, user, body.device_id, event, out) for _, event in ordered]
    return SyncOut(results=results, server_time=clock.now())


def _one(
    db: Session, clock: Clock, user: User, device_id: str, event: SyncEventIn, out: Outbound
) -> SyncResultOut:
    if db.get(Event, event.event_id) is not None:
        return SyncResultOut(event_id=event.event_id, status="duplicate")  # BR-36
    pending = Outbound()
    try:
        db.add(
            Event(
                event_id=event.event_id,
                type=event.type,
                actor_id=user.id,
                device_id=device_id,
                plan_version_id=event.plan_version_id,
                entity_type=event.entity.type,
                entity_id=event.entity.id,
                payload=event.payload,
                event_time=ensure_utc(event.event_time),  # device time counts (BR-37)
                received_at=clock.now(),
            )
        )
        db.flush()
        applied = _apply(db, clock, user, event, pending)
        db.commit()
    except DomainError as exc:
        db.rollback()
        return SyncResultOut(
            event_id=event.event_id,
            status="rejected",
            code=exc.code,
            rule_id=exc.rule_id,
            detail=exc.detail,
        )
    out.messages.extend(pending.messages)
    if applied.conflict_id is not None:
        return SyncResultOut(
            event_id=event.event_id, status="conflict", conflict_id=applied.conflict_id
        )
    return SyncResultOut(event_id=event.event_id, status="accepted")


# ── resolution and scope ──────────────────────────────────────────────────────


def _uuid(value: str, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise NotFoundError("ENTITY_NOT_FOUND", f"Unknown {what} {value}") from exc


def _trip(db: Session, trip_id: str) -> Trip:
    trip = db.get(Trip, _uuid(trip_id, "trip"))
    if trip is None:
        raise NotFoundError("ENTITY_NOT_FOUND", f"Unknown trip {trip_id}")
    return trip


def _stop(db: Session, stop_id: str) -> Stop:
    stop = db.get(Stop, _uuid(stop_id, "stop"))
    if stop is None:
        raise NotFoundError("ENTITY_NOT_FOUND", f"Unknown stop {stop_id}")
    return stop


def _depot(db: Session, trip: Trip) -> str:
    version = db.get(PlanVersion, trip.version_id)
    assert version is not None
    plan = db.get(Plan, version.plan_id)
    assert plan is not None
    return plan.depot


def _check_scope(db: Session, user: User, trip: Trip) -> None:
    """Drivers act on their own vehicle; loaders on their own depot's trips (BR-55)."""
    if user.role == "driver" and trip.vehicle_code != user.vehicle_code:
        raise ForbiddenError(
            "OUT_OF_SCOPE", f"{trip.vehicle_code} is not your vehicle", rule_id="BR-55"
        )
    if user.role == "loader" and _depot(db, trip) != user.depot:
        raise ForbiddenError("OUT_OF_SCOPE", "This trip is not on your dock", rule_id="BR-55")
    if user.role not in ("driver", "loader", "dispatcher"):
        raise ForbiddenError("ROLE_FORBIDDEN", "Only field roles sync events", rule_id="BR-55")


def _active_hold(db: Session, trip_id: uuid.UUID) -> Hold | None:
    return db.scalar(select(Hold).where(Hold.trip_id == trip_id, Hold.status == "active"))


# ── projections ───────────────────────────────────────────────────────────────


def _apply(db: Session, clock: Clock, user: User, event: SyncEventIn, out: Outbound) -> Applied:
    if event.type == "note_added":
        return Applied()
    if event.entity.type == "trip":
        trip = _trip(db, event.entity.id)
        _check_scope(db, user, trip)
        if event.type == "trip_acknowledged":
            return _acknowledge(db, clock, user, trip, event, out)
        if event.type == "shortfall_reported":
            return _shortfall(db, user, trip, event, out)
        if event.type in ("load_checked", "trip_loaded"):
            if event.type == "trip_loaded" and _active_hold(db, trip.id):
                raise DomainError("TRIP_ON_HOLD", "This van is on hold", rule_id="BR-27")
            return Applied()
    if event.entity.type == "stop" and event.type in ("arrived", "outcome_recorded"):
        stop = _stop(db, event.entity.id)
        stop_trip = db.get(Trip, stop.trip_id)
        assert stop_trip is not None
        _check_scope(db, user, stop_trip)
        return _stop_event(db, clock, user, stop_trip, stop, event, out)
    raise DomainError(
        "UNSUPPORTED_EVENT", f"{event.type} on a {event.entity.type} is not supported"
    )


def _acknowledge(
    db: Session, clock: Clock, user: User, trip: Trip, event: SyncEventIn, out: Outbound
) -> Applied:
    """Record the ack (BR-32). A loader's ack releases the holds it resolves (BR-31)."""
    version_id = event.plan_version_id or trip.version_id
    if db.get(PlanAck, (version_id, user.id)) is None:
        db.add(
            PlanAck(version_id=version_id, user_id=user.id, acked_at=ensure_utc(event.event_time))
        )
    if user.role == "loader":
        release_holds(db, clock, user, version_id, out)
    return Applied()


def release_holds(
    db: Session, clock: Clock, user: User, version_id: uuid.UUID, out: Outbound
) -> list[Hold]:
    """Holds that a repair moved onto this version's trips are lifted by the loader's ack (BR-31).

    A hold still on an unrepaired trip stays active: acknowledging v1 resolves nothing.
    """
    holds = list(
        db.scalars(
            select(Hold)
            .join(Trip, Hold.trip_id == Trip.id)
            .where(Trip.version_id == version_id, Hold.status == "active")
        )
    )
    version = db.get(PlanVersion, version_id)
    if version is None or version.status != "published" or version.parent_version_id is None:
        return []
    for hold in holds:
        hold.status = "released"
        hold.released_at = clock.now()
        hold.released_by = user.id
        for item in db.scalars(
            select(ExceptionItem).where(
                ExceptionItem.kind == "shortfall",
                ExceptionItem.entity_id == str(hold.shortfall_id),
                ExceptionItem.status == "open",
            )
        ):
            item.status = "resolved"
        trip = db.get(Trip, hold.trip_id)
        assert trip is not None
        out.add(
            "hold.released",
            {"hold_id": str(hold.id), "trip_id": str(hold.trip_id), "vehicle": trip.vehicle_code},
            _dispatch_and_loaders(_depot(db, trip)),
        )
    return holds


def _shortfall(db: Session, user: User, trip: Trip, event: SyncEventIn, out: Outbound) -> Applied:
    """A dock shortfall report puts that vehicle's trip on hold (BR-26, BR-27)."""
    p = event.payload
    order_id = _uuid(str(p.get("order_id", "")), "order")
    planned = {so.order_id: so.planned_cases for stop in trip.stops for so in stop.orders}
    if order_id not in planned:
        raise DomainError("ORDER_NOT_ON_TRIP", "That order is not on this trip", rule_id="BR-26")
    kind, reason, qty = p.get("kind"), p.get("reason"), p.get("qty")
    if kind not in ("missing", "damaged"):
        raise DomainError("INVALID_SHORTFALL", "Kind must be missing or damaged", rule_id="BR-26")
    if reason not in SHORTFALL_REASONS:
        raise DomainError("INVALID_SHORTFALL", "Choose a reason", rule_id="BR-26")
    if not isinstance(qty, int) or not 0 < qty <= planned[order_id]:
        raise DomainError(
            "INVALID_SHORTFALL", f"Quantity must be 1 to {planned[order_id]}", rule_id="BR-26"
        )
    at = ensure_utc(event.event_time)
    shortfall = Shortfall(
        trip_id=trip.id,
        order_id=order_id,
        kind=kind,
        qty=qty,
        reason=reason,
        photo_url=p.get("photo_url"),
        reported_by=user.id,
        event_time=at,
    )
    db.add(shortfall)
    db.flush()
    hold = Hold(trip_id=trip.id, shortfall_id=shortfall.id, status="active", created_at=at)
    db.add(hold)
    order = db.get(Order, order_id)
    assert order is not None
    db.add(
        ExceptionItem(
            kind="shortfall",
            impact=qty,
            title=f"{trip.vehicle_code} T{trip.trip_no} on hold · {order.outlet_code} {kind} {qty}",
            detail=reason,
            entity_type="shortfall",
            entity_id=str(shortfall.id),
            created_at=at,
        )
    )
    db.flush()
    depot = _depot(db, trip)
    out.add(
        "hold.created",
        {
            "hold_id": str(hold.id),
            "shortfall_id": str(shortfall.id),
            "trip_id": str(trip.id),
            "vehicle": trip.vehicle_code,
        },
        _dispatch_and_loaders(depot),
    )
    out.add(
        "exception.created", {"kind": "shortfall", "entity_id": str(shortfall.id)}, _dispatch(depot)
    )
    return Applied()


def _stop_event(
    db: Session,
    clock: Clock,
    user: User,
    trip: Trip,
    stop: Stop,
    event: SyncEventIn,
    out: Outbound,
) -> Applied:
    if user.role == "driver":
        seen = event.plan_version_id or trip.version_id
        if db.get(PlanAck, (seen, user.id)) is None:
            raise DomainError(
                "PLAN_NOT_ACKNOWLEDGED", "Acknowledge the plan before starting", rule_id="BR-32"
            )
    if event.type == "outcome_recorded":
        _validate_outcome(event.payload)
    source = db.get(PlanVersion, trip.version_id)
    assert source is not None
    current = views.current_version_for(db, source)
    target = stop
    if current is not None and current.id != source.id:
        target = views.equivalent_stop(current, stop, trip.vehicle_code)  # type: ignore[assignment]
        if target is None or _changed(stop, target):
            issue = _open_issue(db, clock, stop, "stale_plan", event, out, _depot(db, trip))
            return Applied(conflict_id=issue.id)  # BR-53: stored, not applied
    if event.type == "arrived":
        if target.status == "planned":
            target.status = "in_transit"
        return Applied()
    return _outcome(db, clock, target, trip, event, out)


def _changed(old: Stop, new: Stop) -> bool:
    return {(o.order_id, o.planned_cases) for o in old.orders} != {
        (o.order_id, o.planned_cases) for o in new.orders
    }


def _validate_outcome(p: dict[str, Any]) -> None:
    if p.get("outcome") not in OUTCOMES:
        raise DomainError(
            "INVALID_OUTCOME", "Outcome must be delivered, partial or failed", rule_id="BR-34"
        )
    for line in p.get("orders", []):
        if not isinstance(line.get("cases"), int) or line["cases"] < 0:
            raise DomainError("INVALID_OUTCOME", "Cases must be a whole number", rule_id="BR-34")


def _outcome(
    db: Session, clock: Clock, stop: Stop, trip: Trip, event: SyncEventIn, out: Outbound
) -> Applied:
    """Record the outcome (BR-34); a count that differs from the store receipt conflicts (BR-52)."""
    p = event.payload
    stop.status = "delivered" if p["outcome"] in ("delivered", "partial") else "failed"
    conflict: uuid.UUID | None = None
    on_stop = {so.order_id for so in stop.orders}
    for line in p.get("orders", []):
        order_id = _uuid(str(line.get("order_id", "")), "order")
        if order_id not in on_stop:
            raise DomainError(
                "ORDER_NOT_ON_STOP", "That order is not on this stop", rule_id="BR-34"
            )
        order = db.get(Order, order_id)
        assert order is not None
        if p["outcome"] != "failed":
            order.status = "delivered"
        receipt = db.scalar(select(Receipt).where(Receipt.order_id == order_id))
        if receipt is not None and receipt.total_cases != line["cases"]:
            issue = _open_issue(
                db,
                clock,
                stop,
                "count_conflict",
                event,
                out,
                _depot(db, trip),
                order_id=order_id,
                driver_qty=line["cases"],
                store_qty=receipt.total_cases,
            )
            conflict = conflict or issue.id
    return Applied(conflict_id=conflict)


def _open_issue(
    db: Session,
    clock: Clock,
    stop: Stop,
    kind: str,
    event: SyncEventIn,
    out: Outbound,
    depot: str,
    *,
    order_id: uuid.UUID | None = None,
    driver_qty: int | None = None,
    store_qty: int | None = None,
) -> Issue:
    """Both records stay; dispatch decides in D13 (BR-52, BR-53)."""
    order_id = order_id or stop.orders[0].order_id
    issue = Issue(
        order_id=order_id,
        kind=kind,
        status="open",
        driver_event_id=event.event_id,
        driver_qty=driver_qty,
        store_qty=store_qty,
        opened_at=clock.now(),
    )
    db.add(issue)
    db.flush()
    title = (
        f"{stop.outlet_code}: driver {driver_qty} vs store {store_qty}"
        if kind == "count_conflict"
        else f"{stop.outlet_code}: update recorded against an older plan"
    )
    db.add(
        ExceptionItem(
            kind="conflict",
            impact=abs((driver_qty or 0) - (store_qty or 0)),
            title=title,
            entity_type="issue",
            entity_id=str(issue.id),
            created_at=clock.now(),
        )
    )
    out.add(
        "conflict.created",
        {"issue_id": str(issue.id), "kind": kind, "outlet": stop.outlet_code},
        _dispatch(depot),
    )
    return issue
