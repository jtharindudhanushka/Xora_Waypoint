# Dev 2 handover · 4 Oct 2026

Tasks 2.1–2.5 are implemented and pushed. The lead merges the PRs below in order,
using merge commits and keeping every branch. This handover was prepared before
the 19:00 feature freeze. The post-merge stretch has not started.

## 1. PRs and merge order

| PR | Branch | PR base | Dependency | Summary | CI |
|---|---|---|---|---|---|
| [#11](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/11) | feat/engine-rules | main | none | Pure models, shared BR-01–12 and worked timing tests | Green; merged |
| [#12](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/12) | feat/engine-greedy | main | #11 | Greedy, windows, deferrals, KPIs and Task 2B export | Green; open |
| [#13](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/13) | feat/planning-api | main | #12 | M1 generate → confirm → publish, fleet, scoped SSE | Green; open |
| [#14](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/14) | feat/dispatch-plan-ui | main | #13 | D1 tabs/dialog, locks and serve-instead | Green; open |
| [#15](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/15) | feat/dispatch-shortfall | main | #14 | A/B/C repair, linked quantities, v2 and D6 | Green; open |
| [#16](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/16) | docs/dev2-handover | main | #15 | Work status, disclosure and this report | Implementation checks green; see PR for latest documentation run |

All PRs target main as requested; each dependent branch contains its predecessor's
unmerged work. GitHub removes that inherited diff as the earlier PRs land. No
branches were deleted or merged by the author. No dataset, CSV, PDF or model
artifact is tracked in these changes. Attribution is confined to the disclosure doc.

## 2. What works end to end

Follow [docs/09](09-seed-and-demo.md), with these concrete dispatcher steps:

1. Start the seeded stack; sign in as `dispatch.peliyagoda@waypoint.demo` /
   `demo1234`. Open `/dispatch/plan` (defaults to 7 Apr; `?date=YYYY-MM-DD` selects
   another day). Jump the header clock to **Mon 16:05**.
2. Click **Generate plan**. Review served/chilled/risk KPIs and **Limit today** →
   **Why?**. Inspect pre-dawn/daytime lanes, VEH036's two trips and OUT074's stop.
   Select a trip to inspect quantities, windows, budget and rule explanations.
3. Open **Fleet**: VEH038 is off with its reason; workshop vehicles cannot be
   switched on. Available vehicles can be switched, then **Re-run** the draft.
4. Open **Deferred**. Read the groups and reasons; repeat deferrals require a
   written reason. Confirm the selected deferrals. **Serve instead** previews
   displaced orders and asks for an explicit application; **Keep on re-run**
   preserves a trip while generating another draft.
5. Click **Review & publish**. The API gate checks hard rules and deferral
   confirmations. Review real late-window warnings and click **Publish plan v1**.
   The API creates English notices, audit events and scoped `plan.published` SSE.
6. Once the lead's loader/sync track creates a `Shortfall` plus active `Hold`, jump
   to **Tue 04:15** or set the demo clock to the report's operating day. Open
   `/dispatch/shortfalls/<shortfall UUID>`. D6 shows the report, hold timers,
   standing rule and up to three feasible repairs, with the recommendation selected.
7. Choose A/B/C and click **Apply … · publish v2**. The UI returns to the current
   published plan. v1 is unchanged. A splits the linked operational quantities;
   B delays/reforecasts; C creates the outstanding quantity on the next operating
   date. Every active hold follows its new trip and remains active.
8. The lead's loader acknowledgement must release the hold; the driver must
   acknowledge the current version before departure. These field actions belong
   to the lead's track and were not implemented or claimed as click-through here.

The allocation path was tested against real seeded S1 through the API. The S1
repair path was also tested locally by creating the report/hold through the shared
models, fetching A/B/C and applying A. Browser interaction tests use synthetic
responses; they do not claim a full four-role production walkthrough.

## 3. Partial or not started

| Area | Exact stopping point |
|---|---|
| CP-SAT and drag/drop trip editing | Not started; 2.1–2.5 have not all merged. The engine reports GREEDY honestly. D1 editing controls are disabled. |
| Orders tab | Disabled; no supplied frame defines it. |
| Sinhala/Tamil notices | Server template and preview are English; multilingual delivery remains open. |
| Dock calling | D6 button is disabled until a contact number is configured. |
| Late-risk probability | No calibrated probability exists. Real likely-window/count changes are displayed. |
| Loader/sync/driver/store integration | Their routes/screens remain the lead's responsibility. D6 has its specified direct route; linking a hold from D5 and releasing it from L5 must be wired by that track. |
| Full Docker/Postgres walkthrough | Docker is unavailable on this machine. CI builds the images; local behavior tests use SQLite. The lead must run migrations and the live stack on a Docker machine. |

## 4. S1 results

The final reproducible allocation check returned:

```text
FEASIBILITY: PASSED - every rule satisfied.
orders served: 72 / 85
chilled served: 14
deferrals: 13
stops at risk: 23
solve time: 901 ms (local run; varies by machine)
```

VEH036 has two trips rather than the infeasible combined 1,096 / 1,040 kg load;
OUT074 is served. No allocation CSV is committed. The actual S1 plan departs
VEH036 T1 at 03:30, whereas Figma's illustrative hold starts before a 04:40
departure. At the story's 04:19 report time, A reschedules the held vehicle and
its later top-up within all hard budgets; all A/B/C options were returned, A was
recommended, C flagged OUT003's standing rule, and applying A published v2.

## 5. Endpoints, contract and DB

All paths below start with `/api/v1`; existing auth, Clock, DB and errors are reused.

| Method | Path | Purpose |
|---|---|---|
| POST | /plans/{operating_date}/generate | New draft from the shared engine |
| GET | /plans/{operating_date} | Current plan with trips, windows, deferrals and KPIs |
| GET | /fleet?date=YYYY-MM-DD | Scoped fleet/day status and fuel budget |
| PATCH | /fleet/{vehicle}/{operating_date} | Switch an available vehicle on/off |
| POST | /plan-versions/{version_id}/deferrals/confirm | Record confirmed deferrals/repeat reasons |
| GET | /plan-versions/{version_id}/publish-check | Hard gate and likely-late warnings |
| POST | /plan-versions/{version_id}/publish | Publish with explicit late-risk acceptance |
| POST | /deferrals/{deferral_id}/serve-instead | Counterfactual preview or confirmed draft |
| POST | /trips/{trip_id}/lock | Preserve a draft trip on re-run |
| DELETE | /trips/{trip_id}/lock | Remove that draft lock |
| GET | /shortfalls/{shortfall_id}/options | Version-bound repair quotes and D6 data |
| POST | /shortfalls/{shortfall_id}/apply | Human-selected repair publishes v(n+1) |

Pydantic schemas were exported to `services/api/openapi.json` and the generated
web `schema.d.ts`. Added plan totals, rule/protection messages, deferral notice
preview, serve-instead response, repair report/options and nullable
`top_up_of_order_ref`. The API wheel/Docker image bundles the same engine source.
**No new DB migration**: all writes use the existing plan, loading, order,
notification, hold and event models. Events are appended, never updated/deleted.
Repair snapshots are validated again under scoped locks before publication.

For field integration: active `Hold.trip_id` points at the new v2 trip while
`Shortfall.trip_id` retains the original report provenance. Unresolved holds
remain repairable against their current trip. A's top-up has
`StopOrder.top_up_of_order_id`; C's new order id and original order id are linked
in the append-only `repair.applied` payload. Publishing does not acknowledge a
version or release a hold.

## 6. Figma departures and verification

Approved DEP-3–7 are listed in [business rules](02-business-rules.md#departures-from-the-submitted-design).
They cover disabled Edit/Orders, real windows instead of probability, English
notices, and the missing dock number. DEP-1/2 preserve real dataset values rather
than illustrative design counts. No further design departure was introduced.

Side-by-side evidence uses the original Figma reference and **original synthetic
app fixtures**, at 1440 × 900:

- [D1, Deferred, Fleet and Publish](qa/dev2-planning/README.md)
- [D6](qa/dev2-repair/README.md)

Shared app-bar type and nav spacing were corrected during D6 and all four D1
comparisons refreshed. The actual product uses server values and exported icons,
existing tokens and primitives.

## 7. Known limitations, risks and next three lead actions

The greedy plan is feasible, not globally optimal. Deferral choice witnesses are
actual forced greedy plans; the solver does not claim CP-SAT infeasibility proofs.
Fallback travel ratios are used where no learned district/hour ratio exists.
The SSE broker is in-process and assumes one API instance. Real Postgres triggers
and concurrent transactions still need the deployed smoke test. C creates an
order-level quantity obligation; the lead's item-level pick view must handle it
without inventing which item was missing. Deployment status is outside Dev 2's track.

1. **Merge #12 → #13 → #14 → #15 → the handover PR**, retaining merge commits and
   branches, then run `docker compose up --build` and the dispatcher walkthrough.
2. **Connect loader report/hold, D6 link, acknowledgement and driver revision.**
   Follow the hold/top-up linkage above; verify the hold is released only by L5
   acknowledgement, and carry the known shortage into R3 without double reporting.
3. **Run the combined four-role smoke test and deploy**, then record actual
   remaining gaps/departures in the submission README and video. Do not start
   stretch after 19:00. Prioritize submission over adding CP-SAT or editing.

## 8. Exact local commands

Run from the repository root in PowerShell (Python 3.12, Node 22). The organiser
pack must stay in ignored `datasets/` with the layout in docs/09.

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -e "packages/engine[dev]" -e "services/api[dev]"

Push-Location packages/engine
../../.venv/Scripts/python.exe -m ruff check .
../../.venv/Scripts/python.exe -m ruff format --check .
../../.venv/Scripts/python.exe -m mypy --strict src
../../.venv/Scripts/python.exe -m pytest
Pop-Location

Push-Location services/api
../../.venv/Scripts/python.exe -m ruff check .
../../.venv/Scripts/python.exe -m ruff format --check .
../../.venv/Scripts/python.exe -m mypy app
../../.venv/Scripts/python.exe -m pytest
Pop-Location

.venv/Scripts/python.exe services/api/scripts/export_openapi.py
Push-Location apps/web
npm ci
npm run gen:api
npm exec prettier -- --write src/api/schema.d.ts
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
Pop-Location

.venv/Scripts/python.exe services/api/scripts/verify_s1.py
# Outputs datasets/s1_allocation.csv and invokes the organisers' checker.
# To rerun the checker alone:
.venv/Scripts/python.exe datasets/check_allocation.py datasets/s1_allocation.csv

Copy-Item .env.example .env  # First setup only; preserve existing configuration.
docker compose up --build
# Open http://localhost:8080; API docs: http://localhost:8080/api/docs
```

Synthetic browser checks (in a separate terminal from the running Vite server):

```powershell
# Terminal 1, from root:
Push-Location apps/web
npm run dev -- --host 127.0.0.1

# Terminal 2, from root, using Edge on Windows:
npm install --prefix .venv/browser-qa playwright
$env:PLAYWRIGHT_MODULE = "$PWD/.venv/browser-qa/node_modules/playwright"
node apps/web/scripts/verify-planning.cjs
node apps/web/scripts/verify-repair.cjs
# Captures are ignored .venv/ui-*.png. No live dataset is needed.
```

Latest local checks: **65 engine tests, 33 API tests, 10 web tests**, all applicable
lint/format/types checks and the production web build passed. Browser checks
captured all five states without page errors. API tests use synthetic fixtures only.
