"""Separate store acceptance and D10 item reports (BR-46/47)."""

from fastapi import APIRouter

from app.core.deps import ClockDep, DbDep
from app.modules.orders import service as orders
from app.modules.orders.router import StoreUser
from app.modules.receipts import service
from app.modules.receipts.schemas import (
    IssueIn,
    IssueOut,
    IssuePreviewOut,
    ReceiptDraftOut,
    ReceiptIn,
    ReceiptOut,
)
from app.modules.stream.broker import broker

router = APIRouter(tags=["receipts"])


@router.get("/orders/{ref}/receipt-draft", response_model=ReceiptDraftOut)
def draft(ref: str, db: DbDep, user: StoreUser, clock: ClockDep) -> ReceiptDraftOut:
    return service.draft(db, user, clock, orders.order_for(db, user, ref))


@router.post("/orders/{ref}/receipt", response_model=ReceiptOut)
async def confirm(
    ref: str, body: ReceiptIn, db: DbDep, user: StoreUser, clock: ClockDep
) -> ReceiptOut:
    out = service.confirm(db, user, clock, ref, body)
    await broker.publish(
        "receipt.confirmed",
        out.model_dump(mode="json"),
        audience=lambda s: s.get("outlet") == user.outlet_code,
    )
    return out


@router.post("/orders/{ref}/issues", response_model=IssueOut)
async def report(ref: str, body: IssueIn, db: DbDep, user: StoreUser, clock: ClockDep) -> IssueOut:
    out = service.report(db, user, clock, ref, body)
    outlet = orders.outlet_for(db, user)
    await broker.publish(
        "exception.created",
        out.model_dump(mode="json"),
        audience=lambda s: s.get("outlet") == outlet.code or s.get("depot") == outlet.depot,
    )
    return out


@router.post("/orders/{ref}/issues/check", response_model=IssuePreviewOut)
def check_report(
    ref: str, body: IssueIn, db: DbDep, user: StoreUser, clock: ClockDep
) -> IssuePreviewOut:
    order = orders.order_for(db, user, ref)
    view = service.draft(db, user, clock, order)
    _, _, good = service.report_counts(db, order, body, view)
    return IssuePreviewOut(good_cases=sum(good.values()))
