"""BR-48 impact ranking, BR-49 automatic notices, BR-50 quiet dead-zone status."""

import uuid
from dataclasses import replace

from sqlalchemy import select
from xora_engine import Assignment, validate
from xora_engine.repair import forecast, operational_inputs
from xora_engine.timing import planned_arrivals

from app.core.clock import Clock, ensure_utc
from app.core.errors import ConflictError, DomainError
from app.modules.auth.models import User
from app.modules.catalog.models import District, Outlet
from app.modules.loading.models import Hold
from app.modules.ops.models import ExceptionItem, Notification
from app.modules.ops.repository import Repository
from app.modules.ops.schemas import ExceptionOut, FixOut, OpsOut, OpsStopOut, OpsTripOut
from app.modules.orders.models import Order
from app.modules.planning import adapter
from app.modules.planning.models import Deferral, PlanVersion, Stop, StopOrder, Trip
from app.modules.planning.service import audit
from app.modules.stream.broker import broker


def exception_out(row: ExceptionItem) -> ExceptionOut:
    return ExceptionOut(**{key: getattr(row, key) for key in ExceptionOut.model_fields})


def swap_preview(repo: Repository, trip: Trip, left: int, right: int) -> tuple[Assignment, dict]:
    """Validate an adjacent pending-stop swap with the existing engine and forecast."""
    stops = sorted(trip.stops, key=lambda s: s.seq)
    if right != left + 1 or left < 1 or right > len(stops):
        raise DomainError("INVALID_SWAP", "Choose two adjacent stops", rule_id="BR-48")
    if any(s.status in {"delivered", "arrived", "on_hold"} for s in stops[left - 1 : right]):
        raise ConflictError("STOP_ALREADY_VISITED", "These stops are no longer available to swap")
    if repo.db.scalar(select(Hold).where(Hold.trip_id == trip.id, Hold.status == "active")):
        raise ConflictError("TRIP_ON_HOLD", "Resolve the vehicle hold first", rule_id="BR-27")
    problem = adapter.load_problem(repo, trip.version, include_completed=True)
    original = adapter.load_assignment(trip.version, repo)
    target = next(
        t for t in original.trips if (t.vehicle, t.trip_no) == (trip.vehicle_code, trip.trip_no)
    )
    # A DB stop may carry multiple order links; move the whole store block together.
    order_refs = {
        o.id: o.ref for o in repo.orders(trip.version.plan.operating_date, include_completed=True)
    }
    blocks = [
        [s for s in target.stops if s.order_ref in {order_refs[so.order_id] for so in row.orders}]
        for row in stops
    ]
    blocks[left - 1], blocks[right - 1] = blocks[right - 1], blocks[left - 1]
    revised = replace(target, stops=tuple(s for block in blocks for s in block))
    revised = replace(
        revised,
        stops=tuple(
            replace(s, plan_arrival=a)
            for s, a in zip(revised.stops, planned_arrivals(revised, problem), strict=True)
        ),
    )
    candidate = Assignment(tuple(revised if t is target else t for t in original.trips))
    scaled, scaled_problem = operational_inputs(candidate, problem)
    violations = validate(scaled, scaled_problem)
    if violations:
        raise DomainError("SWAP_INFEASIBLE", violations[0].message, rule_id=violations[0].rule_id)
    arrivals = {(a.vehicle, a.trip_no, a.order_ref): a for a in forecast(candidate, problem)}
    affected = {order_refs[so.order_id]: row for row in stops for so in row.orders}
    for s in revised.stops:
        a = arrivals[(revised.vehicle, revised.trip_no, s.order_ref)]
        old = affected[s.order_ref]
        if a.at_risk and not old.at_risk and old.status != "delivered":
            raise DomainError("SWAP_ADDS_RISK", "This swap would put another store at risk")
    return candidate, arrivals


def refresh(repo: Repository, clock: Clock, version: PlanVersion) -> OpsOut:
    now = clock.local_now()
    events = repo.events(version)
    existing = {
        (e.kind, e.entity_id): e for status in ("open", "resolved") for e in repo.exceptions(status)
    }
    trips: list[OpsTripOut] = []
    delivered = on_time = 0
    silent: set[str] = set()
    for trip in sorted(version.trips, key=lambda t: (t.vehicle_code, t.trip_no)):
        district = repo.db.get(District, trip.district)
        stop_ids = {str(s.id) for s in trip.stops}
        ancestor_ids = set(stop_ids | {str(trip.id)})
        for event in events:
            if event.entity_type == "stop":
                prior = repo.db.get(Stop, uuid.UUID(event.entity_id))
                if prior and (prior.trip.vehicle_code, prior.trip.trip_no) == (
                    trip.vehicle_code,
                    trip.trip_no,
                ):
                    ancestor_ids.add(event.entity_id)
        relevant = [e for e in events if e.entity_id in ancestor_ids]
        last = relevant[-1].event_time if relevant else None
        departure = adapter.minute(trip.planned_depart)
        elapsed = (
            (clock.now() - ensure_utc(last)).total_seconds() / 60
            if last
            else (now.hour * 60 + now.minute - departure)
        )
        pending = bool(
            district
            and district.is_dead_zone
            and elapsed >= 15
            and now.date() == version.plan.operating_date
            and any(s.status != "delivered" for s in trip.stops)
        )
        if pending:
            silent.add(trip.vehicle_code)
        chain: list[OpsStopOut] = []
        for stop in trip.stops:
            outlet = repo.db.get(Outlet, stop.outlet_code)
            assert outlet is not None
            recorded = []
            for event in relevant:
                if event.type != "outcome_recorded" or event.entity_type != "stop":
                    continue
                prior = repo.db.get(Stop, uuid.UUID(event.entity_id))
                if prior and prior.outlet_code == stop.outlet_code:
                    recorded.append(event)
            actual = recorded[-1].event_time if recorded else None
            done = stop.status == "delivered"
            if done:
                for resolved_kind in ("late_risk", "pending_sync"):
                    prior_exception = existing.get((resolved_kind, str(stop.id)))
                    if prior_exception:
                        prior_exception.status = "resolved"
            delivered += int(done)
            if done and actual:
                from app.core.clock import COLOMBO

                local = ensure_utc(actual).astimezone(COLOMBO)
                on_time += int(
                    local.date() == version.plan.operating_date
                    and outlet.window_open
                    <= local.time().replace(tzinfo=None)
                    <= outlet.window_close
                )
            status = (
                "delivered"
                if done
                else "pending_sync"
                if pending
                else (
                    "at_risk"
                    if stop.at_risk
                    else "in_transit"
                    if stop.status == "arrived"
                    else stop.status
                )
            )
            chain.append(
                OpsStopOut(
                    id=stop.id,
                    seq=stop.seq,
                    outlet_code=stop.outlet_code,
                    status=status,
                    likely_from=stop.likely_from,
                    likely_to=stop.likely_to,
                    actual_at=actual,
                    top_up_cases=sum(
                        so.planned_cases for so in stop.orders if so.top_up_of_order_id
                    ),
                )
            )
            kind = "pending_sync" if pending else "late_risk" if stop.at_risk else None
            if done or kind is None or (kind, str(stop.id)) in existing:
                continue
            orders = [repo.db.get(Order, so.order_id) for so in stop.orders]
            impact = (
                0
                if pending
                else sum(float(o.weight_kg) for o in orders if o)
                * (3 if any(o and o.temp_requirement == "chilled" for o in orders) else 1)
            )
            fix: dict = {"action": "mark_seen", "label": "Mark as seen"} if pending else {}
            if not pending and stop.seq > 1:
                try:
                    _, arrival = swap_preview(repo, trip, stop.seq - 1, stop.seq)
                    rescued = all(
                        not arrival[(trip.vehicle_code, trip.trip_no, o.ref)].at_risk
                        for o in orders
                        if o
                    )
                    if rescued:
                        fix = {
                            "action": "swap_stops",
                            "trip_id": str(trip.id),
                            "left": stop.seq - 1,
                            "right": stop.seq,
                            "label": f"Swap stops {stop.seq - 1} and {stop.seq}",
                            "effect": f"Swap fixes it: {stop.outlet_code} on time · "
                            "the other stop stays inside its window",
                        }
                except DomainError:
                    pass
            detail = (
                "No signal · normal on this road"
                if pending
                else (
                    f"Likely {str(stop.likely_from)[:5]}–{str(stop.likely_to)[:5]} · "
                    f"closes {str(outlet.window_close)[:5]}"
                )
            )
            if not pending:
                notice = Notification(
                    outlet_code=stop.outlet_code,
                    kind="eta_late",
                    lang="en",
                    title="Delivery may arrive late",
                    body=detail,
                    data={"stop_id": str(stop.id)},
                    created_at=clock.now(),
                )
                repo.db.add(notice)
                detail += f" · store told automatically at {now:%H:%M}"
            row = ExceptionItem(
                kind=kind,
                impact=impact,
                title=f"{trip.vehicle_code} · stop {stop.seq} · {stop.outlet_code} {trip.district}",
                detail=detail,
                entity_type="stop",
                entity_id=str(stop.id),
                suggested_fix=fix,
                status="open",
                created_at=clock.now(),
            )
            repo.db.add(row)
        trips.append(
            OpsTripOut(
                id=trip.id,
                vehicle_code=trip.vehicle_code,
                trip_no=trip.trip_no,
                district=trip.district,
                brand=trip.brand,
                stops=chain,
            )
        )
    repo.db.commit()
    return OpsOut(
        operating_date=version.plan.operating_date,
        depot=repo.depot,
        version_id=version.id,
        number=version.number,
        delivered=delivered,
        stops_total=sum(len(t.stops) for t in trips),
        on_time=on_time,
        pending_sync=len(silent),
        exceptions=[
            exception_out(e)
            for e in repo.exceptions()
            if e.entity_type != "stop"
            or e.entity_id in {str(s.id) for t in version.trips for s in t.stops}
        ],
        trips=trips,
    )


async def apply_fix(repo: Repository, user: User, clock: Clock, identifier: uuid.UUID) -> FixOut:
    row = repo.exception(identifier)
    source = repo.db.get(Stop, uuid.UUID(row.entity_id)) if row.entity_type == "stop" else None
    if source:
        repo.plan(source.trip.version.plan.operating_date, lock=True)
    row = repo.exception(identifier, lock=True)
    if row.status != "open":
        raise ConflictError("EXCEPTION_RESOLVED", "This exception has already been handled")
    action = row.suggested_fix.get("action")
    version_id = None
    if action == "swap_stops" and source:
        old = source.trip.version
        latest = repo.latest(old.plan_id)
        if latest is None or latest.id != old.id or old.status != "published":
            raise ConflictError("STALE_FIX", "Refresh the current published plan before applying")
        candidate, arrivals = swap_preview(
            repo, source.trip, row.suggested_fix["left"], row.suggested_fix["right"]
        )
        if repo.db.scalar(
            select(Hold).join(Trip).where(Trip.version_id == old.id, Hold.status == "active")
        ):
            raise ConflictError(
                "PLAN_ON_HOLD", "Resolve active shortfalls before revising this plan"
            )
        new = PlanVersion(
            plan_id=old.plan_id,
            number=old.number + 1,
            parent_version_id=old.id,
            status="draft",
            created_by=user.id,
            created_at=clock.now(),
            change_reason=f"exception:{row.id}",
            solver_status=old.solver_status,
            kpis=dict(old.kpis),
            bottleneck=dict(old.bottleneck),
        )
        repo.db.add(new)
        repo.db.flush()
        orders = {o.id: o.ref for o in repo.orders(old.plan.operating_date, include_completed=True)}
        for t in old.trips:
            revised = next(
                v for v in candidate.trips if (v.vehicle, v.trip_no) == (t.vehicle_code, t.trip_no)
            )
            copy = Trip(
                version_id=new.id,
                **{
                    k: getattr(t, k)
                    for k in (
                        "vehicle_code",
                        "trip_no",
                        "brand",
                        "district",
                        "lane",
                        "planned_depart",
                        "plan_minutes",
                        "litres",
                        "weight_kg",
                        "volume_m3",
                        "locked",
                    )
                },
            )
            repo.db.add(copy)
            repo.db.flush()
            ranked = {s.order_ref: i for i, s in enumerate(revised.stops)}
            ordered = sorted(
                t.stops, key=lambda s: min(ranked[orders[so.order_id]] for so in s.orders)
            )
            for seq, s in enumerate(ordered, 1):
                a = arrivals[(t.vehicle_code, t.trip_no, orders[s.orders[0].order_id])]
                copy_stop = Stop(
                    trip_id=copy.id,
                    seq=seq,
                    outlet_code=s.outlet_code,
                    status=s.status,
                    plan_arrival=adapter.as_time(a.plan_arrival),
                    likely_from=adapter.as_time(a.likely_from),
                    likely_to=adapter.as_time(a.likely_to),
                    at_risk=a.at_risk,
                )
                repo.db.add(copy_stop)
                repo.db.flush()
                for so in s.orders:
                    repo.db.add(
                        StopOrder(
                            stop_id=copy_stop.id,
                            order_id=so.order_id,
                            planned_cases=so.planned_cases,
                            top_up_of_order_id=so.top_up_of_order_id,
                        )
                    )
        for d in old.deferrals:
            repo.db.add(
                Deferral(
                    version_id=new.id,
                    **{
                        k: getattr(d, k)
                        for k in (
                            "order_id",
                            "reason_code",
                            "group",
                            "priority",
                            "displaces",
                            "explanation",
                            "next_run",
                            "confirmed_by",
                            "confirmed_at",
                            "confirm_reason",
                        )
                    },
                )
            )
        audit(
            repo,
            user,
            clock,
            "exception.fixed",
            new,
            {"exception_id": str(row.id), "action": action},
        )
        audit(repo, user, clock, "plan.published", new, {"reason": "swap_stops"})
        new.kpis = {**new.kpis, "stops_at_risk": sum(a.at_risk for a in arrivals.values())}
        for driver in repo.db.scalars(
            select(User).where(User.role == "driver", User.vehicle_code == source.trip.vehicle_code)
        ):
            repo.db.add(
                Notification(
                    recipient_user_id=driver.id,
                    kind="plan_changed",
                    lang="en",
                    title=f"Plan v{new.number}: stop order changed",
                    body=row.suggested_fix.get("label", "Review the revised trip"),
                    data={"version_id": str(new.id)},
                    created_at=clock.now(),
                )
            )
        repo.db.flush()
        new.status = "published"
        new.published_at = clock.now()
        version_id = new.id
    elif action != "mark_seen":
        raise DomainError("NO_SAFE_FIX", "Open this item to review the available actions")
    row.status = "resolved"
    repo.db.commit()
    await broker.publish(
        "exception.updated",
        {"id": str(row.id), "status": "resolved"},
        audience=lambda s: s.get("depot") == repo.depot,
    )
    if version_id:
        await broker.publish(
            "plan.published",
            {
                "version_id": str(version_id),
                "number": new.number,
                "depot": repo.depot,
                "operating_date": old.plan.operating_date.isoformat(),
            },
            audience=lambda s: (
                s.get("depot") == repo.depot
                or s.get("vehicle") in {t.vehicle_code for t in old.trips}
                or s.get("outlet") in {st.outlet_code for t in old.trips for st in t.stops}
            ),
        )
    return FixOut(exception_id=row.id, status=row.status, version_id=version_id)
