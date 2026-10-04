"""BR-11 includes the return distance even though BR-08 excludes return time."""

from collections.abc import Sequence

from xora_engine.models import Order, Problem, Vehicle


def trip_litres(orders: Sequence[Order], vehicle: Vehicle, problem: Problem) -> float:
    if not orders:
        return 0.0
    if vehicle.km_per_l <= 0:
        return float("inf")
    district = problem.districts[orders[0].district]
    return (
        2 * district.depot_to_district_km + district.inter_stop_km * (len(orders) - 1)
    ) / vehicle.km_per_l
