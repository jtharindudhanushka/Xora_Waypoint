# 06 · Planning engine (`packages/engine`)

A **pure Python package**: no FastAPI, no SQLAlchemy, no I/O. It takes plain dataclasses in and returns dataclasses out. The API adapts DB rows into engine inputs. The same package can run Datathon Task 2B and be checked by the organisers' `check_allocation.py`. Decision: [ADR-0005](adr/0005-engine-as-library.md).

## Public interface
```python
from xora_engine import Problem, Policy, plan, validate, explain, repair, trip_minutes

result: PlanResult = plan(problem: Problem, policy: Policy = Policy(), locks: list[LockedTrip] = [], time_limit_s: float = 10)
violations: list[Violation] = validate(assignment: Assignment, problem: Problem)   # used live for drag-and-drop (BR-19)
options: list[RepairOption] = repair(published: Assignment, shortfall: Shortfall, problem: Problem, policy: Policy)  # BR-28
```

### Inputs (`Problem`)
| Field | Content |
|---|---|
| `orders` | ref, outlet, brand, district, depot, temp, dock_type, parking, mall window, window, units, kg, m³, deferred_yesterday, days_since_last_served |
| `vehicles` | code, type, temp, kg cap, m³ cap, depot, km_per_l, fuel quota remaining (L), switched_on |
| `districts` | depot_to_district min and km, inter_stop min and km |
| `service_allowance` | (brand, dock_type) → minutes |
| `calendar` | festival_ramp for the operating date |
| `travel_ratio` | (district, hour) → p50/p90 ratio (for the likely window) |

### Outputs (`PlanResult`)
- `trips`: vehicle, trip_no, brand, district, lane, plan_minutes, litres, kg, m³, plus stops (seq, outlet, orders, plan_arrival, likely window, at_risk).
- `deferrals`: order, reason_code, group (`unavoidable` / `choice`), priority, displaces[], next_run.
- `kpis`: orders served, chilled served, stops at risk, reefer m³ used/total, value served.
- `bottleneck`: `{resource, used, capacity, explanation}`.
- `solver`: status (`OPTIMAL` / `FEASIBLE` / `GREEDY`), gap, ms.

## Rules implemented (`rules.py`, one function per BR)
BR-01 to BR-12 are each a pure predicate. `validate()` runs them all and returns `Violation(rule_id, code, message, context)`. The solver builds the same constraints, so **one rule definition serves both validation and optimisation**, with a test asserting they agree.

## Trip time (BR-08), shared with the organisers' formula
```
trip_minutes = D[district].depot_to_district_freeflow_min
             + D[district].inter_stop_freeflow_min × (n_orders − 1)
             + Σ service_allowance[(brand, dock_type)]
```
Worked checks, which are unit tests:
- Fresh Gampaha, 2 rear dock + 1 street: 37 + 9×2 + 15 + 15 + 16 = **101**.
- Fresh Colombo, 4 street: 24 + 8×3 + 16×4 = **112**.
- VEH036 Colombo (OUT001, OUT003): 24 + 8 + 16 + 16 = **64**.

## Objective (BR-13, BR-14)
```
priority(o) = base × perish × skip × peak × window          (reported 0–100 after scaling)
  base   = volume_m3 × brand_weight      (Fresh 1.0 · Style 0.6 · Tech 1.2)
  perish = 1.8 if chilled else 1.0
  skip   = 1 + 0.5 × days_since_last_served + 1.0 × deferred_yesterday
  peak   = 1 + 0.5 × festival_ramp
  window = 1.2 if mall_dock else 1.0
maximise  Σ_served priority(o)  −  Σ_trips (5 + 0.2 × litres)  −  reefer_protection_penalty
reefer_protection_penalty = λ × ambient m³ placed on reefers   (λ > 0 only when reefer space is binding)
```
The weights are **assumptions**, kept in `policy.py` defaults, shown in the UI ("How priority is calculated") and documented in the README. The units are value units, not LKR.

## Solving
| Step | Method | Notes |
|---|---|---|
| 1. Prune | Build only compatible (order, vehicle) pairs: depot, temp, van_only, switched on | Shrinks the model |
| 2. Greedy | Sort by priority ÷ scarce capacity; group by (brand, district); first-fit decreasing into trips; check BR-06, BR-09, BR-11 | < 100 ms. Warm start and fallback |
| 3. CP-SAT | OR-Tools: `x[o,v,k]`, `y[v,k,g]`, capacity, time budgets (integer minutes), fuel, locks fixed. Objective as above; hint = greedy | 10 s limit. Reports status and gap |
| 4. Sequence | Per trip: mall stops inside their window, then earliest window close, then nearest | Plan arrival times |
| 5. Likely window | Propagate along stops: travel × ratio(p50…p90 by district and hour) + service; wait for the window to open | `at_risk` if likely_to > window close (BR-18) |
| 6. Explain | Below | |

**Scale check:** S1 is 85 orders × (27 switched-on vehicles × 2 trips), after pruning. It solves in seconds.

Implementation: `cpsat.py` uses OR-Tools 9.15, eight workers, fixed seed 0 and
deterministic interleaved batches of 16 ([ADR-0009](adr/0009-repeatable-planning-search.md)).
Canonical order, vehicle and lock ordering makes DB row order irrelevant. The maximum
ten-second wall-clock solver budget is also bounded by deterministic work: 0.5 units
for the Fresh neighbourhood and 2.2 for the full search at the default limit.
A brief Fresh neighbourhood search strengthens the initial greedy
hint; the full model uses the remaining budget. kg, m³ and litres are conservatively
scaled by 1,000,000, with the same 1e-6 capacity epsilon. Objective value/trip/fuel
coefficients use scale 1,000. Symmetry ordering applies only to unlocked slots.
The selected candidate must improve the exact objective without reducing served
order count, chilled count or priority value below the greedy baseline.

Both backends use the same sequencing, validation, explanation and KPI functions.
Impossible singleton mall windows are pruned; an unschedulable grouped trip tries
its greedy slot, then the entire candidate is validated again. Failure, timeout
without a solution, a worse candidate or broken locks returns GREEDY. OPTIMAL is
reported only for an unchanged, validated globally solved integer model; repaired
or time-limited incumbents report FEASIBLE. API elapsed time also includes model
construction, validation and explanations, so it can exceed ten seconds. If the
wall-clock cap interrupts a deterministic search before its work budget completes,
the result is GREEDY instead of a timing-dependent partial incumbent.

## Explanations (BR-15 to BR-17)
- **Reason code per deferral:** try to insert the order into every vehicle and trip and keep the *first* blocking rule. If it fits somewhere but wasn't chosen, the code is `LOWER_PRIORITY`.
- **Group:** re-solve with `served[o] = 1` forced. If infeasible → `unavoidable`. Otherwise `choice`, and `displaces` = orders dropped in that solution (used for "Serve instead").
- **Bottleneck:** utilisation of reefer m³ over reefer trips, van-only capacity, Fresh minutes and dry m³. The binding resource is the one at capacity with deferrals in its class.
- **Counterfactual** (optional, cached): +1 of the bottleneck resource → orders recovered.

## Repair (BR-28 to BR-30)
Input: a published assignment + shortfall `{order, qty_missing}`. Up to 3 candidate options:

| Option | Rule |
|---|---|
| A · Send now + top-up later the same morning | Only if a same-depot reefer trip later that morning has capacity and time (BR-06, BR-09); respects `split_rule = same_morning_only` |
| B · Hold the van for a re-pick (~25 min) | Recompute likely windows; report risk changes on later stops |
| C · Send now, move the rest to the next run | Flags `breaks_store_rule` when `split_rule ≠ any` |

The options are ranked by loss. Locked and departed trips are never changed.

## Tests
- Unit tests per rule (positive and negative).
- Trip-time worked checks.
- Property tests (Hypothesis): every `plan()` output passes `validate()`.
- **S1 regression:** VEH036 can't carry OUT001+OUT002+OUT003 (1,095.7 kg > 1,040 kg); OUT074 is served; the result passes `validate()`.
- **CI step (when `datasets/` exists):** export the S1 plan to Task 2B CSV format → `python datasets/check_allocation.py` must print `FEASIBILITY: PASSED`.
