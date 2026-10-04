"""Generate, confirm and publish with engine gates and immutable versions."""

import uuid
from dataclasses import asdict
from datetime import UTC, date, datetime, time, timedelta
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from xora_engine import Assignment, Problem, validate
from xora_engine import plan as engine_plan
from xora_engine.fuel import trip_litres

from app.core.clock import COLOMBO, Clock, ensure_utc
from app.core.errors import ConflictError, DomainError, ForbiddenError, NotFoundError
from app.modules.auth.models import User
from app.modules.catalog.models import CalendarDay, Outlet
from app.modules.ops.models import Notification
from app.modules.orders.models import Order
from app.modules.planning import adapter
from app.modules.planning.models import Deferral, Plan, PlanVersion, Stop, StopOrder, Trip
from app.modules.planning.repository import Repository
from app.modules.planning.schemas import (
    ConfirmIn,
    DeferralOut,
    FleetOut,
    PlanOut,
    PublishCheckOut,
    ServeInsteadOut,
    StopOrderOut,
    StopOut,
    TripOut,
    ViolationOut,
)
from app.modules.stream.broker import broker
from app.modules.sync.models import Event


def repository(db: Session, user: User) -> Repository:
    if not user.depot:
        raise ForbiddenError("DEPOT_REQUIRED", "Your account needs a depot", rule_id="BR-55")
    return Repository(db, user.depot)


def require_draft(version: PlanVersion) -> None:
    if version.status != "draft":
        raise ConflictError(
            "IMMUTABLE_VERSION", "A published plan cannot be changed", rule_id="BR-23"
        )


def audit(
    repo: Repository,
    user: User,
    clock: Clock,
    kind: str,
    version: PlanVersion,
    payload: dict[str, Any],
) -> None:
    now = clock.now()
    repo.db.add(
        Event(
            event_id=uuid.uuid4(),
            type=kind,
            actor_id=user.id,
            device_id=None,
            plan_version_id=version.id,
            entity_type="plan_version",
            entity_id=str(version.id),
            payload=payload,
            event_time=now,
            received_at=now,
        )
    )


def generate(
    repo: Repository,
    user: User,
    clock: Clock,
    operating_date: date,
    force_order_ref: str | None = None,
) -> PlanVersion:
    cutoff = datetime.combine(operating_date - timedelta(days=1), time(16), tzinfo=COLOMBO)
    if clock.now() < cutoff:
        raise DomainError(
            "ORDERS_OPEN", "Orders have not closed for this operating day", rule_id="BR-40"
        )
    calendar = repo.db.get(CalendarDay, operating_date)
    if calendar is None or not calendar.is_operating:
        raise DomainError("NON_OPERATING_DAY", "Choose an operating day from the calendar")
    plan = repo.plan(operating_date, lock=True)
    if plan is None:
        plan = Plan(depot=repo.depot, operating_date=operating_date)
        repo.db.add(plan)
        repo.db.flush()
    previous = repo.latest(plan.id)
    # Dataset draft fallback promised by docs/09: never place a user's unfinished app draft.
    drafts = repo.db.scalars(
        select(Order)
        .join(Outlet, Order.outlet_code == Outlet.code)
        .where(
            Outlet.depot == repo.depot,
            Order.delivery_date == operating_date,
            Order.status == "draft",
            Order.source == "dataset",
        )
    )
    for order in drafts:
        order.status = "placed"
        order.placed_at = clock.now()
    repo.db.flush()
    problem = adapter.load_problem(repo, operating_date=operating_date)
    locks = (
        tuple(t for t in adapter.load_assignment(previous, repo).trips if t.locked)
        if previous
        else ()
    )
    started = perf_counter()
    try:
        result = engine_plan(problem, locks=locks, force_order_ref=force_order_ref)
    except ValueError as exc:
        raise DomainError("PLAN_INFEASIBLE", str(exc)) from exc
    elapsed = round((perf_counter() - started) * 1000)
    version = PlanVersion(
        plan_id=plan.id,
        number=previous.number + 1 if previous else 1,
        status="draft",
        parent_version_id=previous.id if previous else None,
        created_by=user.id,
        created_at=clock.now(),
        solver_status=result.solver_status,
        solve_ms=elapsed,
        kpis=asdict(result.kpis),
        bottleneck=asdict(result.bottleneck),
    )
    repo.db.add(version)
    repo.db.flush()
    by_ref = {o.ref: o for o in repo.orders(operating_date)}
    windows = {s.order_ref: s for s in result.likely_stops}
    for engine_trip in result.trips:
        orders = [problem.orders[s.order_ref] for s in engine_trip.stops]
        trip = Trip(
            version_id=version.id,
            vehicle_code=engine_trip.vehicle,
            trip_no=engine_trip.trip_no,
            brand=orders[0].brand,
            district=orders[0].district,
            lane="predawn" if orders[0].brand == "Fresh" else "daytime",
            planned_depart=adapter.as_time(engine_trip.planned_depart),
            plan_minutes=engine_trip.plan_minutes,
            litres=trip_litres(orders, problem.vehicles[engine_trip.vehicle], problem),
            weight_kg=sum(o.weight_kg for o in orders),
            volume_m3=sum(o.volume_m3 for o in orders),
            locked=engine_trip.locked,
        )
        repo.db.add(trip)
        repo.db.flush()
        for seq, engine_stop in enumerate(engine_trip.stops, 1):
            row = by_ref[engine_stop.order_ref]
            likely = windows[row.ref]
            stop = Stop(
                trip_id=trip.id,
                seq=seq,
                outlet_code=row.outlet_code,
                plan_arrival=adapter.as_time(likely.plan_arrival),
                likely_from=adapter.as_time(likely.likely_from),
                likely_to=adapter.as_time(likely.likely_to),
                at_risk=likely.at_risk,
                status="planned",
            )
            repo.db.add(stop)
            repo.db.flush()
            repo.db.add(StopOrder(stop_id=stop.id, order_id=row.id, planned_cases=row.units))
    next_run = repo.next_operating_date(operating_date)
    for deferred in result.deferrals:
        repo.db.add(
            Deferral(
                version_id=version.id,
                order_id=by_ref[deferred.order_ref].id,
                reason_code=deferred.reason_code,
                group=deferred.group,
                priority=deferred.priority,
                displaces=list(deferred.displaces),
                explanation=deferred.explanation,
                next_run=datetime.combine(next_run, time(3, 30), tzinfo=COLOMBO).astimezone(UTC)
                if next_run
                else None,
            )
        )
    audit(
        repo,
        user,
        clock,
        "plan.generated",
        version,
        {"solver": result.solver_status, "forced_order": force_order_ref},
    )
    repo.db.commit()
    return repo.version(version.id)


def plan_out(repo: Repository, version: PlanVersion) -> PlanOut:
    by_id = {o.id: o for o in repo.orders(version.plan.operating_date, include_completed=True)}
    outlets = {o.code: o for o in repo.outlets()}
    problem = adapter.load_problem(repo, version, include_completed=True)
    assignment = adapter.load_assignment(version, repo)
    return PlanOut(
        id=version.id,
        plan_id=version.plan_id,
        number=version.number,
        operating_date=version.plan.operating_date,
        depot=repo.depot,
        status=version.status,
        solver_status=version.solver_status,
        solve_ms=version.solve_ms,
        kpis=version.kpis,
        bottleneck=version.bottleneck,
        orders_total=len(
            {so.order_id for t in version.trips for s in t.stops for so in s.orders}
            | {d.order_id for d in version.deferrals}
        ),
        chilled_total=sum(
            by_id[order_id].temp_requirement == "chilled"
            for order_id in {so.order_id for t in version.trips for s in t.stops for so in s.orders}
            | {d.order_id for d in version.deferrals}
        ),
        trips=[
            TripOut(
                id=t.id,
                vehicle_code=t.vehicle_code,
                trip_no=t.trip_no,
                brand=t.brand,
                district=t.district,
                lane=t.lane,
                planned_depart=t.planned_depart,
                plan_minutes=t.plan_minutes,
                litres=float(t.litres),
                weight_kg=float(t.weight_kg),
                volume_m3=float(t.volume_m3),
                locked=t.locked,
                stops=[
                    StopOut(
                        id=s.id,
                        seq=s.seq,
                        outlet_code=s.outlet_code,
                        plan_arrival=s.plan_arrival,
                        likely_from=s.likely_from,
                        likely_to=s.likely_to,
                        at_risk=s.at_risk,
                        status=s.status,
                        orders=[
                            StopOrderOut(
                                order_ref=by_id[so.order_id].ref,
                                cases=so.planned_cases,
                                top_up_of_order_ref=by_id[so.top_up_of_order_id].ref
                                if so.top_up_of_order_id
                                else None,
                            )
                            for so in s.orders
                        ],
                    )
                    for s in t.stops
                ],
                rule_messages=[]
                if version.solver_status == "REPAIR"
                else trip_rule_messages(problem, assignment, t),
                protected_outlets=sorted(
                    {
                        s.outlet_code
                        for s in t.stops
                        for so in s.orders
                        if by_id[so.order_id].deferred_yesterday
                        or by_id[so.order_id].days_since_last_served >= 3
                    }
                ),
            )
            for t in version.trips
        ],
        deferrals=[
            DeferralOut(
                id=d.id,
                order_ref=by_id[d.order_id].ref,
                outlet_code=by_id[d.order_id].outlet_code,
                reason_code=d.reason_code,
                group=d.group,
                priority=float(d.priority),
                explanation=d.explanation,
                displaces=d.displaces,
                # BR-15/BR-21: UTC 22:00 is the next day's 03:30 Colombo run.
                next_run=ensure_utc(d.next_run).astimezone(COLOMBO).date() if d.next_run else None,
                repeat_skip=by_id[d.order_id].deferred_yesterday
                or by_id[d.order_id].days_since_last_served >= 3,
                confirmed=d.confirmed_by is not None,
                confirm_reason=d.confirm_reason,
                district=outlets[by_id[d.order_id].outlet_code].district,
                temp_requirement=by_id[d.order_id].temp_requirement,
                volume_m3=float(by_id[d.order_id].volume_m3),
                weight_kg=float(by_id[d.order_id].weight_kg),
                notice_body=deferral_notice(d, by_id[d.order_id]),
                notice_language="en",
            )
            for d in version.deferrals
        ],
    )


def deferral_notice(deferred: Deferral, order: Order) -> str:
    """BR-21: preview and delivered notification use the identical server template."""
    next_label = (
        ensure_utc(deferred.next_run).astimezone(COLOMBO).isoformat()
        if deferred.next_run
        else "to be confirmed"
    )
    return (
        f"{order.ref}: {deferred.explanation or deferred.reason_code}. "
        f"Next run: {next_label}. Written from the plan."
    )


def trip_rule_messages(problem: Problem, assignment: Assignment, trip: Trip) -> list[ViolationOut]:
    """Explain why an order on the next trip cannot join this trip (BR-06)."""
    from dataclasses import replace

    from xora_engine import Assignment
    from xora_engine import Stop as EngineStop
    from xora_engine.rules import capacity_violations

    target = next(
        t for t in assignment.trips if t.vehicle == trip.vehicle_code and t.trip_no == trip.trip_no
    )
    messages: list[ViolationOut] = []
    for other in assignment.trips:
        if other.vehicle != target.vehicle or other.trip_no == target.trip_no:
            continue
        for stop in other.stops:
            order = problem.orders[stop.order_ref]
            if order.brand != trip.brand or order.district != trip.district:
                continue
            candidate = replace(target, stops=(*target.stops, EngineStop(order.ref, order.units)))
            for violation in capacity_violations(Assignment((candidate,)), problem):
                messages.append(
                    ViolationOut(
                        rule_id=violation.rule_id,
                        code=violation.code,
                        message=f"{order.outlet} won’t fit: " + violation.message.split(": ", 1)[1],
                        context=dict(violation.context),
                    )
                )
    return messages


def serve_instead(
    repo: Repository, user: User, clock: Clock, deferral_id: uuid.UUID, apply: bool
) -> ServeInsteadOut:
    deferred = repo.db.get(Deferral, deferral_id)
    if deferred is None:
        raise NotFoundError("DEFERRAL_NOT_FOUND", "Deferral not found")
    version = repo.version(deferred.version_id, lock=True)
    require_draft(version)
    latest = repo.latest(version.plan_id)
    if latest is None or latest.id != version.id:
        raise ConflictError(
            "STALE_DRAFT", "Reopen the latest draft before replacing an order", rule_id="BR-23"
        )
    order = repo.db.get(Order, deferred.order_id)
    assert order is not None
    problem = adapter.load_problem(repo, version)
    assignment = adapter.load_assignment(version, repo)
    locks = tuple(t for t in assignment.trips if t.locked)
    try:
        result = engine_plan(problem, locks=locks, force_order_ref=order.ref)
    except ValueError as exc:
        raise DomainError("CANNOT_SERVE_INSTEAD", str(exc), rule_id="BR-16") from exc
    served_before = {s.order_ref for t in assignment.trips for s in t.stops}
    served_after = {s.order_ref for t in result.trips for s in t.stops}
    displaced = sorted(served_before - served_after)
    replacement = (
        generate(repo, user, clock, version.plan.operating_date, force_order_ref=order.ref)
        if apply
        else None
    )
    return ServeInsteadOut(
        order_ref=order.ref,
        displaces=displaced,
        version=plan_out(repo, replacement) if replacement else None,
    )


def confirm(
    repo: Repository, user: User, clock: Clock, version_id: uuid.UUID, body: ConfirmIn
) -> PlanVersion:
    version = repo.version(version_id, lock=True)
    require_draft(version)
    by_id = {d.id: d for d in version.deferrals}
    seen: set[uuid.UUID] = set()
    for item in body.items:
        if item.deferral_id not in by_id or item.deferral_id in seen:
            raise DomainError("INVALID_DEFERRAL", "Choose each deferral from this version once")
        seen.add(item.deferral_id)
        order = repo.db.get(Order, by_id[item.deferral_id].order_id)
        assert order is not None
        if (order.deferred_yesterday or order.days_since_last_served >= 3) and not (
            item.reason or ""
        ).strip():
            raise DomainError(
                "REPEAT_SKIP_REASON",
                f"{order.ref}: write a reason for another deferral",
                rule_id="BR-21",
            )
    for item in body.items:
        deferred = by_id[item.deferral_id]
        deferred.confirmed_by = user.id
        deferred.confirmed_at = clock.now()
        deferred.confirm_reason = (item.reason or "").strip() or None
    audit(
        repo,
        user,
        clock,
        "deferrals.confirmed",
        version,
        {"items": body.model_dump(mode="json")["items"]},
    )
    repo.db.commit()
    return version


def publish_check(repo: Repository, version: PlanVersion) -> PublishCheckOut:
    if version.status != "draft":
        return PublishCheckOut(
            can_publish=False,
            violations=[
                ViolationOut(
                    rule_id="BR-23",
                    code="IMMUTABLE_VERSION",
                    message="A published plan cannot be changed",
                    context={},
                )
            ],
            unconfirmed_deferrals=[],
            late_risk_order_refs=[],
        )
    problem = adapter.load_problem(repo, version)
    assignment = adapter.load_assignment(version, repo)
    violations = [
        ViolationOut(rule_id=v.rule_id, code=v.code, message=v.message, context=dict(v.context))
        for v in validate(assignment, problem)
    ]
    assigned = {s.order_ref for t in assignment.trips for s in t.stops}
    deferred: set[str] = set()
    for item in version.deferrals:
        order = repo.db.get(Order, item.order_id)
        assert order is not None
        deferred.add(order.ref)
    if assigned & deferred or assigned | deferred != set(problem.orders):
        violations.append(
            ViolationOut(
                rule_id="BR-05",
                code="INCOMPLETE_PLAN",
                message="Every order needs exactly one served or deferred decision",
                context={},
            )
        )
    latest = repo.latest(version.plan_id)
    if version.status != "draft" or latest is None or latest.id != version.id:
        violations.append(
            ViolationOut(
                rule_id="BR-23",
                code="STALE_DRAFT",
                message="Only the latest draft can be published",
                context={},
            )
        )
    unconfirmed = [d.id for d in version.deferrals if d.confirmed_by is None]
    late = [
        so.order_ref
        for t in plan_out(repo, version).trips
        for s in t.stops
        if s.at_risk
        for so in s.orders
    ]
    return PublishCheckOut(
        can_publish=not violations and not unconfirmed,
        violations=violations,
        unconfirmed_deferrals=unconfirmed,
        late_risk_order_refs=late,
    )


async def publish(
    repo: Repository, user: User, clock: Clock, version_id: uuid.UUID, accept_late_risk: bool
) -> PlanVersion:
    version = repo.version(version_id, lock=True)
    require_draft(version)
    repo.plan(version.plan.operating_date, lock=True)
    gate = publish_check(repo, version)
    if not gate.can_publish:
        raise DomainError(
            "PUBLISH_BLOCKED",
            "Resolve hard-rule violations and confirm every deferral",
            rule_id="BR-22",
            gate=gate.model_dump(mode="json"),
        )
    if gate.late_risk_order_refs and not accept_late_risk:
        raise DomainError(
            "LATE_RISK_ACCEPTANCE", "Accept likely-late warnings before publishing", rule_id="BR-22"
        )
    by_id = {o.id: o for o in repo.orders(version.plan.operating_date)}
    now = clock.now()
    for deferred in version.deferrals:
        order = by_id[deferred.order_id]
        order.status = "deferred"
        repo.db.add(
            Notification(
                outlet_code=order.outlet_code,
                order_id=order.id,
                kind="deferral",
                reason_code=deferred.reason_code,
                lang="en",
                title="Delivery deferred",
                body=deferral_notice(deferred, order),
                data={
                    "version_id": str(version.id),
                    # ISO with the Colombo offset; the store UI parses it (QA B1).
                    "next_run": ensure_utc(deferred.next_run).astimezone(COLOMBO).isoformat()
                    if deferred.next_run
                    else None,
                },
                created_at=now,
            )
        )
    for trip in version.trips:
        for stop in trip.stops:
            for so in stop.orders:
                by_id[so.order_id].status = "planned"
    audit(repo, user, clock, "plan.published", version, {"accepted_late_risk": accept_late_risk})
    # Flush child rows while the version is still draft (published-version triggers enforce BR-23).
    repo.db.flush()
    version.status = "published"
    version.published_at = now
    repo.db.commit()
    vehicles = {t.vehicle_code for t in version.trips}
    outlets = {o.outlet_code for o in by_id.values()}
    await broker.publish(
        "plan.published",
        {
            "version_id": str(version.id),
            "number": version.number,
            "depot": repo.depot,
            "operating_date": version.plan.operating_date.isoformat(),
        },
        audience=lambda s: (
            s.get("depot") == repo.depot
            or s.get("vehicle") in vehicles
            or s.get("outlet") in outlets
        ),
    )
    return version


def get_plan(repo: Repository, operating_date: date) -> PlanVersion:
    plan = repo.plan(operating_date)
    version = repo.latest(plan.id) if plan else None
    if version is None:
        raise NotFoundError("PLAN_NOT_FOUND", "Generate a plan for this date first")
    return version


def fleet_out(repo: Repository, operating_date: date) -> list[FleetOut]:
    return [
        FleetOut(
            vehicle_code=v.code,
            date=day.date,
            type=v.type,
            temp=v.temp,
            status=day.status,
            switched_on=day.switched_on,
            off_reason=day.off_reason,
            weight_cap_kg=float(v.weight_cap_kg),
            volume_cap_m3=float(v.volume_cap_m3),
            fuel_used_l=used,
            fuel_remaining_l=max(0, float(v.weekly_fuel_quota_l) - used),
        )
        for v, day, used in repo.fleet(operating_date)
    ]


def lock_trip(
    repo: Repository, user: User, clock: Clock, trip_id: uuid.UUID, locked: bool
) -> PlanOut:
    trip = repo.db.get(Trip, trip_id)
    if trip is None:
        raise NotFoundError("TRIP_NOT_FOUND", "Trip not found")
    version = repo.version(trip.version_id, lock=True)
    require_draft(version)
    trip.locked = locked
    audit(
        repo,
        user,
        clock,
        "trip.locked" if locked else "trip.unlocked",
        version,
        {"trip_id": str(trip_id)},
    )
    repo.db.commit()
    return plan_out(repo, version)
