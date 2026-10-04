"""Aggregate shared predicates into UI-ready violations."""

from xora_engine.models import Assignment, Problem, Violation
from xora_engine.rules import RULES, capacity_violations


def validate(assignment: Assignment, problem: Problem) -> list[Violation]:
    violations: list[Violation] = []
    for trip in assignment.trips:
        if trip.vehicle not in problem.vehicles:
            violations.append(
                Violation("BR-10", "UNKNOWN_VEHICLE", f"Unknown vehicle {trip.vehicle}")
            )
        if not trip.stops:
            violations.append(Violation("BR-05", "EMPTY_TRIP", "A trip needs at least one order"))
        for stop in trip.stops:
            if stop.order_ref not in problem.orders:
                violations.append(
                    Violation("BR-05", "UNKNOWN_ORDER", f"Unknown order {stop.order_ref}")
                )
    if violations:
        return violations
    for rule_id, code, message, predicate in RULES:
        if not predicate(assignment, problem):
            if rule_id == "BR-06":
                violations.extend(capacity_violations(assignment, problem))
            else:
                violations.append(Violation(rule_id, code, message))
    return violations
