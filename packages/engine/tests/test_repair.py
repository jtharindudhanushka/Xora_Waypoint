from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from xora_engine import (
    Assignment,
    District,
    Order,
    Problem,
    Shortfall,
    Stop,
    Trip,
    Vehicle,
    repair,
    validate_repair,
)
from xora_engine.repair import forecast
from xora_engine.timing import planned_arrivals, trip_minutes


def published(problem):
    trips = []
    for number, ref, depart in [(1, "O1", 240), (2, "O2", 360)]:
        t = Trip(
            "V1", number, (Stop(ref, 10),), depart, trip_minutes([problem.orders[ref]], problem)
        )
        trips.append(
            replace(t, stops=(replace(t.stops[0], plan_arrival=planned_arrivals(t, problem)[0]),))
        )
    return Assignment(tuple(trips))


def test_br28_returns_a_b_c_and_recommends_without_mutating_published(problem):
    original = published(problem)
    options = repair(original, Shortfall("O1", 2, "V1", 1, 230), problem)
    assert [o.label for o in options] == ["A", "B", "C"]
    assert [o.label for o in options if o.recommended] == ["A"]
    assert original.trips[0].stops[0].cases == 10
    assert options[0].assignment.trips[0].stops[0].cases == 8
    assert options[0].top_up_trip == ("V1", 2)


@pytest.mark.parametrize(
    "rule,a_breaks,c_breaks,recommended",
    [
        ("same_morning_only", False, True, "A"),
        ("any", False, False, "A"),
        ("never", True, True, "B"),
    ],
)
def test_br29_store_split_rule_labels_conflicts(problem, rule, a_breaks, c_breaks, recommended):
    options = repair(published(problem), Shortfall("O1", 2, "V1", 1, 230, rule), problem)
    by_label = {o.label: o for o in options}
    assert by_label["A"].breaks_store_rule == a_breaks
    assert by_label["C"].breaks_store_rule == c_breaks
    assert next(o.label for o in options if o.recommended) == recommended


def test_br06_top_up_cannot_overload_later_trip(problem):
    orders = {ref: replace(o, weight_kg=1040) for ref, o in problem.orders.items()}
    problem = replace(problem, orders=orders)
    options = repair(published(problem), Shortfall("O1", 2, "V1", 1, 230), problem)
    assert "A" not in {o.label for o in options}


def test_br28_locked_and_departed_trips_never_change(problem):
    assignment = published(problem)
    original = replace(assignment.trips[0], locked=True)
    assert (
        repair(
            Assignment((original, assignment.trips[1])), Shortfall("O1", 2, "V1", 1, 230), problem
        )
        == ()
    )
    options = repair(
        assignment,
        Shortfall("O1", 2, "V1", 1, 230, unavailable_trips=frozenset({("V1", 2)})),
        problem,
    )
    assert "A" not in {o.label for o in options}
    assert all(o.assignment.trips[1] == assignment.trips[1] for o in options)


def test_br28_hold_shifts_following_trip_and_recomputes_windows(problem):
    assignment = published(problem)
    options = repair(assignment, Shortfall("O1", 2, "V1", 1, 230), problem)
    held = next(o for o in options if o.label == "B")
    before = forecast(assignment, problem)[0]
    after = held.arrivals[0]
    assert after.likely_from == before.likely_from + 25
    assert after.likely_to == before.likely_to + 25


def test_br30_quantity_conservation_cannot_be_bypassed(problem):
    original = published(problem)
    bad = replace(original.trips[0], stops=(replace(original.trips[0].stops[0], cases=11),))
    violations = validate_repair(
        Assignment((bad, original.trips[1])), original, Shortfall("O1", 2, "V1", 1, 230), problem
    )
    assert violations[0].rule_id == "BR-30"


def test_br28_topup_waits_for_repick_and_rechecks_later_trip_budget(problem):
    original = published(problem)
    value = Shortfall("O1", 2, "V1", 1, 350)
    option = next(o for o in repair(original, value, problem) if o.label == "A")
    later = next(t for t in option.assignment.trips if t.trip_no == 2)
    assert later.planned_depart >= 375
    assert option.assignment.trips[0].planned_depart == 350
    assert not validate_repair(option.assignment, original, value, problem)


def test_br28_br29_shortfall_on_trip_two_never_topups_an_earlier_trip(problem):
    original = published(problem)
    value = Shortfall("O2", 2, "V1", 2, 350, "same_morning_only")
    options = {o.label: o for o in repair(original, value, problem)}
    assert set(options) == {"B", "C"}
    assert options["B"].recommended
    assert not options["B"].breaks_store_rule
    assert options["C"].breaks_store_rule
    for option in options.values():
        assert option.assignment.trips[0] == original.trips[0]
        assert not validate_repair(
            option.assignment, original, value, problem, option.next_run_cases
        )


def test_br28_br29_trip_two_can_topup_a_later_compatible_vehicle(problem):
    problem = replace(
        problem,
        orders={**problem.orders, "O3": replace(problem.orders["O1"], ref="O3", outlet="OUT3")},
        vehicles={**problem.vehicles, "V2": replace(problem.vehicles["V1"], code="V2")},
    )
    original = Assignment((*published(problem).trips, Trip("V2", 1, (Stop("O3", 10),), 400, 40)))
    value = Shortfall("O2", 2, "V1", 2, 350, "same_morning_only")
    options = {o.label: o for o in repair(original, value, problem)}
    assert set(options) == {"A", "B", "C"}
    assert options["A"].recommended
    assert options["A"].top_up_trip == ("V2", 1)
    assert "Trip 1 on V2" in options["A"].title
    assert not options["A"].breaks_store_rule
    assert options["C"].breaks_store_rule
    assert not validate_repair(options["A"].assignment, original, value, problem)


@given(st.integers(min_value=1, max_value=10))
def test_br30_every_repair_preserves_quantity_and_passes_shared_rules(missing):
    order = Order(
        "O1", "OUT1", "Fresh", "Colombo", "Depot", "chilled", "street", "normal", 10, 100, 1
    )
    problem = Problem(
        {"O1": order, "O2": replace(order, ref="O2", outlet="OUT2")},
        {"V1": Vehicle("V1", "van", "reefer", 1040, 10, "Depot", 10, 100)},
        {"Colombo": District("Colombo", 24, 8, 20, 2)},
        {("Fresh", "street"): 16},
    )
    original = published(problem)
    shortfall = Shortfall("O1", missing, "V1", 1, 230)
    for option in repair(original, shortfall, problem):
        assert (
            validate_repair(option.assignment, original, shortfall, problem, option.next_run_cases)
            == []
        )
