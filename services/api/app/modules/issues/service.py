"""BR-51 commercial decisions; BR-52 count evidence remains append-only."""

import uuid
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import select

from app.core.clock import COLOMBO, Clock, ensure_utc
from app.core.errors import ConflictError, DomainError
from app.modules.auth.models import User
from app.modules.catalog.models import Outlet, OutletProfile, Product
from app.modules.issues.repository import Repository
from app.modules.issues.schemas import IssueItemOut, IssueOut, ResolveIn
from app.modules.ops.models import ExceptionItem, Notification
from app.modules.orders.models import Order, OrderLine
from app.modules.planning.models import Stop, StopOrder, Trip
from app.modules.receipts.models import Issue, IssueLine, Receipt
from app.modules.stream.broker import broker
from app.modules.sync.models import Event


def issue_out(repo: Repository, clock: Clock, issue: Issue) -> IssueOut:
    order = repo.db.get(Order, issue.order_id)
    assert order is not None
    outlet = repo.db.get(Outlet, order.outlet_code)
    assert outlet is not None
    event = repo.db.get(Event, issue.driver_event_id) if issue.driver_event_id else None
    driver = repo.db.get(User, event.actor_id) if event else None
    receipt = repo.db.scalar(select(Receipt).where(Receipt.order_id == order.id))
    store = repo.db.get(User, receipt.confirmed_by) if receipt else None
    profile = repo.db.get(OutletProfile, outlet.code)
    trip = repo.db.scalar(
        select(Trip)
        .join(Stop)
        .join(StopOrder)
        .where(StopOrder.order_id == order.id)
        .order_by(Trip.version_id)
        .limit(1)
    )
    vehicle = driver.vehicle_code if driver else (trip.vehicle_code if trip else None)
    items: list[IssueItemOut] = []
    problems = {line.order_line_id: line for line in issue.lines if line.order_line_id}
    receipt_lines = {line.order_line_id: line for line in receipt.lines} if receipt else {}
    for line in order.lines:
        product = repo.db.get(Product, line.product_id)
        problem = problems.get(line.id)
        items.append(
            IssueItemOut(
                product_id=line.product_id,
                name=product.name if product else line.product_id,
                driver_qty=receipt_lines[line.id].driver_qty
                if line.id in receipt_lines
                else line.qty_delivered,
                problem=problem.problem if problem else None,
                problem_qty=problem.qty if problem else 0,
                photo_url=problem.photo_url if problem else None,
            )
        )
    for reported in issue.lines:
        if reported.order_line_id in problems:
            continue
        product = repo.db.get(Product, reported.product_id) if reported.product_id else None
        items.append(
            IssueItemOut(
                product_id=reported.product_id,
                name=product.name if product else "Reported cases",
                driver_qty=issue.driver_qty,
                problem=reported.problem,
                problem_qty=reported.qty,
                photo_url=reported.photo_url,
            )
        )
    now = clock.local_now()
    due = datetime.combine(now.date(), time(9), tzinfo=COLOMBO)
    if due <= now:
        due += timedelta(days=1)
    return IssueOut(
        id=issue.id,
        kind=issue.kind,
        status=issue.status,
        order_ref=order.ref,
        outlet_code=outlet.code,
        district=outlet.district,
        temp_requirement=order.temp_requirement,
        vehicle_code=vehicle,
        driver_record_id=event.event_id if event else None,
        driver_recorded_at=ensure_utc(event.event_time) if event else None,
        driver_uploaded_at=ensure_utc(event.received_at) if event else None,
        driver_name=driver.name if driver else None,
        driver_photo_url=event.payload.get("photo_url") if event else None,
        store_recorded_at=ensure_utc(receipt.confirmed_at if receipt else issue.opened_at),
        store_name=store.name if store else (profile.contact_name if profile else None),
        store_photo_url=issue.store_photo_url
        or next((line.photo_url for line in issue.lines if line.photo_url), None),
        opened_at=ensure_utc(issue.opened_at),
        driver_qty=issue.driver_qty,
        store_qty=issue.store_qty,
        items=items,
        affected_cases=sum(line.qty for line in issue.lines),
        next_run=repo.next_operating_date(order.delivery_date),
        window_open=outlet.window_open,
        window_close=outlet.window_close,
        recount_due=due,
        resolution=issue.resolution,
        note=issue.note,
        resolved_at=ensure_utc(issue.resolved_at) if issue.resolved_at else None,
    )


async def resolve(
    repo: Repository, user: User, clock: Clock, identifier: uuid.UUID, body: ResolveIn
) -> IssueOut:
    issue = repo.issue(identifier, lock=True)
    if issue.status != "open":
        raise ConflictError("ISSUE_RESOLVED", "This issue already has a decision")
    allowed = {
        "store_report": {"redeliver", "credit", "reject"},
        "count_conflict": {"driver_stands", "store_stands", "recount"},
    }
    rule = "BR-51" if issue.kind == "store_report" else "BR-52"
    if body.resolution not in allowed.get(issue.kind, set()):
        raise DomainError(
            "INVALID_RESOLUTION", "Choose a decision for this issue type", rule_id=rule
        )
    note = (body.note or "").strip() or None
    if body.resolution == "reject" and not note:
        raise DomainError(
            "REJECTION_REASON_REQUIRED", "Write a reason for rejecting this report", rule_id="BR-51"
        )
    order = repo.db.get(Order, issue.order_id)
    assert order is not None
    details = issue_out(repo, clock, issue)
    future: Order | None = None
    next_day = details.next_run
    if body.resolution == "redeliver":
        if next_day is None:
            raise DomainError(
                "NEXT_RUN_REQUIRED", "No next operating run is available", rule_id=rule
            )
        qty = details.affected_cases
        if not 0 < qty <= order.units:
            raise DomainError(
                "INVALID_CLAIM_QUANTITY", "The reported quantity needs review", rule_id=rule
            )
        ratio = qty / order.units
        future = Order(
            ref=f"I-{issue.id.hex[:16]}",
            outlet_code=order.outlet_code,
            brand=order.brand,
            temp_requirement=order.temp_requirement,
            delivery_date=next_day,
            units=qty,
            weight_kg=float(order.weight_kg) * ratio,
            volume_m3=float(order.volume_m3) * ratio,
            status="placed",
            source="app",
            deferred_yesterday=True,
            days_since_last_served=order.days_since_last_served + 1,
            placed_by=user.id,
            placed_at=clock.now(),
        )
        repo.db.add(future)
        repo.db.flush()
        for line in issue.lines:
            if line.product_id:
                repo.db.add(
                    OrderLine(order_id=future.id, product_id=line.product_id, qty_ordered=line.qty)
                )
    short_claim: Issue | None = None
    if body.resolution == "store_stands":
        if issue.driver_qty is None or issue.store_qty is None:
            raise DomainError("COUNTS_REQUIRED", "Both original counts are required", rule_id=rule)
        difference = issue.driver_qty - issue.store_qty
        if difference > 0:
            short_claim = Issue(
                order_id=issue.order_id,
                kind="store_report",
                status="open",
                driver_event_id=issue.driver_event_id,
                driver_qty=issue.driver_qty,
                store_qty=issue.store_qty,
                store_photo_url=issue.store_photo_url,
                opened_at=clock.now(),
                note=f"Short claim from {issue.id}",
            )
            repo.db.add(short_claim)
            repo.db.flush()
            repo.db.add(IssueLine(issue_id=short_claim.id, problem="missing", qty=difference))
            repo.db.add(
                ExceptionItem(
                    kind="store_report",
                    impact=difference,
                    title=f"{order.outlet_code} · {difference}-case short claim",
                    detail="Store count stands · review the commercial decision",
                    entity_type="issue",
                    entity_id=str(short_claim.id),
                    suggested_fix={"action": "review_report"},
                    status="open",
                    created_at=clock.now(),
                )
            )
    issue.status = "resolved"
    issue.resolution = body.resolution
    issue.note = note
    issue.resolved_by = user.id
    issue.resolved_at = clock.now()
    damage: list[dict[str, Any]] = [
        {"product_id": line.product_id, "qty": line.qty, "problem": line.problem}
        for line in issue.lines
        if line.problem in {"damaged", "warm"}
    ]
    payload = {
        "issue_id": str(issue.id),
        "resolution": body.resolution,
        "note": note,
        "rule_id": rule,
        "redelivery_order_id": str(future.id) if future else None,
        "short_claim_id": str(short_claim.id) if short_claim else None,
        "driver_qty": issue.driver_qty,
        "store_qty": issue.store_qty,
        "credit_cases": details.affected_cases if body.resolution == "credit" else 0,
        "pick_note": damage,
        "pick_date": next_day.isoformat() if next_day else None,
        "recount_due": details.recount_due.isoformat() if body.resolution == "recount" else None,
    }
    event = repo.db.get(Event, issue.driver_event_id) if issue.driver_event_id else None
    drivers = (
        {event.actor_id}
        if event
        else {
            driver.id
            for driver in repo.db.scalars(
                select(User).where(User.role == "driver", User.vehicle_code == details.vehicle_code)
            )
        }
        if details.vehicle_code
        else set()
    )
    if not drivers:
        raise DomainError(
            "DRIVER_RECORD_REQUIRED",
            "Link the driver's record or assigned vehicle before notifying both sides",
            rule_id=rule,
        )
    labels = {
        "redeliver": "Redeliver on the next run",
        "credit": "Credit the store",
        "reject": "Report rejected",
        "driver_stands": "Driver’s count stands",
        "store_stands": "Store count stands",
        "recount": "Recount requested",
    }
    text = labels[body.resolution] + (f" · {note}" if note else "")
    repo.db.add(
        Notification(
            outlet_code=order.outlet_code,
            order_id=order.id,
            kind="decision",
            lang="en",
            title=labels[body.resolution],
            body=text,
            data=payload,
            created_at=clock.now(),
        )
    )
    for driver_id in drivers:
        repo.db.add(
            Notification(
                recipient_user_id=driver_id,
                order_id=order.id,
                kind="decision",
                lang="en",
                title=labels[body.resolution],
                body=text,
                data=payload,
                created_at=clock.now(),
            )
        )
    for loader in repo.db.scalars(
        select(User).where(User.role == "loader", User.depot == repo.depot)
    ):
        if damage:
            repo.db.add(
                Notification(
                    recipient_user_id=loader.id,
                    order_id=order.id,
                    kind="decision",
                    lang="en",
                    title="Damaged-stock pick note",
                    body=f"{order.outlet_code}: {sum(d['qty'] for d in damage)} cases "
                    "reported damaged or warm · review the next pick",
                    data=payload,
                    created_at=clock.now(),
                )
            )
    repo.db.add(
        Event(
            event_id=uuid.uuid4(),
            type="issue.resolved",
            actor_id=user.id,
            plan_version_id=event.plan_version_id if event else None,
            entity_type="issue",
            entity_id=str(issue.id),
            payload=payload,
            event_time=clock.now(),
            received_at=clock.now(),
        )
    )
    for exception in repo.db.scalars(
        select(ExceptionItem).where(
            ExceptionItem.entity_type == "issue",
            ExceptionItem.entity_id == str(issue.id),
            ExceptionItem.status == "open",
        )
    ):
        exception.status = "resolved"
    repo.db.commit()
    recipients = {str(d) for d in drivers}
    await broker.publish(
        "issue.resolved",
        payload,
        audience=lambda s: (
            (s.get("role") == "dispatcher" and s.get("depot") == repo.depot)
            or s.get("user_id") in recipients
            or s.get("outlet") == order.outlet_code
        ),
    )
    return issue_out(repo, clock, issue)
