"""Store orders, catalogue, notes and scoped deferral notifications."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import ClockDep, DbDep, require_roles
from app.modules.auth.models import User
from app.modules.orders import service
from app.modules.orders.models import DriverNote
from app.modules.orders.notices import Language
from app.modules.orders.schemas import (
    DriverNoteIn,
    DriverNoteOut,
    NotificationOut,
    OrderCheckIn,
    OrderCheckOut,
    OrderOut,
    OrderSubmitIn,
    StoreHomeOut,
    UsualItemOut,
)
from app.modules.stream.broker import broker

router = APIRouter(tags=["store"])
StoreUser = Annotated[User, Depends(require_roles("store_manager"))]


@router.get("/stores/me/orders", response_model=StoreHomeOut)
def home(db: DbDep, user: StoreUser, clock: ClockDep) -> StoreHomeOut:
    return service.home(db, user, clock)


@router.get("/orders/{ref}", response_model=OrderOut)
def get_order(ref: str, db: DbDep, user: StoreUser, clock: ClockDep) -> OrderOut:
    return service.order_out(db, service.order_for(db, user, ref), clock)


@router.get("/outlets/{code}/usual-items", response_model=list[UsualItemOut])
def usual_items(code: str, db: DbDep, user: StoreUser) -> list[UsualItemOut]:
    return service.usual_items(db, user, code)


@router.get("/outlets/{code}/next-deliveries", response_model=list[OrderOut])
def next_deliveries(code: str, db: DbDep, user: StoreUser, clock: ClockDep) -> list[OrderOut]:
    service.outlet_for(db, user, code)
    return [
        o
        for o in service.home(db, user, clock).orders
        if o.delivery_date >= clock.local_now().date()
    ]


@router.post("/orders/check", response_model=OrderCheckOut)
def check(body: OrderCheckIn, db: DbDep, user: StoreUser, clock: ClockDep) -> OrderCheckOut:
    return service.check(db, user, clock, body)


@router.post("/orders", response_model=list[OrderOut])
async def submit(
    body: OrderSubmitIn, db: DbDep, user: StoreUser, clock: ClockDep
) -> list[OrderOut]:
    out = service.submit(db, user, clock, body)
    outlet = service.outlet_for(db, user)
    await broker.publish(
        "order.placed",
        {"refs": [o.ref for o in out]},
        audience=lambda s: s.get("outlet") == outlet.code or s.get("depot") == outlet.depot,
    )
    return out


@router.post("/outlets/{code}/driver-note", response_model=DriverNoteOut)
async def driver_note(
    code: str, body: DriverNoteIn, db: DbDep, user: StoreUser, clock: ClockDep
) -> DriverNoteOut:
    service.outlet_for(db, user, code)
    note = DriverNote(
        outlet_code=code,
        for_date=clock.local_now().date(),
        text=body.text,
        sent_at=clock.now(),
        sent_by=user.id,
    )
    db.add(note)
    service.audit(db, user, clock, "driver_note.sent", "outlet", code, {"text": body.text})
    db.commit()
    return DriverNoteOut(text=note.text, sent_at=note.sent_at)


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(db: DbDep, user: StoreUser) -> list[NotificationOut]:
    return service.notices(db, user)


@router.get("/notifications/{notice_id}", response_model=NotificationOut)
def notification(
    notice_id: UUID, db: DbDep, user: StoreUser, language: Language | None = None
) -> NotificationOut:
    return service.notification_out(db, service.notice_for(db, user, notice_id), language)


@router.post("/notifications/{notice_id}/read", response_model=NotificationOut)
@router.post("/notifications/{notice_id}/ack", response_model=NotificationOut)
async def acknowledge(
    notice_id: UUID, db: DbDep, user: StoreUser, clock: ClockDep
) -> NotificationOut:
    notice = service.notice_for(db, user, notice_id, lock=True)
    if notice.acked_at is None:
        notice.acked_at = clock.now()
        service.audit(db, user, clock, "notification.read", "notification", str(notice.id), {})
        db.commit()
    out = service.notification_out(db, notice)
    await broker.publish(
        "notification.read",
        out.model_dump(mode="json"),
        audience=lambda s: s.get("outlet") == user.outlet_code,
    )
    return out
