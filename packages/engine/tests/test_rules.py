from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from xora_engine import Assignment, Problem, Stop, Trip, validate
from xora_engine.rules import RULES


def changed_order(problem: Problem, **changes: object) -> Problem:
    return replace(
        problem, orders={**problem.orders, "O1": replace(problem.orders["O1"], **changes)}
    )


def changed_vehicle(problem: Problem, **changes: object) -> Problem:
    return replace(problem, vehicles={"V1": replace(problem.vehicles["V1"], **changes)})


def rules(assignment: Assignment, problem: Problem) -> set[str]:
    return {v.rule_id for v in validate(assignment, problem)}


@pytest.mark.parametrize("rule", RULES, ids=[r[0] for r in RULES])
def test_all_br_predicates_accept_valid_assignment(rule, assignment, problem):
    assert rule[3](assignment, problem)


def test_br01_rejects_mixed_brands(assignment, problem):
    trip = replace(assignment.trips[0], stops=(Stop("O1", 10), Stop("O2", 10)))
    problem = replace(
        problem, orders={**problem.orders, "O2": replace(problem.orders["O2"], brand="Style")}
    )
    assert "BR-01" in rules(Assignment((trip,)), problem)


def test_br01_rejects_mixed_districts(assignment, problem):
    problem = replace(
        problem, orders={**problem.orders, "O2": replace(problem.orders["O2"], district="Other")}
    )
    trip = replace(assignment.trips[0], stops=(Stop("O1", 10), Stop("O2", 10)))
    assert "BR-01" in rules(Assignment((trip,)), problem)


def test_br02_chilled_requires_reefer(assignment, problem):
    assert "BR-02" in rules(assignment, changed_vehicle(problem, temp="ambient"))


def test_br02_ambient_allowed_on_reefer(assignment, problem):
    assert "BR-02" not in rules(assignment, changed_order(problem, temp="ambient"))


def test_br03_van_only_rejects_truck(assignment, problem):
    problem = changed_vehicle(changed_order(problem, parking="van_only"), type="truck")
    assert "BR-03" in rules(assignment, problem)


def test_br04_rejects_wrong_depot(assignment, problem):
    assert "BR-04" in rules(assignment, changed_order(problem, depot="Other"))


def test_br05_rejects_partial_order(assignment, problem):
    trip = replace(assignment.trips[0], stops=(Stop("O1", 9),))
    assert "BR-05" in rules(Assignment((trip,)), problem)


def test_br05_rejects_duplicate_order(assignment, problem):
    trip = replace(assignment.trips[0], trip_no=2)
    assert "BR-05" in rules(Assignment((*assignment.trips, trip)), problem)


def test_br06_weight_cap_rejects_overload(assignment, problem):
    violations = validate(assignment, changed_order(problem, weight_kg=1096))
    violation = next(v for v in violations if v.code == "WEIGHT_CAP")
    assert violation.message == "V1 trip 1: weight 1,096 / 1,040 kg"
    assert violation.context["used"] == 1096
    assert violation.context["capacity"] == 1040


def test_br06_volume_cap_rejects_overload(assignment, problem):
    assert "BR-06" in rules(assignment, changed_order(problem, volume_m3=10.000002))


@pytest.mark.parametrize("weight", [1040, 1040.0000005, 1040.000001])
def test_br06_weight_epsilon_accepts_boundary(assignment, problem, weight):
    assert "BR-06" not in rules(assignment, changed_order(problem, weight_kg=weight))


def test_br07_rejects_third_trip(assignment, problem):
    assert "BR-07" in rules(Assignment((replace(assignment.trips[0], trip_no=3),)), problem)


def test_br07_rejects_duplicate_trip_number(assignment, problem):
    assert "BR-07" in rules(Assignment(assignment.trips * 2), problem)


def test_br08_rejects_invented_duration(assignment, problem):
    assert "BR-08" in rules(Assignment((replace(assignment.trips[0], plan_minutes=39),)), problem)


def test_br08_rejects_invented_arrival(assignment, problem):
    trip = replace(assignment.trips[0], stops=(Stop("O1", 10, 0),))
    assert "BR-08" in rules(Assignment((trip,)), problem)


def test_br09_rejects_fresh_over_budget(assignment, problem):
    problem = replace(
        problem,
        districts={"Colombo": replace(problem.districts["Colombo"], depot_to_district_min=255)},
    )
    assert "BR-09" in rules(assignment, problem)


def test_br09_rejects_daytime_over_budget(assignment, problem):
    problem = changed_order(problem, brand="Style")
    problem = replace(
        problem,
        districts={"Colombo": replace(problem.districts["Colombo"], depot_to_district_min=471)},
    )
    assert "BR-09" in rules(assignment, problem)


def test_br09_keeps_fresh_and_daytime_budgets_separate(assignment, problem):
    problem = replace(
        problem,
        orders={**problem.orders, "O2": replace(problem.orders["O2"], brand="Style")},
        districts={"Colombo": replace(problem.districts["Colombo"], depot_to_district_min=250)},
    )
    fresh = replace(assignment.trips[0], plan_minutes=266)
    daytime = Trip("V1", 2, (Stop("O2", 10),), 480, 260)
    assert "BR-09" not in rules(Assignment((fresh, daytime)), problem)


@pytest.mark.parametrize("changes", [{"status": "in_workshop"}, {"switched_on": False}])
def test_br10_rejects_unavailable_vehicle(assignment, problem, changes):
    assert "BR-10" in rules(assignment, changed_vehicle(problem, **changes))


def test_br11_rejects_weekly_fuel_overrun(assignment, problem):
    assert "BR-11" in rules(assignment, changed_vehicle(problem, fuel_remaining_l=3.9))


def test_br11_accepts_exact_remaining_quota(assignment, problem):
    assert "BR-11" not in rules(assignment, changed_vehicle(problem, fuel_remaining_l=4))


@pytest.mark.parametrize("arrival, accepted", [(233, False), (234, True), (235, False)])
def test_br12_mall_window_inclusive(assignment, problem, arrival, accepted):
    problem = changed_order(problem, dock_type="mall_dock", mall_open=234, mall_close=234)
    trip = replace(assignment.trips[0], planned_depart=arrival - 24, plan_minutes=44)
    assert ("BR-12" not in rules(Assignment((trip,)), problem)) == accepted


@given(
    st.floats(min_value=0, max_value=1040, allow_nan=False),
    st.floats(min_value=0, max_value=10, allow_nan=False),
)
def test_br06_generated_feasible_loads_have_zero_violations(weight, volume):
    from xora_engine import District, Order, Vehicle

    order = Order(
        "O", "OUT", "Fresh", "D", "Depot", "chilled", "street", "none", 10, weight, volume
    )
    problem = Problem(
        {"O": order},
        {"V": Vehicle("V", "van", "reefer", 1040, 10, "Depot", 10, 100)},
        {"D": District("D", 24, 8, 20, 2)},
        {("Fresh", "street"): 16},
    )
    assignment = Assignment((Trip("V", 1, (Stop("O", 10),), 210, 40),))
    assert all(predicate(assignment, problem) for _, _, _, predicate in RULES)
    assert validate(assignment, problem) == []
