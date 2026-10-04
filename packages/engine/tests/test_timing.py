from dataclasses import replace

import pytest

from xora_engine import District, trip_minutes
from xora_engine.fuel import trip_litres


@pytest.mark.parametrize(
    "district,docks,expected",
    [
        (District("Gampaha", 37, 9, 30, 3), ["rear_dock", "rear_dock", "street"], 101),
        (District("Colombo", 24, 8, 20, 2), ["street"] * 4, 112),
        (District("Colombo", 24, 8, 20, 2), ["street"] * 2, 64),
    ],
)
def test_br08_worked_examples(problem, district, docks, expected):
    orders = [
        replace(problem.orders["O1"], ref=f"O{i}", district=district.name, dock_type=dock)
        for i, dock in enumerate(docks)
    ]
    problem = replace(problem, districts={district.name: district})
    assert trip_minutes(orders, problem) == expected


def test_br08_empty_trip_has_zero_minutes(problem):
    assert trip_minutes([], problem) == 0


def test_br11_includes_return_distance(problem):
    assert trip_litres(list(problem.orders.values()), problem.vehicles["V1"], problem) == 4.2
