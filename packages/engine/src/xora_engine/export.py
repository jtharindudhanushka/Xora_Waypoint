"""Task 2B serialisation, with no file or I/O imports; the caller writes the returned text."""

from xora_engine.models import Problem
from xora_engine.planning import PlanResult


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"' if any(c in value for c in ',"\r\n') else value


def export_task2b(result: PlanResult, problem: Problem, scenario: str) -> str:
    assignments = {s.order_ref: (t.vehicle, t.trip_no) for t in result.trips for s in t.stops}
    rows = ["scenario,order_ref,decision,vehicle_id,trip_id"]
    for ref in sorted(problem.orders):
        vehicle, number = assignments.get(ref, ("", 0))
        rows.append(
            ",".join(
                _quote(v)
                for v in (
                    scenario,
                    ref,
                    "served" if vehicle else "deferred",
                    vehicle,
                    str(number) if vehicle else "",
                )
            )
        )
    return "\n".join(rows) + "\n"
