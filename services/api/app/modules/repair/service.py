"""Human-selected repairs publish immutable revisions; holds wait for loader acknowledgement."""

import json
import uuid
from dataclasses import asdict, replace
from datetime import UTC, datetime
from math import ceil
from time import perf_counter
from typing import Any

from sqlalchemy import select
from xora_engine import Assignment, Problem, repair, validate_repair
from xora_engine import RepairOption as EngineOption
from xora_engine import Shortfall as EngineShortfall
from xora_engine.fuel import trip_litres
from xora_engine.policy import priority
from xora_engine.repair import operational_inputs

from app.core.clock import Clock
from app.core.errors import ConflictError, DomainError, NotFoundError
from app.modules.auth.models import User
from app.modules.catalog.models import OutletProfile
from app.modules.loading.models import RepairOption, Shortfall
from app.modules.ops.models import ExceptionItem, Notification
from app.modules.orders.models import Order
from app.modules.planning import adapter
from app.modules.planning.models import Deferral, PlanVersion, Stop, StopOrder, Trip
from app.modules.planning.service import audit
from app.modules.repair.repository import Repository
from app.modules.repair.schemas import RepairOptionOut, RepairStopOut, ShortfallOptionsOut
from app.modules.stream.broker import broker


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02}:{minutes % 60:02}"


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _compute(
    repo: Repository, clock: Clock, shortfall_id: uuid.UUID
) -> tuple[Shortfall, Trip, Problem, Assignment, EngineShortfall, tuple[EngineOption, ...], int]:
    shortfall, trip = repo.shortfall(shortfall_id, lock=True)
    repo.plan(trip.version.plan.operating_date, lock=True)
    latest = repo.latest(trip.version.plan_id)
    if latest is None or latest.id != trip.version_id or latest.status != "published":
        raise ConflictError(
            "STALE_SHORTFALL",
            "Refresh the shortfall against the current published plan",
            rule_id="BR-23",
        )
    if repo.applied(shortfall.id):
        raise ConflictError(
            "REPAIR_ALREADY_APPLIED",
            "This shortfall already has a published repair",
            rule_id="BR-30",
        )
    if repo.hold(shortfall.id) is None:
        raise ConflictError(
            "HOLD_REQUIRED", "This shortfall needs an active vehicle hold", rule_id="BR-27"
        )
    if clock.local_now().date() != trip.version.plan.operating_date:
        raise DomainError("REPAIR_OPERATING_DAY", "Set the clock to the shortfall's operating day")
    order = repo.db.get(Order, shortfall.order_id)
    assert order is not None
    profile = repo.db.get(OutletProfile, order.outlet_code)
    problem = adapter.load_problem(repo, trip.version, include_completed=True)
    assignment = adapter.load_assignment(trip.version, repo)
    other_holds = {
        h.trip_id for h in repo.active_holds(trip.version_id) if h.shortfall_id != shortfall.id
    }
    unavailable = frozenset(
        (t.vehicle_code, t.trip_no)
        for t in trip.version.trips
        if t.id in other_holds or any(s.status in {"in_transit", "delivered"} for s in t.stops)
    )
    value = EngineShortfall(
        order.ref,
        shortfall.qty,
        trip.vehicle_code,
        trip.trip_no,
        clock.local_now().hour * 60 + clock.local_now().minute,
        profile.split_rule if profile else "any",
        unavailable_trips=unavailable,
    )
    start = perf_counter()
    try:
        options = repair(assignment, value, problem)
    except ValueError as exc:
        raise DomainError("INVALID_SHORTFALL", str(exc), rule_id="BR-26") from exc
    # C requires a real next operating date; never promise a fictional next run.
    if repo.next_operating_date(trip.version.plan.operating_date) is None:
        options = tuple(option for option in options if option.label != "C")
        if options:
            best = min(options, key=lambda o: (o.breaks_store_rule, o.loss, o.label))
            options = tuple(replace(o, recommended=o.label == best.label) for o in options)
    return (
        shortfall,
        trip,
        problem,
        assignment,
        value,
        options,
        round((perf_counter() - start) * 1000),
    )


def _snapshot(option: EngineOption, version_id: uuid.UUID) -> dict[str, Any]:
    return json.loads(json.dumps({"version_id": str(version_id), **asdict(option)}, sort_keys=True))


def _option_id(shortfall_id: uuid.UUID, snapshot: dict[str, Any]) -> uuid.UUID:
    return uuid.uuid5(shortfall_id, json.dumps(snapshot, sort_keys=True))


def get_options(repo: Repository, clock: Clock, shortfall_id: uuid.UUID) -> ShortfallOptionsOut:
    shortfall, trip, problem, assignment, value, options, elapsed = _compute(
        repo, clock, shortfall_id
    )
    order = repo.db.get(Order, shortfall.order_id)
    reporter = repo.db.get(User, shortfall.reported_by)
    assert order is not None and reporter is not None
    rank = {
        o.label: i
        for i, o in enumerate(
            sorted(options, key=lambda o: (o.breaks_store_rule, o.loss, o.label)), 1
        )
    }
    out: list[RepairOptionOut] = []
    for option in options:
        snapshot = _snapshot(option, trip.version_id)
        option_id = _option_id(shortfall.id, snapshot)
        row = repo.db.get(RepairOption, option_id)
        if row is None:
            row = RepairOption(
                id=option_id,
                shortfall_id=shortfall.id,
                label=option.label,
                rank=rank[option.label],
                title=option.title,
                summary=snapshot,
                breaks_store_rule=option.breaks_store_rule,
                loss=option.loss,
                recommended=option.recommended,
            )
            repo.db.add(row)
        arrival = next(
            (
                a
                for a in option.arrivals
                if a.order_ref == order.ref
                and (a.vehicle, a.trip_no) != (trip.vehicle_code, trip.trip_no)
            ),
            None,
        )
        first = next(
            a
            for a in option.arrivals
            if a.order_ref == order.ref
            and (a.vehicle, a.trip_no) == (trip.vehicle_code, trip.trip_no)
        )
        next_day = repo.next_operating_date(trip.version.plan.operating_date)
        next_label = next_day.strftime("%a") if next_day else "next run"
        gets = (
            f"{option.delivered_now} now · {shortfall.qty} at ~{_clock(arrival.likely_from)}"
            if option.label == "A" and arrival
            else f"{option.delivered_now} at ~{_clock(first.likely_from)}"
            if option.label == "B"
            else f"{option.delivered_now} now · {option.next_run_cases} on {next_label}"
        )
        out.append(
            RepairOptionOut(
                id=option_id,
                label=option.label,
                rank=rank[option.label],
                title=option.title
                if option.label != "C"
                else f"Send {option.delivered_now}, move {option.next_run_cases} to {next_label}",
                gets=gets,
                delay=f"{trip.vehicle_code} +{option.delay_minutes} min"
                if option.delay_minutes
                else "None",
                other_stops="; ".join(option.effects) or "Unchanged",
                loss=option.loss,
                loss_label="Lowest" if option.loss == min(o.loss for o in options) else "Medium",
                breaks_store_rule=option.breaks_store_rule,
                recommended=option.recommended,
            )
        )
    now = clock.local_now()
    departure = (
        datetime.combine(trip.version.plan.operating_date, trip.planned_depart, tzinfo=now.tzinfo)
        if trip.planned_depart
        else now
    )
    row_order = {
        o.ref: o for o in repo.orders(trip.version.plan.operating_date, include_completed=True)
    }
    stops = [
        RepairStopOut(
            outlet_code=problem.orders[s.order_ref].outlet,
            order_ref=s.order_ref,
            cases=s.cases,
            available_cases=s.cases - shortfall.qty if s.order_ref == order.ref else s.cases,
            window_open=adapter.as_time(problem.orders[s.order_ref].window_open),
            window_close=adapter.as_time(problem.orders[s.order_ref].window_close),
        )
        for t in assignment.trips
        if (t.vehicle, t.trip_no) == (trip.vehicle_code, trip.trip_no)
        for s in t.stops
    ]
    rules = {
        "same_morning_only": "split chilled orders only if the rest arrives the same morning",
        "any": "split chilled deliveries allowed",
        "never": "never split chilled orders",
    }
    repo.db.commit()
    return ShortfallOptionsOut(
        id=shortfall.id,
        version_id=trip.version_id,
        version_number=trip.version.number,
        next_version_number=trip.version.number + 1,
        operating_date=trip.version.plan.operating_date,
        vehicle_code=trip.vehicle_code,
        trip_no=trip.trip_no,
        depot=repo.depot,
        dock=reporter.dock,
        reported_at=_aware(shortfall.event_time)
        .astimezone(now.tzinfo)
        .timetz()
        .replace(tzinfo=None),
        reporter=reporter.name,
        kind=shortfall.kind,
        reason=shortfall.reason.replace("_", " ").capitalize(),
        order_ref=order.ref,
        outlet_code=order.outlet_code,
        district=problem.orders[order.ref].district,
        temp_requirement=row_order[order.ref].temp_requirement,
        planned_cases=next(s.cases for s in stops if s.order_ref == order.ref),
        missing_cases=shortfall.qty,
        waiting_seconds=max(0, int((now - _aware(shortfall.event_time)).total_seconds())),
        to_departure_minutes=max(0, ceil((departure - now).total_seconds() / 60)),
        planned_depart=trip.planned_depart,
        split_rule=value.split_rule,
        split_rule_text=rules[value.split_rule],
        held=True,
        solve_ms=elapsed,
        stops=stops,
        options=out,
    )


async def apply(
    repo: Repository, user: User, clock: Clock, shortfall_id: uuid.UUID, option_id: uuid.UUID
) -> PlanVersion:
    shortfall, source, problem, original, value, options, elapsed = _compute(
        repo, clock, shortfall_id
    )
    row = repo.db.get(RepairOption, option_id)
    if row is None or row.shortfall_id != shortfall.id:
        raise NotFoundError("REPAIR_OPTION_NOT_FOUND", "Choose an option from this shortfall")
    chosen = next((o for o in options if o.label == row.label), None)
    if (
        chosen is None
        or _option_id(shortfall.id, _snapshot(chosen, source.version_id)) != option_id
    ):
        raise ConflictError(
            "STALE_REPAIR_OPTION",
            "The situation changed; refresh the repair options",
            rule_id="BR-28",
        )
    if validate_repair(chosen.assignment, original, value, problem, chosen.next_run_cases):
        raise DomainError(
            "REPAIR_INFEASIBLE", "The repair no longer satisfies hard rules", rule_id="BR-28"
        )
    now = clock.now()
    version = PlanVersion(
        plan_id=source.version.plan_id,
        number=source.version.number + 1,
        parent_version_id=source.version_id,
        status="draft",
        change_reason=f"shortfall:{shortfall.id}",
        created_by=user.id,
        created_at=now,
        solver_status="REPAIR",
        solve_ms=elapsed,
        kpis=dict(source.version.kpis),
        bottleneck=dict(source.version.bottleneck),
    )
    repo.db.add(version)
    repo.db.flush()
    by_ref = {
        o.ref: o for o in repo.orders(source.version.plan.operating_date, include_completed=True)
    }
    arrivals = {(a.vehicle, a.trip_no, a.order_ref): a for a in chosen.arrivals}
    scaled, scaled_problem = operational_inputs(chosen.assignment, problem)
    new_source: Trip | None = None
    trip_ids: dict[uuid.UUID, uuid.UUID] = {}
    for trip, scaled_trip in zip(chosen.assignment.trips, scaled.trips, strict=True):
        orders = [scaled_problem.orders[s.order_ref] for s in scaled_trip.stops]
        new_trip = Trip(
            version_id=version.id,
            vehicle_code=trip.vehicle,
            trip_no=trip.trip_no,
            brand=orders[0].brand,
            district=orders[0].district,
            lane="predawn" if orders[0].brand == "Fresh" else "daytime",
            planned_depart=adapter.as_time(trip.planned_depart),
            plan_minutes=trip.plan_minutes,
            litres=trip_litres(orders, problem.vehicles[trip.vehicle], scaled_problem),
            weight_kg=sum(o.weight_kg for o in orders),
            volume_m3=sum(o.volume_m3 for o in orders),
            locked=trip.locked,
        )
        repo.db.add(new_trip)
        repo.db.flush()
        if (trip.vehicle, trip.trip_no) == (source.vehicle_code, source.trip_no):
            new_source = new_trip
        old_trip = next(
            (
                t
                for t in source.version.trips
                if (t.vehicle_code, t.trip_no) == (trip.vehicle, trip.trip_no)
            ),
            None,
        )
        if old_trip:
            trip_ids[old_trip.id] = new_trip.id
        for sequence, stop in enumerate(trip.stops, 1):
            arrival = arrivals[(trip.vehicle, trip.trip_no, stop.order_ref)]
            old_stop = (
                next(
                    (
                        s
                        for s in old_trip.stops
                        if any(so.order_id == by_ref[stop.order_ref].id for so in s.orders)
                    ),
                    None,
                )
                if old_trip
                else None
            )
            new_stop = Stop(
                trip_id=new_trip.id,
                seq=sequence,
                outlet_code=problem.orders[stop.order_ref].outlet,
                plan_arrival=adapter.as_time(arrival.plan_arrival),
                likely_from=adapter.as_time(arrival.likely_from),
                likely_to=adapter.as_time(arrival.likely_to),
                at_risk=arrival.at_risk,
                status=old_stop.status if old_stop else "planned",
            )
            repo.db.add(new_stop)
            repo.db.flush()
            top_up = (
                chosen.top_up_trip == (trip.vehicle, trip.trip_no)
                and stop.order_ref == value.order_ref
            )
            previous_link = (
                next(
                    (
                        so.top_up_of_order_id
                        for so in old_stop.orders
                        if so.order_id == by_ref[stop.order_ref].id
                    ),
                    None,
                )
                if old_stop
                else None
            )
            repo.db.add(
                StopOrder(
                    stop_id=new_stop.id,
                    order_id=by_ref[stop.order_ref].id,
                    planned_cases=stop.cases,
                    top_up_of_order_id=shortfall.order_id if top_up else previous_link,
                )
            )
    for deferred in source.version.deferrals:
        repo.db.add(
            Deferral(
                version_id=version.id,
                order_id=deferred.order_id,
                reason_code=deferred.reason_code,
                group=deferred.group,
                priority=deferred.priority,
                displaces=deferred.displaces,
                explanation=deferred.explanation,
                next_run=deferred.next_run,
                confirmed_by=deferred.confirmed_by,
                confirmed_at=deferred.confirmed_at,
                confirm_reason=deferred.confirm_reason,
            )
        )
    future_order_id: uuid.UUID | None = None
    if chosen.next_run_cases:
        order = by_ref[value.order_ref]
        next_day = repo.next_operating_date(source.version.plan.operating_date)
        assert next_day is not None
        ratio = chosen.next_run_cases / order.units
        future = Order(
            ref=f"R-{shortfall.id.hex[:16]}",
            outlet_code=order.outlet_code,
            brand=order.brand,
            temp_requirement=order.temp_requirement,
            delivery_date=next_day,
            units=chosen.next_run_cases,
            weight_kg=float(order.weight_kg) * ratio,
            volume_m3=float(order.volume_m3) * ratio,
            deferred_yesterday=True,
            days_since_last_served=order.days_since_last_served + 1,
            status="placed",
            source="app",
            placed_at=now,
            placed_by=user.id,
        )
        repo.db.add(future)
        repo.db.flush()
        future_order_id = future.id
    hold = repo.hold(shortfall.id)
    assert hold is not None and new_source is not None
    # BR-27/31: carry the hold to v2; acknowledgement is the loader track's release gate.
    for active_hold in repo.active_holds(source.version_id):
        active_hold.trip_id = trip_ids[active_hold.trip_id]
    row.applied_at = now
    row.applied_by = user.id
    totals: dict[str, int] = {}
    for t in chosen.assignment.trips:
        for s in t.stops:
            totals[s.order_ref] = totals.get(s.order_ref, 0) + s.cases
    served = {ref for ref, cases in totals.items() if cases > 0}
    version.kpis = {
        **version.kpis,
        "orders_served": len(served),
        "chilled_served": sum(problem.orders[ref].temp == "chilled" for ref in served),
        "stops_at_risk": sum(a.at_risk for a in chosen.arrivals),
        "value_served": sum(
            priority(problem.orders[ref], problem.festival_ramp)
            * totals[ref]
            / problem.orders[ref].units
            for ref in served
        ),
        "reefer_m3_used": sum(
            scaled_problem.orders[s.order_ref].volume_m3
            for t in scaled.trips
            if problem.vehicles[t.vehicle].temp == "reefer"
            for s in t.stops
        ),
    }
    audit(
        repo,
        user,
        clock,
        "repair.applied",
        version,
        {
            "shortfall_id": str(shortfall.id),
            "option_id": str(row.id),
            "label": row.label,
            "breaks_store_rule": chosen.breaks_store_rule,
            "loss": chosen.loss,
            "original_order_id": str(shortfall.order_id),
            "future_order_id": str(future_order_id) if future_order_id else None,
            "next_run_cases": chosen.next_run_cases,
            "held_trip_id": str(new_source.id),
            "previous_trip_id": str(source.id),
        },
    )
    for exception in repo.db.scalars(
        select(ExceptionItem).where(
            ExceptionItem.entity_id == str(shortfall.id), ExceptionItem.kind == "shortfall"
        )
    ):
        exception.status = "resolved"
    repo.db.add(
        Notification(
            outlet_code=by_ref[value.order_ref].outlet_code,
            order_id=shortfall.order_id,
            kind="plan_changed",
            lang="en",
            title=f"Plan revised to v{version.number}",
            body=row.title,
            data={
                "version_id": str(version.id),
                "shortfall_id": str(shortfall.id),
                "option": row.label,
            },
            created_at=now,
        )
    )
    audit(repo, user, clock, "plan.published", version, {"repair_option_id": str(row.id)})
    repo.db.flush()
    version.status = "published"
    version.published_at = now
    repo.db.commit()
    vehicles = {t.vehicle for t in chosen.assignment.trips}
    outlets = {o.outlet_code for o in by_ref.values()}
    await broker.publish(
        "plan.published",
        {
            "version_id": str(version.id),
            "number": version.number,
            "depot": repo.depot,
            "operating_date": version.plan.operating_date.isoformat(),
            "shortfall_id": str(shortfall.id),
        },
        audience=lambda s: (
            s.get("depot") == repo.depot
            or s.get("vehicle") in vehicles
            or s.get("outlet") in outlets
        ),
    )
    return repo.version(version.id)
