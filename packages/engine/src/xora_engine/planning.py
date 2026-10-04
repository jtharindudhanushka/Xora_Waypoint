"""Deterministic greedy fallback, sharing every hard predicate with validate()."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from math import ceil

from xora_engine.fuel import trip_litres
from xora_engine.models import Assignment, Order, Problem, Stop, Trip, Vehicle
from xora_engine.policy import DEFAULT_POLICY, Policy, priority
from xora_engine.rules import RULES
from xora_engine.timing import planned_arrivals, trip_minutes
from xora_engine.validation import validate


@dataclass(frozen=True)
class LikelyStop:
    order_ref: str
    plan_arrival: int
    likely_from: int
    likely_to: int
    at_risk: bool


@dataclass(frozen=True)
class Deferral:
    order_ref: str
    reason_code: str
    group: str
    priority: float
    displaces: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class Kpis:
    orders_served: int
    chilled_served: int
    stops_at_risk: int
    deferrals: int
    value_served: float
    reefer_m3_used: float
    reefer_m3_total: float


@dataclass(frozen=True)
class Bottleneck:
    resource: str
    used: float
    capacity: float
    explanation: str


@dataclass(frozen=True)
class PlanResult:
    assignment: Assignment
    likely_stops: tuple[LikelyStop, ...]
    deferrals: tuple[Deferral, ...]
    kpis: Kpis
    bottleneck: Bottleneck
    solver_status: str = "GREEDY"

    @property
    def trips(self) -> tuple[Trip, ...]:
        return self.assignment.trips


def _accepts(assignment: Assignment, problem: Problem) -> bool:
    return all(predicate(assignment, problem) for _, _, _, predicate in RULES)


def _scheduled(trip: Trip, assignment: Assignment, problem: Problem) -> Trip | None:
    orders = sorted(
        (problem.orders[s.order_ref] for s in trip.stops),
        key=lambda o: (o.mall_close if o.mall_close is not None else 1441, o.window_close, o.ref),
    )
    if not orders:
        return None
    fresh = orders[0].brand == "Fresh"
    start, end = (210, 480) if fresh else (480, 960)
    for existing in assignment.trips:
        if existing.vehicle == trip.vehicle and existing.trip_no < trip.trip_no:
            existing_fresh = problem.orders[existing.stops[0].order_ref].brand == "Fresh"
            if fresh == existing_fresh:
                start = max(start, existing.planned_depart + existing.plan_minutes)
    duration = trip_minutes(orders, problem)
    latest = end - duration
    trial = replace(
        trip,
        stops=tuple(Stop(o.ref, o.units) for o in orders),
        planned_depart=0,
        plan_minutes=duration,
    )
    offsets = planned_arrivals(trial, problem)
    for order, offset in zip(orders, offsets, strict=True):
        if order.mall_open is not None and order.mall_close is not None:
            start = max(start, order.mall_open - offset)
            latest = min(latest, order.mall_close - offset)
    if start > latest:
        return None
    trial = replace(trial, planned_depart=start)
    arrivals = planned_arrivals(trial, problem)
    return replace(
        trial, stops=tuple(Stop(o.ref, o.units, a) for o, a in zip(orders, arrivals, strict=True))
    )


def _insert(order: Order, assignment: Assignment, problem: Problem) -> Assignment | None:
    # Cheap pruning calls the same BR predicates used by final validation.
    vehicles = sorted(
        problem.vehicles.values(),
        key=lambda v: (
            v.temp == "reefer" and order.temp != "chilled",
            v.type == "van" and order.parking != "van_only",
            v.volume_cap_m3,
            v.code,
        ),
    )
    for vehicle in vehicles:
        solo = Assignment((Trip(vehicle.code, 1, (Stop(order.ref, order.units),), 210, 0),))
        if not all(
            predicate(solo, problem)
            for rid, _, _, predicate in RULES
            if rid in ("BR-02", "BR-03", "BR-04", "BR-10")
        ):
            continue
        existing = [t for t in assignment.trips if t.vehicle == vehicle.code]
        for trip in sorted(existing, key=lambda t: t.trip_no):
            if trip.locked:
                continue
            candidate = replace(trip, stops=(*trip.stops, Stop(order.ref, order.units)))
            # Group check precedes scheduling, which assumes one district and brand.
            if not RULES[0][3](Assignment((candidate,)), problem):
                continue
            scheduled = _scheduled(candidate, assignment, problem)
            if scheduled is None:
                continue
            updated = Assignment(tuple(scheduled if t == trip else t for t in assignment.trips))
            # Reschedule the later trip if lengthening the first changed its earliest start.
            later = [
                t
                for t in updated.trips
                if t.vehicle == vehicle.code and t.trip_no > scheduled.trip_no
            ]
            for next_trip in later:
                next_scheduled = _scheduled(next_trip, updated, problem)
                if next_scheduled is None or (next_trip.locked and next_scheduled != next_trip):
                    break
                updated = Assignment(
                    tuple(next_scheduled if t == next_trip else t for t in updated.trips)
                )
            else:
                if _accepts(updated, problem):
                    return updated
        for number in (1, 2):
            if any(t.trip_no == number for t in existing):
                continue
            trip = Trip(vehicle.code, number, (Stop(order.ref, order.units),), 210, 0)
            scheduled = _scheduled(trip, assignment, problem)
            if scheduled is not None:
                updated = Assignment((*assignment.trips, scheduled))
                if _accepts(updated, problem):
                    return updated
    return None


def _greedy(
    problem: Problem, policy: Policy, locks: tuple[Trip, ...] = (), forced: str | None = None
) -> Assignment:
    assignment = Assignment(tuple(replace(t, locked=True) for t in locks))
    violations = validate(assignment, problem)
    if violations:
        raise ValueError(violations[0].message)
    assigned = {s.order_ref for t in locks for s in t.stops}
    orders = sorted(
        problem.orders.values(),
        key=lambda o: (
            o.ref != forced,
            not o.deferred_yesterday,
            o.parking != "van_only",
            o.temp != "chilled",
            -priority(o, problem.festival_ramp, policy) / max(o.volume_m3, 1e-6),
            o.brand,
            o.district,
            o.ref,
        ),
    )
    for order in orders:
        if order.ref in assigned:
            continue
        candidate = _insert(order, assignment, problem)
        if candidate is not None:
            assignment = candidate
    return assignment


def likely_windows(assignment: Assignment, problem: Problem) -> tuple[LikelyStop, ...]:
    result: list[LikelyStop] = []
    for trip in assignment.trips:
        first = problem.orders[trip.stops[0].order_ref]
        district = problem.districts[first.district]
        low = high = float(trip.planned_depart)
        for i, stop in enumerate(trip.stops):
            order = problem.orders[stop.order_ref]
            minutes = district.depot_to_district_min if i == 0 else district.inter_stop_min
            p50, p90 = problem.travel_ratio.get((order.district, int(low) // 60), (1.5, 1.9))
            low = max(order.window_open, low + minutes * p50)
            high = max(order.window_open, high + minutes * p90, low)
            result.append(
                LikelyStop(
                    order.ref,
                    stop.plan_arrival or 0,
                    ceil(low),
                    ceil(high),
                    high > order.window_close,
                )
            )
            service = problem.service_allowance[(order.brand, order.dock_type)]
            low += service
            high += service
    return tuple(result)


def plan(
    problem: Problem,
    policy: Policy = DEFAULT_POLICY,
    locks: tuple[Trip, ...] = (),
    time_limit_s: float = 10,
    force_order_ref: str | None = None,
) -> PlanResult:
    """Optimise from a validated greedy hint; callers measure elapsed time outside the library."""
    if time_limit_s <= 0:
        raise ValueError("time_limit_s must be positive")
    if force_order_ref is not None and force_order_ref not in problem.orders:
        raise ValueError("Unknown forced order")
    assignment = _greedy(problem, policy, locks, forced=force_order_ref)
    status = "GREEDY"
    try:
        from xora_engine.cpsat import optimise
    except ImportError:
        pass  # Dependency/load failures keep the validated fallback available.
    else:
        assignment, status = optimise(
            assignment, problem, policy, locks, time_limit_s, force_order_ref
        )
    return explain(assignment, problem, policy, locks, status, force_order_ref)


def explain(
    assignment: Assignment,
    problem: Problem,
    policy: Policy = DEFAULT_POLICY,
    locks: tuple[Trip, ...] = (),
    solver_status: str = "GREEDY",
    force_order_ref: str | None = None,
) -> PlanResult:
    """One BR-15–18 explanation and KPI path for both solver backends."""
    served = {s.order_ref for t in assignment.trips for s in t.stops}
    if force_order_ref is not None and force_order_ref not in served:
        raise ValueError("This order cannot be served without breaking a hard rule or a trip lock")
    max_priority = (
        max(
            (priority(o, problem.festival_ramp, policy) for o in problem.orders.values()), default=1
        )
        or 1
    )
    deferrals: list[Deferral] = []
    for order in problem.orders.values():
        if order.ref in served:
            continue
        solo = _insert(order, Assignment(), problem)
        if solo is not None:
            forced = _greedy(problem, policy, locks, forced=order.ref)
            forced_served = {s.order_ref for t in forced.trips for s in t.stops}
            displaces = tuple(sorted(served - forced_served))
            # Locked plans may prevent a forced insertion although the order is feasible alone.
            explanation = (
                ("Can be served by replacing: " + ", ".join(displaces))
                if displaces
                else ("Feasible on an empty fleet; the current trips or locks prevent insertion")
            )
            code, group = "LOWER_PRIORITY", "choice"
        else:
            displaces = ()
            code = _blocking_reason(order, problem)
            group = "unavoidable"
            explanation = (
                "No eligible vehicle can carry this whole order: " + code.replace("_", " ").lower()
            )
        deferrals.append(
            Deferral(
                order.ref,
                code,
                group,
                round(100 * priority(order, problem.festival_ramp, policy) / max_priority, 2),
                displaces,
                explanation,
            )
        )
    windows = likely_windows(assignment, problem)
    reefer_used = sum(
        problem.orders[s.order_ref].volume_m3
        for t in assignment.trips
        if problem.vehicles[t.vehicle].temp == "reefer"
        for s in t.stops
    )
    reefer_total = sum(
        v.volume_cap_m3 * 2
        for v in problem.vehicles.values()
        if v.temp == "reefer" and v.status == "available" and v.switched_on
    )
    value = sum(priority(problem.orders[r], problem.festival_ramp, policy) for r in served)
    kpis = Kpis(
        len(served),
        sum(problem.orders[r].temp == "chilled" for r in served),
        sum(s.at_risk for s in windows),
        len(deferrals),
        value,
        reefer_used,
        reefer_total,
    )
    bottleneck = _bottleneck(assignment, problem, deferrals, reefer_used, reefer_total)
    return PlanResult(assignment, windows, tuple(deferrals), kpis, bottleneck, solver_status)


def _blocking_reason(order: Order, problem: Problem) -> str:
    candidates = list(problem.vehicles.values())
    filters: tuple[tuple[str, Callable[[Vehicle], bool]], ...] = (
        (
            "VEHICLE_UNAVAILABLE",
            lambda v: v.status == "available" and v.switched_on and v.depot == order.depot,
        ),
        ("NO_REEFER_CAPACITY", lambda v: order.temp != "chilled" or v.temp == "reefer"),
        ("NO_VAN_AVAILABLE", lambda v: order.parking != "van_only" or v.type == "van"),
        ("VOLUME_CAP", lambda v: order.volume_m3 <= v.volume_cap_m3 + 1e-6),
        ("WEIGHT_CAP", lambda v: order.weight_kg <= v.weight_cap_kg + 1e-6),
    )
    for code, predicate in filters:
        candidates = [v for v in candidates if predicate(v)]
        if not candidates:
            return code
    duration = trip_minutes([order], problem)
    if duration > (270 if order.brand == "Fresh" else 480):
        return "FRESH_TIME_BUDGET" if order.brand == "Fresh" else "DAY_TIME_BUDGET"
    if all(trip_litres([order], v, problem) > v.fuel_remaining_l + 1e-6 for v in candidates):
        return "FUEL_QUOTA"
    # A mall's window may be impossible inside its lane, even with an otherwise empty fleet.
    return "FRESH_TIME_BUDGET" if order.brand == "Fresh" else "DAY_TIME_BUDGET"


def _bottleneck(
    assignment: Assignment,
    problem: Problem,
    deferrals: list[Deferral],
    reefer_used: float,
    reefer_total: float,
) -> Bottleneck:
    if any(problem.orders[d.order_ref].temp == "chilled" for d in deferrals):
        reefers = {
            v.code
            for v in problem.vehicles.values()
            if v.temp == "reefer" and v.switched_on and v.status == "available"
        }
        trips = [t for t in assignment.trips if t.vehicle in reefers]
        fresh_minutes = sum(
            t.plan_minutes for t in trips if problem.orders[t.stops[0].order_ref].brand == "Fresh"
        )
        resources = (
            ("reefer_space", reefer_used, reefer_total),
            ("reefer_fresh_minutes", float(fresh_minutes), float(len(reefers) * 270)),
            ("reefer_trip_slots", float(len(trips)), float(len(reefers) * 2)),
        )
        resource, used, capacity = max(resources, key=lambda r: r[1] / r[2] if r[2] else 0)
        return Bottleneck(
            resource,
            used,
            capacity,
            "Highest utilisation among eligible reefer resources; "
            "brand, district and per-vehicle limits also constrain the greedy plan",
        )
    active = [v for v in problem.vehicles.values() if v.switched_on and v.status == "available"]
    return Bottleneck(
        "trip_slots",
        float(len(assignment.trips)),
        float(2 * len(active)),
        "Each available vehicle can make at most two trips; "
        "brand, district and time also constrain insertion",
    )
