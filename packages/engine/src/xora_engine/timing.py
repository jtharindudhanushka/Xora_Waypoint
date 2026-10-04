"""Planning-standard integer minutes (BR-08); never reads a clock."""

from collections.abc import Sequence

from xora_engine.models import Order, Problem, Trip


def trip_minutes(orders: Sequence[Order], problem: Problem) -> int:
    if not orders:
        return 0
    district = problem.districts[orders[0].district]
    return (
        district.depot_to_district_min
        + district.inter_stop_min * (len(orders) - 1)
        + sum(problem.service_allowance[(o.brand, o.dock_type)] for o in orders)
    )


def planned_arrivals(trip: Trip, problem: Problem) -> tuple[int, ...]:
    """Arrival precedes service; each order consumes an allowance, including co-located ones."""
    if not trip.stops:
        return ()
    orders = [problem.orders[s.order_ref] for s in trip.stops]
    district = problem.districts[orders[0].district]
    arrival = trip.planned_depart + district.depot_to_district_min
    arrivals: list[int] = []
    for order in orders:
        arrivals.append(arrival)
        arrival += (
            problem.service_allowance[(order.brand, order.dock_type)] + district.inter_stop_min
        )
    return tuple(arrivals)
