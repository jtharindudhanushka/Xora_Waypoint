from dataclasses import replace

import pytest

from xora_engine import Assignment, District, Order, Problem, Stop, Trip, Vehicle, trip_minutes


@pytest.fixture
def problem() -> Problem:
    order = Order(
        "O1", "OUT1", "Fresh", "Colombo", "Depot", "chilled", "street", "none", 10, 100, 1
    )
    return Problem(
        {"O1": order, "O2": replace(order, ref="O2", outlet="OUT2")},
        {"V1": Vehicle("V1", "van", "reefer", 1040, 10, "Depot", 10, 100)},
        {"Colombo": District("Colombo", 24, 8, 20, 2)},
        {
            ("Fresh", "street"): 16,
            ("Fresh", "rear_dock"): 15,
            ("Fresh", "mall_dock"): 20,
            ("Style", "street"): 10,
        },
    )


@pytest.fixture
def assignment(problem: Problem) -> Assignment:
    return Assignment(
        (Trip("V1", 1, (Stop("O1", 10),), 210, trip_minutes([problem.orders["O1"]], problem)),)
    )
