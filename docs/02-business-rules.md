# 02 · Business rules

**This is the single source of truth for behaviour.** Each rule has an ID (`BR-xx`), an enforcement point, and the **Figma screen** that promises it.
- Code and tests reference rule IDs (e.g. `# BR-07`, `test_br07_reefer_required`).
- Enforced in: **E** = engine (`packages/engine`), **A** = API (`services/api`), **W** = web (UX only; never the sole guard).
- When a rule changes, update it here first.

---

## A. Hard planning rules (never violated; mirror the organisers' `check_allocation.py`)
| ID | Rule | Enforced | Screens |
|---|---|---|---|
| BR-01 | All orders on one vehicle trip share **one brand and one district** | E | D1, D2 |
| BR-02 | Orders with `temp_requirement = chilled` need a vehicle with `temp = reefer`. Reefers may also carry ambient | E | D1, D2 |
| BR-03 | Outlets with `parking_constraint = van_only` need a vehicle with `type = van` | E | D1, R2 |
| BR-04 | A vehicle serves only outlets of **its own home depot** | E | D1 |
| BR-05 | **Whole orders** in the plan: an order isn't split across trips or vehicles at plan time (operational top-ups are BR-24) | E | D1 |
| BR-06 | Per trip, Σ`order_volume_m3` ≤ `volume_cap_m3` **and** Σ`order_weight_kg` ≤ `weight_cap_kg` | E | D1, D2, L2 |
| BR-07 | At most **2 trips per vehicle per day** | E | D1 |
| BR-08 | **Trip time (plan standard)** = `depot_to_district_freeflow_min` + `inter_stop_freeflow_min` × (n_orders − 1) + Σ `service_allowance_min(brand, dock_type)`. The return trip is not added | E | D1 timeline bars |
| BR-09 | Per vehicle: Σ Fresh trip minutes ≤ **270** (pre-dawn 03:30–08:00). Σ Style + Tech trip minutes ≤ **480** (daytime). The budgets are separate, but BR-07 still caps the total number of trips at 2 | E | D1 (two lanes), D4 |
| BR-10 | Only vehicles that are **available and switched on** are planned. `in_workshop` is locked off. The dispatcher may switch an available vehicle off with a reason (e.g. VEH038 "no driver"); the dataset is never modified | E, A | D1 Fleet tab |
| BR-11 | **Weekly fuel quota:** litres = (2 × `depot_to_district_km` + `inter_stop_km` × (n−1)) / `km_per_l`. A plan may not push a vehicle past `weekly_fuel_quota_l` minus litres already used that ISO week | E | D1 Fleet tab, D4 |
| BR-12 | **Mall outlets** (`mall_dock`): the stop is sequenced so that the plan arrival falls inside `mall_window` | E | D2 |

## B. Planning objective and explanations
| ID | Rule | Enforced | Screens |
|---|---|---|---|
| BR-13 | **Priority = expected loss if not delivered today.** It rises with chilled goods, `days_since_last_served`, `deferred_yesterday`, festival week (`festival_ramp`) and mall windows. Shown as a score (e.g. "Priority 78"). Weights live in config and are documented in [06](06-planning-engine.md) | E | D3 |
| BR-14 | The engine **maximises priority-weighted value served minus trip cost**. It reserves reefer space for chilled goods when reefers are the bottleneck | E | D1 |
| BR-15 | Every deferral has **one reason code**: `NO_REEFER_CAPACITY`, `NO_VAN_AVAILABLE`, `VOLUME_CAP`, `WEIGHT_CAP`, `FRESH_TIME_BUDGET`, `DAY_TIME_BUDGET`, `TRIP_LIMIT`, `FUEL_QUOTA`, `VEHICLE_UNAVAILABLE`, `LOWER_PRIORITY` | E | D3, S8 |
| BR-16 | Deferrals are grouped: **No space anywhere** (unavoidable: infeasible even at top priority) vs **Bumped by a higher priority** (our choice: shows which orders it would displace, plus a **Serve instead** action) | E, A | D3 |
| BR-17 | The plan header shows **orders served**, **chilled served**, **stops at risk**, and a **"Limit today"** strip naming the binding resource (e.g. "Reefer space 172/172 m³") with **Why?** | E, W | D1 |
| BR-18 | Every stop has **two clocks**: the plan time (BR-08 standard) and a **likely window** (realistic estimate; roads run about 1.7× slower than plan). A stop is **At risk** when the likely window ends after the delivery window closes | E | D1, R1, S1 |

## C. Dispatcher control and publishing
| ID | Rule | Enforced | Screens |
|---|---|---|---|
| BR-19 | **Edit trips:** drag an order onto a trip, and BR-01…BR-12 are checked **before the drop**. An infeasible change can't be saved. Edits are saved or discarded as a batch | A (via engine validate), W | D1 Edit |
| BR-20 | **Lock a trip** ("Keep on re-run"): a re-run must keep locked trips unchanged and optimise around them | E | D1 |
| BR-21 | **Repeat skips** (`deferred_yesterday = 1` or `days_since_last_served ≥ 3`) can't be bulk-confirmed. Each needs a written reason | A, W | D3 |
| BR-22 | **Publish gate:** any hard-rule break blocks publishing (the reason is shown). Likely-late stops are **warnings** the dispatcher accepts. All deferrals must be confirmed | A | D4 |
| BR-23 | Publishing creates an **immutable plan version** (v1). Any later change creates v(n+1), which affected loaders and drivers **must acknowledge** | A | D4, L5, R1 |

## D. Loading and shortfalls
| ID | Rule | Enforced | Screens |
|---|---|---|---|
| BR-24 | **Load order = reverse stop order** (the last drop is loaded first, by the doors) | A | L2, tablet top view |
| BR-25 | A dock sees only **its own trips, in departure order**, with the plan version in the header | A | L1 |
| BR-26 | **Shortfall report** = order + missing/damaged + quantity + reason (`short_from_chiller_pick`, `not_on_dock`, `damaged_in_pick`, `other`) + optional photo. It queues offline | A, W | L3 |
| BR-27 | Sending a shortfall **puts that vehicle's trip on hold**. The hold is **per vehicle**, not per dock. A held trip can't be released or departed | A | L4, D6 |
| BR-28 | The engine computes **up to 3 repair options** (minimal change), each with: what the outlet gets, delay, effect on other stops, and loss. The recommended one is pre-selected, **never auto-applied** | E, A | D6 |
| BR-29 | **Store split rule:** each outlet has a standing rule for split chilled deliveries (`same_morning_only` / `any` / `never`). Options that break it are labelled "Breaks <outlet>'s rule" | E, A | D6 |
| BR-30 | Applying a repair publishes v(n+1). **An operational top-up on another trip is allowed** (e.g. +2 cases on trip 2) and is tracked as a linked quantity, never in the Task 2B export | A | D6, L5 |
| BR-31 | **The loader acknowledging v(n+1) lifts the hold and releases the van.** The diff shows only what changed | A | L5 |

## E. Driver and offline
| ID | Rule | Enforced | Screens |
|---|---|---|---|
| BR-32 | The driver must **acknowledge the current plan version** before starting a trip | A | R1 |
| BR-33 | **Arrived** records the arrival event time | A | R2 |
| BR-34 | **Outcome** = Delivered / Partial / Failed + cases handed over + damaged/refused + receiver name + photo. **A known loading shortfall is pre-filled and locked**, never re-reported | A, W | R3 |
| BR-35 | Every driver and loader action is stored **on the device first** (outbox) with a client-generated `event_id` (UUID) and the device `event_time`. Uploads are retried until acknowledged | W, A | R3, R4 |
| BR-36 | **Sync is idempotent:** the same `event_id` is accepted once; duplicates return `duplicate` | A | R4, R5 |
| BR-37 | **Event time counts**, and upload time is shown beside it. A late sync never makes a delivery look late | A | R5, D5 |
| BR-38 | Drivers and loaders can **reopen their last session without signal** (cached token + cached plan) | W | X1 |
| BR-39 | Access notes come from the **outlet profile** (van only, street unload, mall window) and are labelled as such. A **same-day store note** appears at the top of the driver's stop | A | R2, S1 |

## F. Store manager
| ID | Rule | Enforced | Screens |
|---|---|---|---|
| BR-40 | **Orders close at 16:00** for next-day delivery. After the cutoff, an order goes to the next operating day (per `calendar.is_operating`) | A | S2, S1 |
| BR-41 | Chilled and dry are **separate orders** | A | S2 |
| BR-42 | **Order sanity check:** a line > 3× the outlet's usual quantity is questioned ("Did you mean 20?"). The manager can fix it or keep it | A, W | S2 |
| BR-43 | Arrival is shown as a **window** with its basis ("based on past runs"), **one line per order/van** | A | S1 |
| BR-44 | **Deferral notice:** what moved, the reason in plain words (from the reason code, labelled "Written from the plan"), the new time, and what still arrives. Available in **Sinhala, Tamil and English** (language set in the account). Says **"First in line (moved once)"**. The store acknowledges it | A | S8 |
| BR-45 | **A moved order is protected on the next run** (top priority) | E | S8, D3 |
| BR-46 | **Receipt confirmation is a separate event** from the driver's record. Lines default to the driver's counts; any change opens an issue | A | S5 |
| BR-47 | **Issues are reported per item line:** missing / damaged / wrong item / chilled-arrived-warm + count + optional photo. Good lines are still confirmed | A | S6 |

## G. Exceptions and resolution
| ID | Rule | Enforced | Screens |
|---|---|---|---|
| BR-48 | **Exceptions are ranked by business impact**, and each has a suggested fix (e.g. "Swap stops 2 and 3") | A | D5 |
| BR-49 | **Stores are told automatically** when a stop is predicted to miss its window. The dispatcher's job is the fix | A | D5, S1 |
| BR-50 | A vehicle silent on a **known dead-zone district** shows as **Pending sync**, not as an alarm | A | D5 |
| BR-51 | **Store report decision:** redeliver on the next run / credit / reject with a reason. Both sides are notified, and damaged stock appears in the next pick note | A | D10 |
| BR-52 | **Count conflict** (driver vs store): both records are kept, nothing is overwritten. Decision: driver's count stands / store's count stands (opens a short claim) / ask for a recount. An optional note goes to both | A | R7, D13 |
| BR-53 | **Stale-plan conflict:** an event referencing a plan version that changed that stop is stored **and** raises a conflict for dispatch | A | R7, D13 |

## H. Cross-cutting
| ID | Rule | Enforced |
|---|---|---|
| BR-54 | One status vocabulary everywhere: `planned`, `loaded`, `in_transit`, `delivered`, `at_risk`, `late`, `deferred`, `pending_sync`, `on_hold` | A |
| BR-55 | Role-scoped access: dispatcher → their depot · loader → their dock · driver → their vehicle · store → their outlet | A |
| BR-56 | All times are Asia/Colombo. All domain time comes from the `Clock` service (demo override) | A |
| BR-57 | Every decision (publish, defer, override, repair, resolution) is recorded with **who, when and why** | A |

---

## Demo-only data (not in the dataset; committed as our own fixtures)
The dataset has cases, kg and m³ per order, not items. We add **original** demo fields, never derived from the data:
- item lines with example names (milk, yoghurt, butter, chicken, fish);
- usual quantities per outlet;
- each store's split rule;
- staff names (Kasun F., Nimal P., N. Perera, S. Jayasinghe, M. Fernando);
- the same-day driver note;
- language preference.

These live in `services/api/app/seed/demo_extras.yaml`.

## Departures from the submitted design
Keep this list current. It goes into the README.
| # | Design said | Build does | Why |
|---|---|---|---|
| DEP-1 | "6 reefers in the workshop" (Problem framing, Fleet tab, video) | **5** (VEH001, 002, 004, 005 trucks + VEH035 van) | Data correctness |
| DEP-2 | Fleet counts, deferral set, priority scores, live-ops counts were illustrative | Real values computed by the engine on S1 | Design marked them as placeholders |
| DEP-3 | D1 Edit trips / Edit this trip are actionable | Visible, disabled pending the post-merge stretch | Core track takes precedence; approved by Dev 2 on 4 Oct |
| DEP-4 | D1 Orders tab can be opened | Visible, disabled until an Orders frame is supplied | No supplied Orders design; approved by Dev 2 on 4 Oct |
| DEP-5 | D4 and D6 show late probabilities (illustrative 62% and 9% → 31%) | Real likely-late count and arrival-window changes, without a probability | Current travel-ratio model predicts windows, not calibrated probabilities; approved by Dev 2 on 4 Oct |
| DEP-6 | Store notices sent in Sinhala, Tamil or English | English server template shared by preview and publication | Multilingual notification delivery remains a handover gap; approved by Dev 2 on 4 Oct |
| DEP-7 | D6 Call the dock connects to the loader | Visible, disabled until a dock phone number is configured | No dock contact number is supplied; approved by Dev 2 on 4 Oct |
| DEP-8 | D10 says damaged stock appears in tomorrow’s pick note | Says “The loading team receives the damaged-stock note”; creates loader notifications and records `pick_note`/`pick_date` in the decision event | Loading view integration belongs to the lead; accurate wording approved by Dev 2 on 4 Oct |
