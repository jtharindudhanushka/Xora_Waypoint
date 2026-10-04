"""Store domain rules and tracking. Published snapshots/events are read-only here."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta
from typing import cast

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.clock import COLOMBO, Clock, ensure_utc
from app.core.errors import ConflictError, DomainError, ForbiddenError, NotFoundError
from app.modules.auth.models import User
from app.modules.catalog.models import CalendarDay, Outlet, OutletProfile, Product, UsualQuantity
from app.modules.loading.models import Hold
from app.modules.ops.models import Notification
from app.modules.orders.catalogue import CASE_MEASUREMENTS
from app.modules.orders.models import DriverNote, Order, OrderLine
from app.modules.orders.notices import PROTECTION, REASONS, SOURCE, TITLE, Language, language_index
from app.modules.orders.schemas import (
    DriverNoteOut,
    NotificationOut,
    OrderCheckIn,
    OrderCheckOut,
    OrderLineOut,
    OrderOut,
    OrderSubmitIn,
    QuantityWarning,
    StoreHomeOut,
    StoreStatus,
    TrackingOut,
    UsualItemOut,
)
from app.modules.planning.models import Deferral, Plan, PlanVersion, Stop, StopOrder, Trip
from app.modules.receipts.models import Receipt
from app.modules.sync.models import Event


def outlet_for(db: Session, user: User, code: str | None = None) -> Outlet:
    # BR-55: no caller-provided scope may widen the authenticated outlet.
    if not user.outlet_code or (code is not None and code != user.outlet_code):
        raise ForbiddenError(
            "OUTLET_SCOPE", "This store belongs to another account", rule_id="BR-55"
        )
    outlet = db.get(Outlet, user.outlet_code)
    if outlet is None:
        raise NotFoundError("OUTLET_NOT_FOUND", "Store profile not found")
    return outlet


def order_for(db: Session, user: User, ref: str, *, lock: bool = False) -> Order:
    outlet = outlet_for(db, user)
    stmt = select(Order).where(Order.ref == ref, Order.outlet_code == outlet.code)
    if lock:
        stmt = stmt.with_for_update()
    order = db.scalar(stmt)
    if order is None:
        raise NotFoundError("ORDER_NOT_FOUND", "Order not found for this store", rule_id="BR-55")
    return order


def ordering(db: Session, clock: Clock) -> OrderCheckOut:
    # BR-40/56: 16:00 is closed; skip holidays using the seeded operating calendar.
    now = clock.local_now()
    cutoff = datetime.combine(now.date(), time(16), COLOMBO)
    after = now >= cutoff
    earliest = now.date() + timedelta(days=2 if after else 1)
    day = db.scalar(
        select(CalendarDay)
        .where(CalendarDay.date >= earliest, CalendarDay.is_operating.is_(True))
        .order_by(CalendarDay.date)
        .limit(1)
    )
    if day is None:
        raise DomainError(
            "CALENDAR_UNAVAILABLE", "No next operating day is configured", rule_id="BR-40"
        )
    return OrderCheckOut(
        warnings=[],
        delivery_date=day.date,
        cutoff_at=cutoff,
        cutoff_seconds=max(0, int((cutoff - now).total_seconds())),
        after_cutoff=after,
    )


def products_for(db: Session, user: User, body: OrderCheckIn) -> dict[str, Product]:
    outlet = outlet_for(db, user)
    ids = [line.product_id for line in body.lines]
    if len(ids) != len(set(ids)):
        raise DomainError("DUPLICATE_ITEM", "Each item must appear once", rule_id="BR-41")
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids)))}
    if len(products) != len(ids) or any(p.brand != outlet.brand for p in products.values()):
        raise DomainError(
            "INVALID_PRODUCT", "Choose items from this store's catalogue", rule_id="BR-41"
        )
    return products


def check(db: Session, user: User, clock: Clock, body: OrderCheckIn) -> OrderCheckOut:
    products_for(db, user, body)
    out = ordering(db, clock)
    usual = {
        u.product_id: u.usual_cases
        for u in db.scalars(
            select(UsualQuantity).where(UsualQuantity.outlet_code == user.outlet_code)
        )
    }
    for line in body.lines:
        qty = usual.get(line.product_id)
        if qty and line.qty >= qty * 3:  # BR-42: Figma's 60 vs usual 20 is questioned.
            out.warnings.append(
                QuantityWarning(
                    product_id=line.product_id,
                    qty=line.qty,
                    usual_qty=qty,
                    message=f"3× your usual. Did you mean {qty}?",
                )
            )
    return out


def audit(
    db: Session,
    user: User,
    clock: Clock,
    kind: str,
    entity: str,
    entity_id: str,
    payload: dict,
    event_id: uuid.UUID | None = None,
) -> Event:
    now = clock.now()
    event = Event(
        event_id=event_id or uuid.uuid4(),
        type=kind,
        actor_id=user.id,
        entity_type=entity,
        entity_id=entity_id,
        payload=payload,
        event_time=now,
        received_at=now,
    )
    db.add(event)
    return event


def usual_items(db: Session, user: User, code: str) -> list[UsualItemOut]:
    outlet = outlet_for(db, user, code)
    usual = {
        u.product_id: u.usual_cases
        for u in db.scalars(select(UsualQuantity).where(UsualQuantity.outlet_code == code))
    }
    return [
        UsualItemOut(
            product_id=p.id, name=p.name, is_chilled=p.is_chilled, usual_qty=usual.get(p.id)
        )
        for p in db.scalars(
            select(Product).where(Product.brand == outlet.brand).order_by(Product.id)
        )
    ]


def submit(db: Session, user: User, clock: Clock, body: OrderSubmitIn) -> list[OrderOut]:
    outlet = outlet_for(db, user)
    # Lock the outlet to serialize draft/new submissions and request idempotency.
    db.scalar(select(Outlet).where(Outlet.code == outlet.code).with_for_update())
    prior = db.get(Event, body.request_id)
    fingerprint = body.model_dump(mode="json")
    if prior:
        if (
            prior.actor_id != user.id
            or prior.type != "order.placed"
            or prior.payload.get("request") != fingerprint
        ):
            raise ConflictError(
                "IDEMPOTENCY_CONFLICT", "This request id was used for another action"
            )
        return [order_out(db, order_for(db, user, ref), clock) for ref in prior.payload["refs"]]
    checked = check(db, user, clock, body)
    if checked.warnings and not body.confirm_unusual:
        raise DomainError(
            "QUANTITY_CONFIRMATION_REQUIRED",
            "Confirm unusual quantities or use your usual amount",
            rule_id="BR-42",
            warnings=[w.model_dump() for w in checked.warnings],
        )
    products = products_for(db, user, body)
    positive = [line for line in body.lines if line.qty > 0]
    if not positive:
        raise DomainError("EMPTY_ORDER", "Add at least one item", rule_id="BR-41")
    groups = {products[line.product_id].is_chilled for line in positive}
    draft = order_for(db, user, body.draft_ref, lock=True) if body.draft_ref else None
    if draft and draft.status != "draft":
        raise ConflictError("ORDER_ALREADY_PLACED", "This draft was already submitted")
    if draft and (len(groups) != 1 or (draft.temp_requirement == "chilled") not in groups):
        raise DomainError(
            "SEPARATE_ORDERS", "Submit chilled and dry items as separate orders", rule_id="BR-41"
        )
    if draft is None:
        if any(line.product_id not in CASE_MEASUREMENTS for line in positive):
            raise DomainError(
                "CATALOGUE_MEASUREMENTS_REQUIRED",
                "Case measurements are not configured for this item",
            )
        created = []
        for chilled in sorted(groups, reverse=True):
            items = [line for line in positive if products[line.product_id].is_chilled == chilled]
            order = Order(
                ref="APP-" + uuid.uuid5(body.request_id, str(chilled)).hex[:16],
                outlet_code=outlet.code,
                brand=outlet.brand,
                temp_requirement="chilled" if chilled else "ambient",
                delivery_date=checked.delivery_date,
                units=sum(line.qty for line in items),
                weight_kg=sum(CASE_MEASUREMENTS[line.product_id][0] * line.qty for line in items),
                volume_m3=sum(CASE_MEASUREMENTS[line.product_id][1] * line.qty for line in items),
                status="placed",
                source="app",
                placed_at=clock.now(),
                placed_by=user.id,
            )
            db.add(order)
            db.flush()
            for item in items:
                db.add(
                    OrderLine(order_id=order.id, product_id=item.product_id, qty_ordered=item.qty)
                )
            created.append(order)
        audit(
            db,
            user,
            clock,
            "order.placed",
            "outlet",
            outlet.code,
            {"refs": [o.ref for o in created], "request": fingerprint},
            body.request_id,
        )
        db.commit()
        return [order_out(db, o, clock) for o in created]
    # Existing S1 aggregate kg/m³ are authoritative, including its corrected 80-case draft.
    existing = {line.product_id: line for line in draft.lines}
    for entry in body.lines:
        line = existing.get(entry.product_id)
        if entry.qty == 0:
            if line:
                db.delete(line)
            continue
        if line:
            line.qty_ordered = entry.qty
        else:
            db.add(OrderLine(order_id=draft.id, product_id=entry.product_id, qty_ordered=entry.qty))
    for product_id, line in existing.items():
        if product_id not in {x.product_id for x in body.lines}:
            db.delete(line)
    units = sum(x.qty for x in positive)
    ratio = units / draft.units
    draft.weight_kg = float(draft.weight_kg) * ratio
    draft.volume_m3 = float(draft.volume_m3) * ratio
    draft.units = units
    draft.delivery_date = checked.delivery_date
    draft.status = "placed"
    draft.placed_at = clock.now()
    draft.placed_by = user.id
    audit(
        db,
        user,
        clock,
        "order.placed",
        "outlet",
        outlet.code,
        {"refs": [draft.ref], "request": fingerprint},
        body.request_id,
    )
    db.commit()
    db.expire(draft, ["lines"])
    return [order_out(db, draft, clock)]


def latest_version(db: Session, order: Order) -> PlanVersion | None:
    outlet = db.get(Outlet, order.outlet_code)
    return (
        db.scalar(
            select(PlanVersion)
            .join(Plan)
            .where(
                Plan.depot == outlet.depot,
                Plan.operating_date == order.delivery_date,
                PlanVersion.status == "published",
            )
            .order_by(PlanVersion.number.desc())
            .limit(1)
        )
        if outlet
        else None
    )


def stop_events(db: Session, stop: Stop) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(
                or_(
                    and_(Event.entity_type == "stop", Event.entity_id == str(stop.id)),
                    and_(Event.entity_type == "trip", Event.entity_id == str(stop.trip_id)),
                )
            )
            .order_by(Event.event_time, Event.received_at, Event.event_id)
        )
    )


def tracking(db: Session, order: Order, clock: Clock) -> list[TrackingOut]:
    version = latest_version(db, order)
    if not version:
        return []
    pairs = list(
        db.execute(
            select(Stop, StopOrder)
            .join(StopOrder)
            .join(Trip)
            .where(
                Trip.version_id == version.id,
                StopOrder.order_id == order.id,
            )
            .order_by(Trip.trip_no, Stop.seq)
        )
    )
    out = []
    for stop, so in pairs:
        trip = stop.trip
        events = stop_events(db, stop)
        status: StoreStatus = "at_risk" if stop.at_risk else "planned"
        last = None
        for event in events:
            if event.type in {"trip_loaded", "load_checked"}:
                status = "loaded"
            elif event.type in {"trip_started", "departed", "trip_departed", "arrived"}:
                status = "in_transit"
            elif event.type == "outcome_recorded":
                outcome = str(event.payload.get("outcome", "delivered")).lower()
                status = "delivered" if outcome in {"delivered", "partial"} else "at_risk"
                last = event
        if not events and stop.status in {
            "loaded",
            "in_transit",
            "delivered",
            "late",
            "pending_sync",
        }:
            status = cast(StoreStatus, stop.status)
        if status != "delivered" and db.scalar(
            select(Hold.id).where(Hold.trip_id == trip.id, Hold.status == "active")
        ):
            status = "on_hold"
        elif status not in {"delivered", "pending_sync"} and stop.likely_to:
            eta = datetime.combine(order.delivery_date, stop.likely_to, COLOMBO)
            if clock.local_now() > eta:
                status = "late"
        out.append(
            TrackingOut(
                stop_id=stop.id,
                stop_seq=stop.seq,
                stop_count=len(trip.stops),
                vehicle_code=trip.vehicle_code,
                trip_no=trip.trip_no,
                version=version.number,
                planned_cases=so.planned_cases,
                plan_arrival=stop.plan_arrival,
                likely_from=stop.likely_from,
                likely_to=stop.likely_to,
                status=status,
                event_time=ensure_utc(last.event_time) if last else None,
                received_at=ensure_utc(last.received_at) if last else None,
            )
        )
    return out


def order_out(db: Session, order: Order, clock: Clock) -> OrderOut:
    tracks = tracking(db, order, clock)
    status: StoreStatus = "planned"
    version = latest_version(db, order)
    if version and db.scalar(
        select(Deferral.id).where(Deferral.version_id == version.id, Deferral.order_id == order.id)
    ):
        status = "deferred"
    elif tracks:
        statuses = [t.status for t in tracks]
        status = (
            "delivered"
            if all(s == "delivered" for s in statuses)
            else next((s for s in statuses if s != "delivered"), "planned")
        )
    elif order.status == "delivered":
        status = "delivered"
    outlet = db.get(Outlet, order.outlet_code)
    return OrderOut(
        ref=order.ref,
        outlet_code=order.outlet_code,
        brand=order.brand,
        district=outlet.district if outlet else "",
        temp_requirement=order.temp_requirement,
        delivery_date=order.delivery_date,
        units=order.units,
        status=status,
        submission_status=order.status,
        placed_at=ensure_utc(order.placed_at).astimezone(COLOMBO) if order.placed_at else None,
        receipt_confirmed=db.scalar(select(Receipt.id).where(Receipt.order_id == order.id))
        is not None,
        lines=[
            OrderLineOut(
                id=line.id,
                product_id=line.product_id,
                name=p.name if (p := db.get(Product, line.product_id)) else line.product_id,
                qty_ordered=line.qty_ordered,
                qty_delivered=line.qty_delivered,
                qty_received=line.qty_received,
            )
            for line in order.lines
        ],
        tracking=tracks,
    )


def home(db: Session, user: User, clock: Clock) -> StoreHomeOut:
    outlet = outlet_for(db, user)
    orders = db.scalars(
        select(Order)
        .where(Order.outlet_code == outlet.code)
        .order_by(Order.delivery_date.desc(), Order.ref)
        .limit(50)
    )
    note = db.scalar(
        select(DriverNote)
        .where(
            DriverNote.outlet_code == outlet.code, DriverNote.for_date == clock.local_now().date()
        )
        .order_by(DriverNote.sent_at.desc())
        .limit(1)
    )
    return StoreHomeOut(
        outlet_code=outlet.code,
        district=outlet.district,
        brand=outlet.brand,
        now=clock.local_now(),
        ordering=ordering(db, clock),
        window_open=outlet.window_open,
        window_close=outlet.window_close,
        orders=[order_out(db, o, clock) for o in orders],
        driver_note=DriverNoteOut(
            text=note.text, sent_at=ensure_utc(note.sent_at).astimezone(COLOMBO)
        )
        if note
        else None,
    )


def notification_out(
    db: Session, notice: Notification, language: Language | None = None
) -> NotificationOut:
    order = db.get(Order, notice.order_id) if notice.order_id else None
    profile = db.get(OutletProfile, notice.outlet_code) if notice.outlet_code else None
    lang = language or cast(Language, profile.language if profile else notice.lang)
    index = language_index(lang)
    body = notice.body
    if notice.kind == "deferral" and lang != "en":
        reason = REASONS.get(notice.reason_code or "", REASONS["LOWER_PRIORITY"])[index]
        body = f"{order.ref if order else ''}: {reason}\n{notice.data.get('next_run', '')}"
    return NotificationOut(
        id=notice.id,
        kind=notice.kind,
        order_ref=order.ref if order else None,
        reason_code=notice.reason_code,
        lang=lang,
        title=TITLE[index] if notice.kind == "deferral" else notice.title,
        body=body,
        source=SOURCE[index],
        protection=PROTECTION[index],
        next_run=notice.data.get("next_run"),
        created_at=ensure_utc(notice.created_at).astimezone(COLOMBO),
        acked_at=ensure_utc(notice.acked_at).astimezone(COLOMBO) if notice.acked_at else None,
    )


def notice_for(
    db: Session, user: User, notice_id: uuid.UUID, *, lock: bool = False
) -> Notification:
    outlet_for(db, user)
    # A user-targeted notice is private even when it also carries an outlet.
    stmt = select(Notification).where(
        Notification.id == notice_id,
        or_(
            Notification.recipient_user_id == user.id,
            and_(
                Notification.recipient_user_id.is_(None),
                Notification.outlet_code == user.outlet_code,
            ),
        ),
    )
    if lock:
        stmt = stmt.with_for_update()
    notice = db.scalar(stmt)
    if notice is None:
        raise NotFoundError("NOTICE_NOT_FOUND", "Notice not found for this store", rule_id="BR-55")
    return notice


def notices(db: Session, user: User) -> list[NotificationOut]:
    outlet_for(db, user)
    rows = db.scalars(
        select(Notification)
        .where(
            or_(
                Notification.recipient_user_id == user.id,
                and_(
                    Notification.recipient_user_id.is_(None),
                    Notification.outlet_code == user.outlet_code,
                ),
            )
        )
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return [notification_out(db, n) for n in rows]
