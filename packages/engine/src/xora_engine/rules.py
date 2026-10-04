"""One definition per hard rule, shared by validation and every planner (BR-01…BR-12)."""

from collections.abc import Callable

from xora_engine.fuel import trip_litres
from xora_engine.models import EPSILON, Assignment, ContextValue, Problem, Trip, Violation
from xora_engine.timing import planned_arrivals, trip_minutes

type Predicate = Callable[[Assignment, Problem], bool]


def _orders(trip: Trip, problem: Problem) -> list[str]:
    return [s.order_ref for s in trip.stops]


def br01(assignment: Assignment, problem: Problem) -> bool:
    return all(
        len({(problem.orders[r].brand, problem.orders[r].district) for r in _orders(t, problem)})
        <= 1
        for t in assignment.trips
    )


def br02(assignment: Assignment, problem: Problem) -> bool:
    return all(
        problem.orders[s.order_ref].temp != "chilled"
        or problem.vehicles[t.vehicle].temp == "reefer"
        for t in assignment.trips
        for s in t.stops
    )


def br03(assignment: Assignment, problem: Problem) -> bool:
    return all(
        problem.orders[s.order_ref].parking != "van_only"
        or problem.vehicles[t.vehicle].type == "van"
        for t in assignment.trips
        for s in t.stops
    )


def br04(assignment: Assignment, problem: Problem) -> bool:
    return all(
        problem.orders[s.order_ref].depot == problem.vehicles[t.vehicle].depot
        for t in assignment.trips
        for s in t.stops
    )


def br05(assignment: Assignment, problem: Problem) -> bool:
    refs = [s.order_ref for t in assignment.trips for s in t.stops]
    return len(refs) == len(set(refs)) and all(
        s.cases == problem.orders[s.order_ref].units for t in assignment.trips for s in t.stops
    )


def br06(assignment: Assignment, problem: Problem) -> bool:
    return all(
        sum(problem.orders[r].weight_kg for r in _orders(t, problem))
        <= problem.vehicles[t.vehicle].weight_cap_kg + EPSILON
        and sum(problem.orders[r].volume_m3 for r in _orders(t, problem))
        <= problem.vehicles[t.vehicle].volume_cap_m3 + EPSILON
        for t in assignment.trips
    )


def br07(assignment: Assignment, problem: Problem) -> bool:
    keys = [(t.vehicle, t.trip_no) for t in assignment.trips]
    return (
        len(keys) == len(set(keys))
        and all(t.trip_no in (1, 2) for t in assignment.trips)
        and all(sum(t.vehicle == v for t in assignment.trips) <= 2 for v in problem.vehicles)
    )


def br08(assignment: Assignment, problem: Problem) -> bool:
    return all(
        t.plan_minutes == trip_minutes([problem.orders[r] for r in _orders(t, problem)], problem)
        and all(
            s.plan_arrival is None or s.plan_arrival == arrival
            for s, arrival in zip(t.stops, planned_arrivals(t, problem), strict=True)
        )
        for t in assignment.trips
    )


def br09(assignment: Assignment, problem: Problem) -> bool:
    for vehicle in problem.vehicles:
        fresh = daytime = 0
        for trip in assignment.trips:
            if trip.vehicle != vehicle or not trip.stops:
                continue
            orders = [problem.orders[r] for r in _orders(trip, problem)]
            minutes = trip_minutes(orders, problem)
            if orders[0].brand == "Fresh":
                fresh += minutes
            else:
                daytime += minutes
        if fresh > 270 or daytime > 480:
            return False
    return True


def br10(assignment: Assignment, problem: Problem) -> bool:
    return all(
        problem.vehicles[t.vehicle].status == "available"
        and problem.vehicles[t.vehicle].switched_on
        for t in assignment.trips
    )


def br11(assignment: Assignment, problem: Problem) -> bool:
    return all(
        sum(
            trip_litres([problem.orders[r] for r in _orders(t, problem)], v, problem)
            for t in assignment.trips
            if t.vehicle == v.code
        )
        <= v.fuel_remaining_l + EPSILON
        for v in problem.vehicles.values()
    )


def br12(assignment: Assignment, problem: Problem) -> bool:
    for trip in assignment.trips:
        for stop, arrival in zip(trip.stops, planned_arrivals(trip, problem), strict=True):
            order = problem.orders[stop.order_ref]
            if (order.dock_type in ("mall_dock", "mall_bay") or order.mall_open is not None) and (
                order.mall_open is None
                or order.mall_close is None
                or not order.mall_open <= arrival <= order.mall_close
            ):
                return False
    return True


RULES: tuple[tuple[str, str, str, Predicate], ...] = (
    ("BR-01", "TRIP_GROUP", "Each trip needs one brand and one district", br01),
    ("BR-02", "NO_REEFER_CAPACITY", "Chilled orders need a reefer", br02),
    ("BR-03", "NO_VAN_AVAILABLE", "Van-only outlets need a van", br03),
    ("BR-04", "DEPOT_MISMATCH", "Orders need a vehicle from their home depot", br04),
    ("BR-05", "WHOLE_ORDER", "Each assigned order must be carried whole exactly once", br05),
    ("BR-06", "CAPACITY", "Trip weight or volume exceeds capacity", br06),
    ("BR-07", "TRIP_LIMIT", "Each vehicle has at most two uniquely numbered trips (1, 2)", br07),
    ("BR-08", "TRIP_TIME", "Trip duration or arrival differs from the planning standard", br08),
    ("BR-09", "TIME_BUDGET", "Vehicle exceeds its Fresh or daytime time budget", br09),
    ("BR-10", "VEHICLE_UNAVAILABLE", "Vehicle must be available and switched on", br10),
    ("BR-11", "FUEL_QUOTA", "Vehicle exceeds its remaining weekly fuel quota", br11),
    ("BR-12", "MALL_WINDOW", "Mall arrival must fall inside its mall window", br12),
)


def capacity_violations(assignment: Assignment, problem: Problem) -> list[Violation]:
    """Numeric diagnostics after the BR-06 predicate fails."""
    violations: list[Violation] = []
    for trip in assignment.trips:
        vehicle = problem.vehicles[trip.vehicle]
        for resource, capacity, unit, code in (
            ("weight", vehicle.weight_cap_kg, "kg", "WEIGHT_CAP"),
            ("volume", vehicle.volume_cap_m3, "m³", "VOLUME_CAP"),
        ):
            used = sum(
                problem.orders[r].weight_kg if resource == "weight" else problem.orders[r].volume_m3
                for r in _orders(trip, problem)
            )
            if used > capacity + EPSILON:
                context: dict[str, ContextValue] = {
                    "vehicle": trip.vehicle,
                    "trip_no": trip.trip_no,
                    "resource": resource,
                    "used": used,
                    "capacity": capacity,
                }
                violations.append(
                    Violation(
                        "BR-06",
                        code,
                        f"{trip.vehicle} trip {trip.trip_no}: "
                        f"{resource} {used:,.6g} / {capacity:,.6g} {unit}",
                        context,
                    )
                )
    return violations
