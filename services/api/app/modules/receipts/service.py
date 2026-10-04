"""Store acceptance and item problems (BR-46/47); never overwrite driver evidence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import COLOMBO, Clock, ensure_utc
from app.core.errors import ConflictError, DomainError
from app.modules.auth.models import User
from app.modules.catalog.models import Product
from app.modules.ops.models import ExceptionItem
from app.modules.orders import service as orders
from app.modules.orders.models import Order
from app.modules.receipts.models import Issue, IssueLine, Receipt, ReceiptLine
from app.modules.receipts.schemas import (
    IssueIn,
    IssueOut,
    ReceiptDraftLine,
    ReceiptDraftOut,
    ReceiptIn,
    ReceiptOut,
)
from app.modules.sync.models import Event


def draft(db: Session, user: User, clock: Clock, order: Order) -> ReceiptDraftOut:
    view = orders.order_out(db, order, clock)
    tracks = view.tracking
    outcome = None
    for track in tracks:
        stop = db.get(orders.Stop, track.stop_id)
        if stop:
            found = [e for e in orders.stop_events(db, stop) if e.type == "outcome_recorded"]
            if found:
                outcome = found[-1]
    payload = outcome.payload if outcome else {}
    # Full handover can supply the ordered breakdown; partial counts require item evidence.
    full = (
        str(payload.get("outcome", "")).lower() == "delivered"
        and int(payload.get("cases_handed_over", payload.get("qty_delivered", order.units)))
        == order.units
    )
    counts = {
        str(x.get("order_line_id")): x.get("qty_delivered", x.get("qty"))
        for x in payload.get("lines", [])
        if isinstance(x, dict)
    }
    lines = []
    for line in order.lines:
        qty = line.qty_delivered
        if qty is None and counts.get(str(line.id)) is not None:
            qty = int(counts[str(line.id)] or 0)
        if qty is None and full:
            qty = line.qty_ordered
        product = db.get(Product, line.product_id)
        lines.append(
            ReceiptDraftLine(
                order_line_id=line.id,
                product_id=line.product_id,
                name=product.name if product else line.product_id,
                ordered_qty=line.qty_ordered,
                driver_qty=qty,
                store_qty=line.qty_received if line.qty_received is not None else qty,
            )
        )
    confirmed = db.scalar(select(Receipt.id).where(Receipt.order_id == order.id)) is not None
    return ReceiptDraftOut(
        order_ref=order.ref,
        outlet_code=order.outlet_code,
        vehicle_code=tracks[0].vehicle_code if tracks else None,
        delivered_at=ensure_utc(outcome.event_time).astimezone(COLOMBO) if outcome else None,
        receiver=payload.get("receiver_name"),
        photo_url=payload.get("photo_url"),
        confirmed=confirmed,
        can_confirm=bool(lines) and all(line.driver_qty is not None for line in lines),
        total_cases=sum(line.driver_qty or 0 for line in lines),
        lines=lines,
    )


def receipt_out(db: Session, order: Order, receipt: Receipt) -> ReceiptOut:
    issue = db.scalar(
        select(Issue).where(Issue.order_id == order.id).order_by(Issue.opened_at).limit(1)
    )
    return ReceiptOut(
        id=receipt.id,
        order_ref=order.ref,
        total_cases=receipt.total_cases,
        confirmed_at=ensure_utc(receipt.confirmed_at).astimezone(COLOMBO),
        issue_id=issue.id if issue else None,
    )


def create_receipt(
    db: Session,
    user: User,
    clock: Clock,
    order: Order,
    counts: dict[uuid.UUID, int],
    driver_counts: dict[uuid.UUID, int],
) -> Receipt:
    receipt = Receipt(
        order_id=order.id,
        confirmed_by=user.id,
        confirmed_at=clock.now(),
        total_cases=sum(counts.values()),
    )
    db.add(receipt)
    db.flush()
    for line in order.lines:
        qty = counts[line.id]
        db.add(
            ReceiptLine(
                receipt_id=receipt.id,
                order_line_id=line.id,
                driver_qty=driver_counts[line.id],
                store_qty=qty,
            )
        )
        line.qty_received = qty
    orders.audit(
        db,
        user,
        clock,
        "receipt.confirmed",
        "order",
        str(order.id),
        {
            "receipt_id": str(receipt.id),
            "total_cases": receipt.total_cases,
            "lines": [{"order_line_id": str(k), "store_qty": v} for k, v in counts.items()],
        },
    )
    return receipt


def confirm(db: Session, user: User, clock: Clock, ref: str, body: ReceiptIn) -> ReceiptOut:
    order = orders.order_for(db, user, ref, lock=True)
    prior = db.scalar(select(Receipt).where(Receipt.order_id == order.id))
    if prior:
        if body.lines is not None:
            requested = {line.order_line_id: line.store_qty for line in body.lines}
            existing = {line.order_line_id: line.store_qty for line in prior.lines}
            if len(requested) != len(body.lines) or requested != existing:
                raise ConflictError(
                    "RECEIPT_ALREADY_CONFIRMED",
                    "The receipt is confirmed; report an item problem instead",
                    rule_id="BR-46",
                )
        return receipt_out(db, order, prior)
    view = draft(db, user, clock, order)
    if not view.can_confirm and body.lines is None:
        raise DomainError(
            "DRIVER_COUNTS_PENDING", "Driver item counts have not arrived yet", rule_id="BR-46"
        )
    driver = {line.order_line_id: line.driver_qty for line in view.lines}
    if body.lines is None:
        counts = {key: value for key, value in driver.items() if value is not None}
    else:
        counts = {line.order_line_id: line.store_qty for line in body.lines}
        if len(counts) != len(body.lines) or set(counts) != {line.id for line in order.lines}:
            raise DomainError(
                "INVALID_RECEIPT_LINES", "Confirm each item exactly once", rule_id="BR-46"
            )
    # Offline receipt may precede sync; preserve ordered baseline and later driver evidence (BR-52).
    driver_counts = {
        line.id: int(driver[line.id] or 0) if driver.get(line.id) is not None else line.qty_ordered
        for line in order.lines
    }
    receipt = create_receipt(db, user, clock, order, counts, driver_counts)
    changed = any(
        driver.get(key) is not None and value != driver[key] for key, value in counts.items()
    )
    if changed:
        db.add(
            Issue(
                order_id=order.id,
                kind="count_conflict",
                status="open",
                opened_at=clock.now(),
                driver_qty=sum(driver_counts.values()),
                store_qty=sum(counts.values()),
            )
        )
    db.commit()
    return receipt_out(db, order, receipt)


def report(db: Session, user: User, clock: Clock, ref: str, body: IssueIn) -> IssueOut:
    order = orders.order_for(db, user, ref, lock=True)
    fingerprint = body.model_dump(mode="json")
    prior = db.get(Event, body.request_id)
    if prior:
        if (
            prior.actor_id != user.id
            or prior.type != "store_report.created"
            or prior.entity_id != str(order.id)
            or prior.payload.get("request") != fingerprint
        ):
            raise ConflictError(
                "IDEMPOTENCY_CONFLICT", "This request id was used for another report"
            )
        issue = db.get(Issue, uuid.UUID(prior.payload["issue_id"]))
        assert issue is not None
        return IssueOut(
            id=issue.id,
            order_ref=ref,
            status=issue.status,
            receipt_id=uuid.UUID(prior.payload["receipt_id"]),
        )
    by_id = {line.id: line for line in order.lines}
    totals: dict[uuid.UUID, int] = {}
    seen: set[tuple[uuid.UUID, str]] = set()
    for entry in body.lines:
        line = by_id.get(entry.order_line_id)
        if line is None or (entry.order_line_id, entry.problem) in seen:
            raise DomainError(
                "INVALID_ISSUE_LINE",
                "Select an item from this order once per problem",
                rule_id="BR-47",
            )
        product = db.get(Product, line.product_id)
        if entry.problem == "warm" and product and not product.is_chilled:
            raise DomainError(
                "DRY_ITEM_WARM", "Only chilled items can arrive warm", rule_id="BR-47"
            )
        seen.add((entry.order_line_id, entry.problem))
        totals[line.id] = totals.get(line.id, 0) + entry.qty
        if totals[line.id] > line.qty_ordered:
            raise DomainError(
                "ISSUE_QUANTITY", "Problem count exceeds the ordered item count", rule_id="BR-47"
            )
    view = draft(db, user, clock, order)
    receipt = db.scalar(select(Receipt).where(Receipt.order_id == order.id))
    if not receipt and not view.can_confirm:
        raise DomainError(
            "DRIVER_COUNTS_PENDING",
            "Wait for the driver item counts before reporting",
            rule_id="BR-46",
        )
    if receipt is None:
        driver = {line.order_line_id: int(line.driver_qty or 0) for line in view.lines}
        # BR-47: confirm good cases; a bad line does not block the whole receipt.
        receipt = create_receipt(
            db,
            user,
            clock,
            order,
            {key: max(0, qty - totals.get(key, 0)) for key, qty in driver.items()},
            driver,
        )
    issue = Issue(
        order_id=order.id,
        kind="store_report",
        status="open",
        opened_at=clock.now(),
        driver_qty=view.total_cases,
        store_qty=receipt.total_cases,
        store_photo_url=view.photo_url,
    )
    db.add(issue)
    db.flush()
    for entry in body.lines:
        db.add(
            IssueLine(
                issue_id=issue.id,
                order_line_id=entry.order_line_id,
                product_id=by_id[entry.order_line_id].product_id,
                problem=entry.problem,
                qty=entry.qty,
                photo_url=entry.photo_url,
            )
        )
    db.add(
        ExceptionItem(
            kind="store_report",
            impact=sum(totals.values()),
            title=f"Store report · {order.ref}",
            entity_type="issue",
            entity_id=str(issue.id),
            created_at=clock.now(),
            suggested_fix={"issue_id": str(issue.id)},
        )
    )
    orders.audit(
        db,
        user,
        clock,
        "store_report.created",
        "order",
        str(order.id),
        {"issue_id": str(issue.id), "receipt_id": str(receipt.id), "request": fingerprint},
        body.request_id,
    )
    db.commit()
    return IssueOut(id=issue.id, order_ref=ref, status=issue.status, receipt_id=receipt.id)
