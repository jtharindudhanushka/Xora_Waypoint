from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st
from ortools.sat.python import cp_model

from xora_engine import Assignment, District, Order, Problem, Stop, Trip, Vehicle, plan, validate
from xora_engine.cpsat import _sequence, objective
from xora_engine.planning import _greedy
from xora_engine.policy import DEFAULT_POLICY


def packing(volumes: list[int]) -> Problem:
    return Problem(
        {
            str(i): Order(
                str(i),
                str(i),
                "Fresh",
                "D",
                "Depot",
                "chilled",
                "street",
                "none",
                10,
                100,
                float(volume),
            )
            for i, volume in enumerate(volumes)
        },
        {"V": Vehicle("V", "van", "reefer", 1040, 10, "Depot", 10, 100)},
        {"D": District("D", 24, 8, 20, 2)},
        {("Fresh", "street"): 16},
    )


def test_br13_cpsat_beats_greedy_packing_and_serves_more_chilled():
    problem = packing([4, 4, 6, 6, 6])
    greedy = _greedy(problem, DEFAULT_POLICY)
    result = plan(problem, time_limit_s=1)
    assert sum(len(t.stops) for t in greedy.trips) == 3
    assert result.kpis.orders_served == result.kpis.chilled_served == 4
    assert result.kpis.reefer_m3_used == 20
    assert objective(result.assignment, problem, DEFAULT_POLICY) > objective(
        greedy, problem, DEFAULT_POLICY
    )
    assert result.solver_status == "OPTIMAL"
    assert not validate(result.assignment, problem)


@settings(max_examples=30, deadline=None)
@given(st.lists(st.integers(min_value=1, max_value=12), min_size=1, max_size=12))
def test_br01_to_br12_cpsat_output_always_passes_shared_validate(volumes):
    problem = packing(volumes)
    result = plan(problem, time_limit_s=0.1)
    assert not validate(result.assignment, problem)
    assert result.solver_status in {"OPTIMAL", "FEASIBLE", "GREEDY"}


def test_br20_cpsat_keeps_locked_quantities_sequence_and_departure():
    problem = packing([4, 4, 6, 6, 6])
    first = _greedy(problem, DEFAULT_POLICY).trips[0]
    locked = replace(first, locked=True)
    result = plan(problem, locks=(locked,), time_limit_s=0.5)
    assert locked in result.trips
    assert not validate(result.assignment, problem)


def test_br11_cpsat_never_exceeds_remaining_weekly_fuel():
    problem = packing([4, 4, 6, 6, 6])
    problem = replace(problem, vehicles={"V": replace(problem.vehicles["V"], fuel_remaining_l=4.2)})
    result = plan(problem, time_limit_s=0.5)
    assert len(result.trips) == 1
    assert not validate(result.assignment, problem)


def test_br12_unschedulable_trip_uses_greedy_slot():
    problem = packing([4, 4])
    problem = replace(
        problem,
        orders={
            "0": problem.orders["0"],
            "1": replace(problem.orders["1"], mall_open=1440, mall_close=1450),
        },
    )
    greedy = _greedy(problem, DEFAULT_POLICY)
    candidate, changed = _sequence(
        Assignment((Trip("V", 1, (Stop("0", 10), Stop("1", 10)), 0, 0),)), greedy, problem
    )
    assert changed
    assert {s.order_ref for t in candidate.trips for s in t.stops} == {"0"}
    assert not validate(candidate, problem)


def test_br13_solver_failure_keeps_validated_greedy(monkeypatch):
    problem = packing([4, 4, 6, 6, 6])

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic solver failure")

    monkeypatch.setattr(cp_model.CpSolver, "solve", fail)
    result = plan(problem)
    assert result.solver_status == "GREEDY"
    assert result.assignment == _greedy(problem, DEFAULT_POLICY)
    assert not validate(result.assignment, problem)


def test_br14_cpsat_repeats_for_same_input_regardless_of_row_order():
    problem = packing([4, 4, 6, 6, 6])
    reversed_rows = replace(problem, orders=dict(reversed(list(problem.orders.items()))))
    results = [plan(p, time_limit_s=1) for p in (problem, reversed_rows, problem)]
    assert all(r.assignment == results[0].assignment for r in results)
    assert all(r.solver_status == results[0].solver_status for r in results)
    assert all(not validate(r.assignment, problem) for r in results)
