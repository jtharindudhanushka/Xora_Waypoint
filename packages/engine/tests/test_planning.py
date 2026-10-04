from dataclasses import replace

from hypothesis import given
from hypothesis import strategies as st

from xora_engine import District, Order, Problem, Vehicle, plan, validate
from xora_engine.export import export_task2b
from xora_engine.policy import priority


def test_br13_priority_formula(problem):
    order = replace(problem.orders["O1"], deferred_yesterday=True, days_since_last_served=2)
    assert priority(order, 1) == 1 * 1 * 1.8 * 3 * 1.5


def test_br06_greedy_splits_overloaded_van(problem):
    problem = replace(
        problem, orders={ref: replace(o, weight_kg=600) for ref, o in problem.orders.items()}
    )
    result = plan(problem)
    assert len(result.trips) == 2
    assert result.kpis.orders_served == 2
    assert validate(result.assignment, problem) == []


def test_br15_unavoidable_explains_no_reefer(problem):
    problem = replace(problem, vehicles={"V1": replace(problem.vehicles["V1"], temp="ambient")})
    result = plan(problem)
    assert all(
        d.reason_code == "NO_REEFER_CAPACITY" and d.group == "unavoidable" for d in result.deferrals
    )


def test_br16_choice_has_counterfactual_displaced_orders(problem):
    orders = {f"O{i}": replace(problem.orders["O1"], ref=f"O{i}", weight_kg=1000) for i in range(3)}
    result = plan(replace(problem, orders=orders))
    assert result.deferrals[0].group == "choice"
    assert result.deferrals[0].displaces


def test_br18_likely_window_waits_for_outlet_open(problem):
    problem = replace(
        problem, orders={r: replace(o, window_open=300) for r, o in problem.orders.items()}
    )
    result = plan(problem)
    assert all(s.likely_from >= 300 for s in result.likely_stops)


def test_br12_mall_bay_window_is_enforced(problem):
    problem = replace(
        problem,
        service_allowance={**problem.service_allowance, ("Fresh", "mall_bay"): 18},
        orders={
            "O1": replace(problem.orders["O1"], dock_type="mall_bay", mall_open=300, mall_close=320)
        },
    )
    result = plan(problem)
    assert result.kpis.orders_served == 1
    assert 300 <= result.trips[0].stops[0].plan_arrival <= 320


def test_br20_locked_trip_is_unchanged(assignment, problem):
    locked = replace(assignment.trips[0], locked=True)
    result = plan(problem, locks=(locked,))
    assert locked in result.trips


def test_task2b_export_has_one_decision_per_order(problem):
    text = export_task2b(plan(problem), problem, "SYNTHETIC")
    assert text.startswith("scenario,order_ref,decision,vehicle_id,trip_id\n")
    assert len(text.splitlines()) == len(problem.orders) + 1


@given(
    st.lists(
        st.tuples(
            st.floats(min_value=1, max_value=2000, allow_nan=False),
            st.floats(min_value=0.1, max_value=20, allow_nan=False),
        ),
        max_size=20,
    )
)
def test_br01_to_br12_every_generated_plan_passes_validate(loads):
    orders = {
        str(i): Order(
            str(i), str(i), "Fresh", "D", "Depot", "chilled", "street", "none", 10, kg, volume
        )
        for i, (kg, volume) in enumerate(loads)
    }
    vehicles = {"V": Vehicle("V", "van", "reefer", 1040, 10, "Depot", 10, 100)}
    problem = Problem(
        orders, vehicles, {"D": District("D", 24, 8, 20, 2)}, {("Fresh", "street"): 16}
    )
    result = plan(problem)
    assert validate(result.assignment, problem) == []
