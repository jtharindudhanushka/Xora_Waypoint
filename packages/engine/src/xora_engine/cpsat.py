"""Integer CP-SAT allocation; shared predicates and sequencing remain the final authority."""

from dataclasses import replace
from math import ceil, floor

from ortools.sat.python import cp_model

from xora_engine.fuel import trip_litres
from xora_engine.models import EPSILON, Assignment, Problem, Stop, Trip
from xora_engine.planning import _scheduled
from xora_engine.policy import Policy, priority
from xora_engine.rules import RULES
from xora_engine.validation import validate

SCALE = 1_000_000
VALUE_SCALE = 1000
type Pair = tuple[str, str, int]
type Group = tuple[str, str, int, str, str]


def objective(assignment: Assignment, problem: Problem, policy: Policy) -> float:
    """BR-13/14 value minus trip/fuel cost; the exact comparison guards rounding/no improvement."""
    return sum(
        priority(problem.orders[s.order_ref], problem.festival_ramp, policy)
        for t in assignment.trips
        for s in t.stops
    ) - sum(
        policy.trip_cost
        + policy.litre_cost
        * trip_litres(
            [problem.orders[s.order_ref] for s in t.stops], problem.vehicles[t.vehicle], problem
        )
        for t in assignment.trips
    )


def _sequence(raw: Assignment, greedy: Assignment, problem: Problem) -> tuple[Assignment, bool]:
    """BR-12: replace an unschedulable trip with its greedy slot and remove duplicated refs."""
    result = Assignment()
    changed = False
    for trip in sorted(raw.trips, key=lambda t: (t.vehicle, t.trip_no)):
        if trip.locked and any(
            t.vehicle == trip.vehicle
            and (problem.orders[t.stops[0].order_ref].brand == "Fresh")
            == (problem.orders[trip.stops[0].order_ref].brand == "Fresh")
            and t.planned_depart + t.plan_minutes > trip.planned_depart
            for t in result.trips
        ):
            return greedy, True
        scheduled = trip if trip.locked else _scheduled(trip, result, problem)
        if scheduled is None:
            changed = True
            scheduled = next(
                (t for t in greedy.trips if (t.vehicle, t.trip_no) == (trip.vehicle, trip.trip_no)),
                None,
            )
            if scheduled is None:
                continue
            refs = {s.order_ref for s in scheduled.stops}
            cleaned: list[Trip] = []
            for previous in result.trips:
                stops = tuple(s for s in previous.stops if s.order_ref not in refs)
                if previous.locked and stops != previous.stops:
                    return greedy, True
                if stops:
                    candidate = (
                        previous
                        if stops == previous.stops
                        else _scheduled(
                            replace(previous, stops=stops), Assignment(tuple(cleaned)), problem
                        )
                    )
                    if candidate is None:
                        return greedy, True
                    cleaned.append(candidate)
            result = Assignment(tuple(cleaned))
            scheduled = _scheduled(scheduled, result, problem)
            if scheduled is None:
                continue
        used = {s.order_ref for t in result.trips for s in t.stops}
        stops = tuple(s for s in scheduled.stops if s.order_ref not in used)
        if not stops:
            continue
        if stops != scheduled.stops:
            changed = True
            scheduled = _scheduled(replace(scheduled, stops=stops), result, problem)
            if scheduled is None:
                continue
        result = Assignment((*result.trips, scheduled))
    return result, changed


def optimise(
    greedy: Assignment,
    problem: Problem,
    policy: Policy,
    locks: tuple[Trip, ...],
    time_limit_s: float,
    forced: str | None = None,
) -> tuple[Assignment, str]:
    """BR-01–11 allocation with repeatable search, hints and hard-validated fallback."""
    if not problem.orders or not problem.vehicles:
        return greedy, "GREEDY"
    model = cp_model.CpModel()
    x: dict[Pair, cp_model.IntVar] = {}
    y: dict[Group, cp_model.IntVar] = {}
    # Pruning uses the exact same BR predicates as validate()/the greedy planner.
    for order in problem.orders.values():
        for vehicle in problem.vehicles.values():
            if vehicle.km_per_l <= 0:
                continue
            solo = Assignment((Trip(vehicle.code, 1, (Stop(order.ref, order.units),), 210, 0),))
            if not all(
                check(solo, problem)
                for rid, _, _, check in RULES
                if rid in {"BR-02", "BR-03", "BR-04", "BR-06", "BR-10"}
            ):
                continue
            if _scheduled(solo.trips[0], Assignment(), problem) is None:
                continue
            for k in (1, 2):
                key = (order.ref, vehicle.code, k)
                x[key] = model.new_bool_var(f"x:{order.ref}:{vehicle.code}:{k}")
                group = (vehicle.code, order.brand, k, order.district, order.depot)
                if group not in y:
                    y[group] = model.new_bool_var(f"y:{group}")
                model.add(x[key] <= y[group])
    for order in problem.orders.values():
        terms = [var for (ref, _, _), var in x.items() if ref == order.ref]
        model.add(sum(terms) == 1 if order.ref == forced else sum(terms) <= 1)
    hint_trips: list[Trip] = []
    for vehicle in problem.vehicles.values():
        trips = [t for t in greedy.trips if t.vehicle == vehicle.code]
        if not any(t.locked for t in trips):
            trips = [
                replace(t, trip_no=k)
                for k, t in enumerate(
                    sorted(
                        trips,
                        key=lambda t: (
                            problem.orders[t.stops[0].order_ref].brand,
                            problem.orders[t.stops[0].order_ref].district,
                        ),
                    ),
                    1,
                )
            ]
        hint_trips.extend(trips)
    hint_pairs = {(s.order_ref, t.vehicle, t.trip_no) for t in hint_trips for s in t.stops}
    model.add(sum(x.values()) >= len(hint_pairs))
    model.add(
        sum(var for (ref, _, _), var in x.items() if problem.orders[ref].temp == "chilled")
        >= sum(problem.orders[ref].temp == "chilled" for ref, _, _ in hint_pairs)
    )
    locked = {(t.vehicle, t.trip_no): replace(t, locked=True) for t in locks}
    costs: list[cp_model.LinearExpr | int] = []
    for group, used in y.items():
        v, brand, k, district_name, _ = group
        terms = [
            var
            for (ref, code, number), var in x.items()
            if code == v
            and number == k
            and problem.orders[ref].brand == brand
            and problem.orders[ref].district == district_name
        ]
        model.add(sum(terms) >= used)
        district = problem.districts[district_name]
        base_fuel = (2 * district.depot_to_district_km - district.inter_stop_km) / problem.vehicles[
            v
        ].km_per_l
        costs.append(round((policy.trip_cost + policy.litre_cost * base_fuel) * VALUE_SCALE) * used)
        model.add_hint(
            used,
            int(
                any(
                    (problem.orders[r].brand, problem.orders[r].district) == (brand, district_name)
                    and code == v
                    and number == k
                    for r, code, number in hint_pairs
                )
            ),
        )
    for vehicle in problem.vehicles.values():
        occupied: list[cp_model.IntVar] = []
        for k in (1, 2):
            groups = [
                var for (v, _, number, _, _), var in y.items() if v == vehicle.code and number == k
            ]
            model.add_at_most_one(groups)
            slot_used = model.new_bool_var(f"used:{vehicle.code}:{k}")
            model.add(slot_used == sum(groups))
            occupied.append(slot_used)
            payload_terms = [
                (problem.orders[ref], var)
                for (ref, v, number), var in x.items()
                if v == vehicle.code and number == k
            ]
            for attr, capacity in (
                ("weight_kg", vehicle.weight_cap_kg),
                ("volume_m3", vehicle.volume_cap_m3),
            ):
                model.add(
                    sum(ceil(getattr(o, attr) * SCALE) * var for o, var in payload_terms)
                    <= floor((capacity + EPSILON) * SCALE)
                )
            if (vehicle.code, k) in locked:
                refs = {s.order_ref for s in locked[(vehicle.code, k)].stops}
                for order, var in payload_terms:
                    model.add(var == int(order.ref in refs))
        if not any(t.vehicle == vehicle.code for t in locks):
            model.add(occupied[1] <= occupied[0])
            # Slots are interchangeable before sequencing; canonical groups remove symmetry.
            # Use equal group ranks across k, rather than the global variable enumeration.
            names = sorted(
                {(brand, district) for v, brand, _, district, _ in y if v == vehicle.code}
            )
            rank_terms = [
                sum(
                    (names.index((brand, d)) + 1) * var
                    for (v, brand, number, d, _), var in y.items()
                    if v == vehicle.code and number == k
                )
                for k in (1, 2)
            ]
            model.add(rank_terms[0] <= rank_terms[1]).only_enforce_if(occupied)
        for fresh, budget in ((True, 270), (False, 480)):
            duration = sum(
                (problem.districts[d].depot_to_district_min - problem.districts[d].inter_stop_min)
                * var
                for (v, brand, _, d, _), var in y.items()
                if v == vehicle.code and (brand == "Fresh") == fresh
            ) + sum(
                (
                    problem.districts[problem.orders[ref].district].inter_stop_min
                    + problem.service_allowance[
                        (problem.orders[ref].brand, problem.orders[ref].dock_type)
                    ]
                )
                * var
                for (ref, v, _), var in x.items()
                if v == vehicle.code and (problem.orders[ref].brand == "Fresh") == fresh
            )
            model.add(duration <= budget)
        if vehicle.km_per_l > 0:
            fuel = sum(
                ceil(
                    (
                        2 * problem.districts[d].depot_to_district_km
                        - problem.districts[d].inter_stop_km
                    )
                    / vehicle.km_per_l
                    * SCALE
                )
                * var
                for (v, _, _, d, _), var in y.items()
                if v == vehicle.code
            ) + sum(
                ceil(
                    problem.districts[problem.orders[ref].district].inter_stop_km
                    / vehicle.km_per_l
                    * SCALE
                )
                * var
                for (ref, v, _), var in x.items()
                if v == vehicle.code
            )
            model.add(fuel <= floor((vehicle.fuel_remaining_l + EPSILON) * SCALE))
    values = []
    for (ref, v, k), var in x.items():
        order = problem.orders[ref]
        marginal_fuel = (
            problem.districts[order.district].inter_stop_km / problem.vehicles[v].km_per_l
        )
        values.append(
            round(
                (priority(order, problem.festival_ramp, policy) - policy.litre_cost * marginal_fuel)
                * VALUE_SCALE
            )
            * var
        )
        model.add_hint(var, int((ref, v, k) in hint_pairs))
    model.maximize(sum(values) - sum(costs))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = min(time_limit_s, 10)
    # BR-14: fixed interleaved batches synchronize workers before sharing incumbents.
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 0
    solver.parameters.interleave_search = True
    solver.parameters.interleave_batch_size = 16
    solver.parameters.max_deterministic_time = min(time_limit_s, 10) * 0.22
    try:
        # Brief neighbourhood search fixes existing daytime allocations, repacking Fresh
        # inside the same hard constraints. Its incumbent strengthens the greedy hint.
        # Both searches together use at most the caller's capped ten-second solver budget.
        if time_limit_s >= 1 and any(problem.orders[ref].brand != "Fresh" for ref, _, _ in x):
            neighbourhood = model.clone()
            for key, var in x.items():
                if problem.orders[key[0]].brand != "Fresh":
                    neighbourhood.add(var == int(key in hint_pairs))
            warm_solver = cp_model.CpSolver()
            warm_solver.parameters.max_time_in_seconds = min(time_limit_s, 10) * 0.2
            warm_solver.parameters.num_search_workers = 8
            warm_solver.parameters.random_seed = 0
            warm_solver.parameters.interleave_search = True
            warm_solver.parameters.interleave_batch_size = 16
            warm_solver.parameters.max_deterministic_time = min(time_limit_s, 10) * 0.05
            warm_status = warm_solver.solve(neighbourhood)
            if warm_status != cp_model.OPTIMAL and (
                warm_solver.response_proto.deterministic_time
                < warm_solver.parameters.max_deterministic_time
            ):
                # A wall-clock interruption must not introduce a machine-dependent hint.
                return greedy, "GREEDY"
            if warm_status in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
                model.clear_hints()  # type: ignore[no-untyped-call]  # OR-Tools lacks this annotation.
                for index in range(len(model.proto.variables)):
                    hint_var = model.get_bool_var_from_proto_index(index)
                    model.add_hint(hint_var, int(warm_solver.boolean_value(hint_var)))
            solver.parameters.max_time_in_seconds = max(
                0.001, min(time_limit_s, 10) - warm_solver.wall_time
            )
        status = solver.solve(model)
    except (RuntimeError, ValueError):
        return greedy, "GREEDY"
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return greedy, "GREEDY"
    if status == cp_model.FEASIBLE and (
        solver.response_proto.deterministic_time < solver.parameters.max_deterministic_time
    ):
        # Keep the ten-second safety cap; use the repeatable baseline on slow machines.
        return greedy, "GREEDY"
    decoded_trips: list[Trip] = []
    for vehicle in problem.vehicles.values():
        for k in (1, 2):
            stops = tuple(
                Stop(ref, problem.orders[ref].units)
                for (ref, v, number), var in x.items()
                if v == vehicle.code and number == k and solver.boolean_value(var)
            )
            if stops:
                decoded_trips.append(
                    locked.get((vehicle.code, k), Trip(vehicle.code, k, stops, 0, 0))
                )
    candidate, changed = _sequence(Assignment(tuple(decoded_trips)), greedy, problem)
    if validate(candidate, problem) or any(t not in candidate.trips for t in locked.values()):
        return greedy, "GREEDY"
    if forced and forced not in {s.order_ref for t in candidate.trips for s in t.stops}:
        return greedy, "GREEDY"
    # The trip-cost objective must never improve by simply withholding existing service.
    greedy_refs = {s.order_ref for t in greedy.trips for s in t.stops}
    candidate_refs = {s.order_ref for t in candidate.trips for s in t.stops}
    if len(candidate_refs) < len(greedy_refs) or sum(
        problem.orders[r].temp == "chilled" for r in candidate_refs
    ) < sum(problem.orders[r].temp == "chilled" for r in greedy_refs):
        return greedy, "GREEDY"
    if (
        sum(priority(problem.orders[r], problem.festival_ramp, policy) for r in candidate_refs)
        < sum(priority(problem.orders[r], problem.festival_ramp, policy) for r in greedy_refs)
        - EPSILON
    ):
        return greedy, "GREEDY"
    if objective(candidate, problem, policy) <= objective(greedy, problem, policy) + EPSILON:
        return greedy, "GREEDY"
    return candidate, "OPTIMAL" if status == cp_model.OPTIMAL and not changed else "FEASIBLE"
