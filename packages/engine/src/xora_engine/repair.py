"""Minimal operational repairs (BR-28–30), separate from whole-order Task 2B planning."""

from dataclasses import dataclass, replace

from xora_engine.models import Assignment, Order, Problem, Stop, Trip, Violation
from xora_engine.planning import likely_windows
from xora_engine.policy import DEFAULT_POLICY, Policy, priority
from xora_engine.timing import planned_arrivals, trip_minutes
from xora_engine.validation import validate


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02}:{minutes % 60:02}"


@dataclass(frozen=True)
class Shortfall:
    order_ref: str
    qty_missing: int
    vehicle: str
    trip_no: int
    now_minutes: int
    split_rule: str = "any"
    repick_minutes: int = 25
    unavailable_trips: frozenset[tuple[str, int]] = frozenset()


@dataclass(frozen=True)
class RepairArrival:
    vehicle: str
    trip_no: int
    order_ref: str
    plan_arrival: int
    likely_from: int
    likely_to: int
    at_risk: bool


@dataclass(frozen=True)
class RepairOption:
    label: str
    title: str
    assignment: Assignment
    delivered_now: int
    next_run_cases: int
    delay_minutes: int
    top_up_trip: tuple[str, int] | None
    breaks_store_rule: bool
    loss: float
    recommended: bool
    arrivals: tuple[RepairArrival, ...]
    effects: tuple[str, ...]


def operational_inputs(assignment: Assignment, problem: Problem) -> tuple[Assignment, Problem]:
    """Scale each linked portion, then reuse the exact BR-01–12 predicates.

    BR-30 permits linked operational portions; BR-05 remains unchanged for plan().
    Unique virtual refs prevent that exemption from hiding duplicated quantities.
    """
    orders: dict[str, Order] = {}
    trips: list[Trip] = []
    for trip in assignment.trips:
        stops: list[Stop] = []
        for index, stop in enumerate(trip.stops):
            original = problem.orders[stop.order_ref]
            ref = f"{original.ref}@{trip.vehicle}:{trip.trip_no}:{index}"
            ratio = stop.cases / original.units
            orders[ref] = replace(
                original,
                ref=ref,
                units=stop.cases,
                weight_kg=original.weight_kg * ratio,
                volume_m3=original.volume_m3 * ratio,
            )
            stops.append(replace(stop, order_ref=ref))
        trips.append(replace(trip, stops=tuple(stops)))
    return Assignment(tuple(trips)), replace(problem, orders=orders)


def _totals(assignment: Assignment) -> dict[str, int]:
    result: dict[str, int] = {}
    for trip in assignment.trips:
        for stop in trip.stops:
            result[stop.order_ref] = result.get(stop.order_ref, 0) + stop.cases
    return result


def validate_repair(
    candidate: Assignment,
    original: Assignment,
    shortfall: Shortfall,
    problem: Problem,
    next_run_cases: int = 0,
) -> list[Violation]:
    before = _totals(original)
    after = _totals(candidate)
    after[shortfall.order_ref] = after.get(shortfall.order_ref, 0) + next_run_cases
    if (
        before != after
        or next_run_cases < 0
        or any(s.cases < 0 for t in candidate.trips for s in t.stops)
    ):
        return [
            Violation(
                "BR-30",
                "QUANTITY_CONSERVATION",
                "A repair must preserve every case, including the linked top-up",
            )
        ]
    if any(s.order_ref not in problem.orders for t in candidate.trips for s in t.stops):
        return [Violation("BR-30", "UNKNOWN_ORDER", "A repair refers to an unknown order")]
    scaled_assignment, scaled_problem = operational_inputs(candidate, problem)
    return validate(scaled_assignment, scaled_problem)


def _schedule(trip: Trip, problem: Problem) -> Trip:
    minutes = trip_minutes([problem.orders[s.order_ref] for s in trip.stops], problem)
    trip = replace(trip, plan_minutes=minutes)
    return replace(
        trip,
        stops=tuple(
            replace(s, plan_arrival=a)
            for s, a in zip(trip.stops, planned_arrivals(trip, problem), strict=True)
        ),
    )


def forecast(assignment: Assignment, problem: Problem) -> tuple[RepairArrival, ...]:
    scaled, scaled_problem = operational_inputs(assignment, problem)
    windows = {s.order_ref: s for s in likely_windows(scaled, scaled_problem)}
    return tuple(
        RepairArrival(
            t.vehicle,
            t.trip_no,
            original.order_ref,
            windows[s.order_ref].plan_arrival,
            windows[s.order_ref].likely_from,
            windows[s.order_ref].likely_to,
            windows[s.order_ref].at_risk,
        )
        for t, original_trip in zip(scaled.trips, assignment.trips, strict=True)
        for s, original in zip(t.stops, original_trip.stops, strict=True)
    )


def _reschedule(
    trips: list[Trip], changed: Trip, shortfall: Shortfall, problem: Problem
) -> Assignment | None:
    end = 0
    updated: list[Trip] = []
    for trip in sorted(trips, key=lambda t: (t.vehicle, t.trip_no)):
        if trip.vehicle != changed.vehicle:
            updated.append(trip)
            continue
        departure = max(trip.planned_depart, end)
        if departure != trip.planned_depart and (
            trip.locked or (trip.vehicle, trip.trip_no) in shortfall.unavailable_trips
        ):
            return None
        if trip == changed or departure != trip.planned_depart:
            trip = _schedule(replace(trip, planned_depart=departure), problem)
        end = trip.planned_depart + trip.plan_minutes
        lane_end = 480 if problem.orders[trip.stops[0].order_ref].brand == "Fresh" else 960
        if end > lane_end:
            return None
        updated.append(trip)
    return Assignment(tuple(updated))


def repair(
    published: Assignment, shortfall: Shortfall, problem: Problem, policy: Policy = DEFAULT_POLICY
) -> tuple[RepairOption, ...]:
    """BR-28: recommend by loss, never apply; BR-29: label standing-rule conflicts."""
    if shortfall.split_rule not in {"any", "never", "same_morning_only"}:
        raise ValueError("Unknown store split rule")
    if shortfall.repick_minutes < 0:
        raise ValueError("Re-pick delay cannot be negative")
    affected = next(
        (
            t
            for t in published.trips
            if (t.vehicle, t.trip_no) == (shortfall.vehicle, shortfall.trip_no)
        ),
        None,
    )
    if (
        affected is None
        or affected.locked
        or (affected.vehicle, affected.trip_no) in shortfall.unavailable_trips
    ):
        return ()
    target = next((s for s in affected.stops if s.order_ref == shortfall.order_ref), None)
    if target is None or not 0 < shortfall.qty_missing <= target.cases:
        raise ValueError("Missing cases must be within the published quantity")
    if shortfall.order_ref not in problem.orders:
        raise ValueError("Unknown shortfall order")
    order = problem.orders[shortfall.order_ref]
    now_cases = target.cases - shortfall.qty_missing
    reduced = replace(
        affected,
        stops=tuple(
            replace(s, cases=now_cases) if s.order_ref == order.ref else s for s in affected.stops
        ),
    )
    base = [reduced if t == affected else t for t in published.trips]
    original_windows = {
        (a.vehicle, a.trip_no, a.order_ref): a for a in forecast(published, problem)
    }
    options: list[RepairOption] = []

    def add(
        label: str,
        title: str,
        candidate: Assignment | None,
        delay: int = 0,
        next_cases: int = 0,
        top_up: tuple[str, int] | None = None,
    ) -> None:
        if candidate is None or validate_repair(
            candidate, published, shortfall, problem, next_cases
        ):
            return
        arrivals = forecast(candidate, problem)
        effects: list[str] = []
        loss = priority(order, problem.festival_ramp, policy) * next_cases / order.units
        loss += delay * priority(order, problem.festival_ramp, policy) / 270
        for arrival in arrivals:
            previous = original_windows.get((arrival.vehicle, arrival.trip_no, arrival.order_ref))
            if (
                previous
                and arrival.order_ref != order.ref
                and (previous.likely_to != arrival.likely_to or previous.at_risk != arrival.at_risk)
            ):
                effects.append(
                    f"{problem.orders[arrival.order_ref].outlet}: likely "
                    f"{_clock(previous.likely_from)}–{_clock(previous.likely_to)} → "
                    f"{_clock(arrival.likely_from)}–{_clock(arrival.likely_to)}"
                )
                if arrival.at_risk and not previous.at_risk:
                    loss += priority(
                        problem.orders[arrival.order_ref], problem.festival_ramp, policy
                    )
        split = order.temp == "chilled" and now_cases > 0 and (next_cases > 0 or top_up is not None)
        same_morning = next_cases == 0 and all(
            a.likely_to < 720 for a in arrivals if a.order_ref == order.ref
        )
        breaks = split and (
            shortfall.split_rule == "never"
            or (shortfall.split_rule == "same_morning_only" and not same_morning)
        )
        options.append(
            RepairOption(
                label,
                title,
                candidate,
                target.cases if label == "B" else now_cases,
                next_cases,
                delay,
                top_up,
                breaks,
                loss,
                False,
                arrivals,
                tuple(effects),
            )
        )

    # A: append a linked top-up only to a later, compatible, editable morning trip.
    for later in sorted(published.trips, key=lambda t: (t.planned_depart, t.vehicle, t.trip_no)):
        if (
            later == affected
            or later.locked
            or later.planned_depart <= affected.planned_depart
            or later.planned_depart < shortfall.now_minutes + shortfall.repick_minutes
            or (later.vehicle, later.trip_no) in shortfall.unavailable_trips
            or problem.vehicles[later.vehicle].temp != "reefer"
            or problem.orders[later.stops[0].order_ref].brand != "Fresh"
        ):
            continue
        existing = any(s.order_ref == order.ref for s in later.stops)
        stops = tuple(
            replace(s, cases=s.cases + shortfall.qty_missing) if s.order_ref == order.ref else s
            for s in later.stops
        )
        if not existing:
            stops = (*stops, Stop(order.ref, shortfall.qty_missing))
        replacement = _schedule(replace(later, stops=stops), problem)
        candidate = _reschedule(
            [replacement if t == later else t for t in base], replacement, shortfall, problem
        )
        count = len(options)
        add(
            "A",
            f"Send {now_cases} now, {shortfall.qty_missing} more on Trip "
            f"{later.trip_no} this morning",
            candidate,
            top_up=(later.vehicle, later.trip_no),
        )
        if len(options) > count:
            break
    # B: preserve quantities; shift subsequent trips on this vehicle, rechecking all rules.
    delay = max(0, shortfall.now_minutes - affected.planned_depart) + shortfall.repick_minutes
    waiting = replace(affected, planned_depart=affected.planned_depart + delay)
    add(
        "B",
        f"Hold van ~{shortfall.repick_minutes} min for re-pick",
        _reschedule(
            [waiting if t == affected else t for t in published.trips], waiting, shortfall, problem
        ),
        delay=delay,
    )
    # C: retain the remaining quantity as an explicit linked next-run obligation.
    add(
        "C",
        f"Send {now_cases}, move {shortfall.qty_missing} to the next run",
        Assignment(tuple(base)),
        next_cases=shortfall.qty_missing,
    )
    if options:
        best = min(
            options, key=lambda option: (option.breaks_store_rule, option.loss, option.label)
        )
        options = [replace(option, recommended=option.label == best.label) for option in options]
    return tuple(options)
