# 09 · Seed data and demo

## Data sources
| Source | Committed? | Loaded into |
|---|---|---|
| **Organisers' dataset pack** in `./datasets/` (or `DATASET_DIR`) | ❌ **Never** (public repo; T&C forbid publishing data or derivatives) | All reference tables, S1 orders (`task2b_peak_day_scenarios.csv`), S1 fleet status, travel ratios (computed from `route_legs_train.csv`) |
| **Our demo extras**, `services/api/app/seed/demo_extras.yaml` | ✅ Original content | Users, outlet profiles (split rule, language), products + item lines, usual quantities, staff names, the driver note text |

### Expected dataset layout (checked before seeding)
```
datasets/
  check_allocation.py
  data/General Data/{outlets,vehicles,calendar,district_travel,service_allowance,traffic_speed,road_conditions}.csv
  data/Test Data/{task2b_peak_day_scenarios,task2b_peak_day_fleet}.csv
  data/Training Data/route_legs_train.csv          (for travel ratios; optional, with a 1.5× fallback)
```
If a required file is missing, the seed exits with code 2 and prints the exact missing paths and a pointer to the README.

## Seed process (`python -m app.seed`, run by the `api` container on start)
1. `alembic upgrade head`.
2. Validate the dataset layout and columns (pydantic models per CSV).
3. Upsert reference data (idempotent, keyed on natural IDs).
4. Load scenario S1 → operating date **2026-04-07**, depot Peliyagoda:
   - 85 orders, with the dataset fields `deferred_yesterday` and `days_since_last_served`;
   - `vehicle_days` from the S1 fleet file;
   - **VEH038 switched off with "No driver"** (an operational override, BR-10).
5. Demo extras:
   - users;
   - outlet profiles: **OUT003 split rule = `same_morning_only`**; OUT054 language `si`;
   - item lines for the story orders (S1-000, S1-001, S1-005, S1-083), summing exactly to the dataset units;
   - usual quantities for OUT001.
6. **S1-001 (OUT001 chilled, 80 cases) is seeded as a `draft`.** The judge submits it in S2 (walkthrough step 1). Before planning, if the clock passes 16:00 and it is still a draft, the cutoff job places it, so the plan is always complete.
7. Set the demo clock to **2026-04-06 14:50 +05:30**.

Re-running the seed is safe. Reference data is merged on every start. **The demo day is inserted only on the first run, so a container restart never wipes a judge's progress.** To start the demo over: `docker compose exec api python -m app.seed --reset-demo` (or set `SEED_RESET_DEMO=true` for one start).

## Demo clock (BR-56)
- `clock_settings.demo_now` overrides `now()` everywhere on the server. When it's null, the real time is used.
- The dispatcher header has quick jumps: **Mon 14:50 · Mon 16:05 (after cutoff) · Tue 04:15 (dock) · Tue 05:30 (deliveries) · Tue 07:45 (sync)**, plus "+15 min".
- Advancing past 16:00 runs the cutoff job.

## Accounts
| Role | Email | Password | Scope |
|---|---|---|---|
| Dispatcher | `dispatch.peliyagoda@waypoint.demo` | `demo1234` | depot Peliyagoda |
| Loader | `loader.dock2@waypoint.demo` | `demo1234` | Peliyagoda Dock 2 |
| Driver (VEH036) | `driver.veh036@waypoint.demo` | `demo1234` | VEH036 |
| Driver (VEH007) | `driver.veh007@waypoint.demo` | `demo1234` | VEH007 (offline story) |
| Store manager | `store.out001@waypoint.demo` | `demo1234` | OUT001 |
| Store manager | `store.out074@waypoint.demo` | `demo1234` | OUT074 (count conflict) |
| Store manager | `store.out002@waypoint.demo` | `demo1234` | OUT002 (deferral notice; deferred on the live S1 plan) |
| Store manager | `store.out054@waypoint.demo` | `demo1234` | OUT054 (served on the live S1 plan, VEH006 T1: no notice) |

The brief asks for 4 accounts (one per role); the first four are those. The extra three make the offline and deferral stories easy to show.

## Judge walkthrough
_Draft. Each step is ticked when its screens are built and verified by the e2e test `e2e/walkthrough.spec.ts`._

| # | Clock | Who | Do | Expect |
|---|---|---|---|---|
| 1 | Mon 14:50 | Store OUT001 | Log in → **New order** → chilled → yoghurt shows 60 → "3× your usual" → **Use 20** → Review → Submit | Order S1-001 placed; cutoff countdown shown |
| 2 | → 16:05 | Dispatcher | Log in → advance the clock → **Generate plan** | Plan in seconds: served / chilled / at-risk numbers; **Limit today** (live runs: reefer trip slots); VEH036 has 2 trips (live: T1 ≈ 767 kg, T2 ≈ 714 kg; read the plan); OUT074 on VEH007 |
| 3 | 16:10 | Dispatcher | **Fleet** tab: VEH038 is off ("No driver"); workshop reefers locked off | BR-10 |
| 4 | 16:12 | Dispatcher | **Deferred** tab: groups, reasons, priorities; confirm (repeat skips need a reason) → **Review & publish** → gate → **Publish v1** | v1 published; stores notified |
| 5 | 16:25 | Store OUT002 | Log in → notice | S8: S1-003 deferred, why and the next run (English template; DEP-6). Corrected from OUT054, which the live plan serves |
| 6 | Tue 04:18 | Loader | Find **S1-005 / OUT003 / 42 cases** in the published plan; use its actual vehicle/trip. On the VM's confirmed greedy run this is **VEH036 T1**, stop 2 after OUT001. Load in reverse order → **Report a problem**: missing 2, short from chiller pick | Actual source trip **on hold** (L4) |
| 7 | 04:19 | Dispatcher | Open that hold → **D6**; inspect OUT003's same-morning split rule. On the greedy T1 run choose **A** (40 now, 2 on later T2); C is flagged. If CP-SAT puts the order on T2 and no later compatible trip exists, A is absent: choose recommended **B**, re-pick all 42 | Human selection publishes v2; no impossible backward top-up |
| 8 | 04:27 | Loader | **Review v2**. Greedy/A: T1 OUT003 42 → 40; T2 OUT002 38 unchanged plus linked OUT003 +2. CP-SAT/B: source OUT003 stays 42; departure/arrival times shift for re-pick, no top-up. **Acknowledge the new v2 trip ID** | Hold transfers to v2 and releases only on its acknowledgement |
| 9 | 04:36 | Driver VEH036 | **Acknowledge v2**, follow its actual stop order → **Arrived** → outcome. Greedy/A: T1 stop 1 OUT001 80, stop 2 OUT003 40 with 2 already reported short. CP-SAT/B: OUT003 42, no remaining loading shortage warning | Two clocks per stop; linked top-up has no duplicate shortfall |
| 10 | 05:40 | Store OUT001 | **Confirm receipt** → change yoghurt and fish → **Report a problem** (2 damaged, 1 missing) | Issue sent to dispatch |
| 11 | 06:14 | Dispatcher | **Live ops** → exceptions by impact → open the store report → **Redeliver** | D10 decision recorded |
| 12 | 06:52 | Driver VEH007 | (Browser offline) record OUT074: 205 cases → **Saved on this phone** | R4 |
| 13 | 07:10 / 07:48 | Store OUT074, then the driver | Store confirms 200 · driver goes online → syncs | R5 uploaded → **R7 needs review** |
| 14 | 07:52 | Dispatcher | **D13**: both counts and evidence → decide | Conflict resolved, both records kept |
