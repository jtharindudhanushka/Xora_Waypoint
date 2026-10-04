# Dev 2 handover — second assignment, 4 October 2026

Tasks 2.6–2.9 are implemented on pushed feature branches. After the 20:30 feature freeze, only the fidelity task already in progress, generated-contract merge fixes, verification and this handover were completed. Submission target is 22:00 Sri Lanka time. The lead owns merging and deployment. The first assignment is recorded in [the original handover](dev2-handover.md); its PRs #11–16 have now merged.

## 1. PR list in merge order

| PR | Branch | Base | Summary | Dependency / CI |
|---|---|---|---|---|
| [#17](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/17) | feat/engine-cpsat | main | Bounded CP-SAT with greedy hints, shared validation, honest status and fallback; engine/API dependency | Independent; four CI jobs green |
| [#18](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/18) | feat/dispatch-live-ops | main | D5, ranked exceptions, pending sync and validated immutable stop swaps | Updated against merged sync/deployment; four CI jobs green |
| [#21](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/21) | feat/dispatch-issues | main | D10/D13, six decisions, next-run orders, short claims, notifications and scoped SSE | Stacked on #18; four CI jobs green |
| [#25](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/25) | feat/dispatch-fidelity | main | Eight-frame review, planning spacing/type corrections and refreshed comparisons; deterministic repair timer fixture | Stacked on #21; four CI jobs green |
| [#27](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/27) | docs/dev2-handover-2 | main | Status, disclosure and this report | Stacked on #25; merge last; see current PR checks |

All branches are retained; no PR was merged by Dev 2. Generated OpenAPI/client conflicts with the lead's merged #20 sync API were resolved by exporting the combined routers, preserving both tracks. Do not choose one side of a generated-file conflict: regenerate after integrating routes. #17 remains independent; the other feature branches intentionally contain preceding unmerged dispatcher work.

## 2. What works and how to walk through it

Follow [the seed/demo instructions](09-seed-and-demo.md), then:

1. Sign in as `dispatch.peliyagoda@waypoint.demo` / `demo1234`. Set the demo clock to Mon 16:05, open `/dispatch/plan`, generate for Tue 7 Apr, and inspect served/chilled KPIs, the bottleneck, pre-dawn/daytime trips and deferral explanations. With #17 installed, the engine attempts the bounded optimiser and labels its actual result.
2. Inspect Fleet, confirm deferrals and open **Review & publish**. Accept any real late-window warning and publish v1. The API enforces the hard gate and stores an immutable version. VEH036 must have two trips; OUT074 must be served.
3. For a loader shortfall plus active hold, open `/dispatch/shortfalls/<UUID>`, inspect A/B/C and explicitly apply a repair. Publication creates v2 and retains the hold for the lead's acknowledgement flow.
4. Set the clock to the operating day and open `/dispatch/ops`. It reads the latest published version and projected stop statuses. Review impact-ranked exceptions, dead-zone **Pending sync**, and stop chains. **Mark as seen** acknowledges a quiet item; a suggested stop swap is offered only if shared engine validation accepts it. Applying a swap publishes a new version without altering its predecessor.
5. After the lead's store flow creates a report, open its link from Live operations or `/dispatch/issues/<UUID>`. D10 shows the original counts, reported items/photos and driver evidence. Choose redelivery, credit or rejection; rejection requires a reason. Redelivery creates a next-operating-day order. Both store and driver receive a persisted notification and scoped `issue.resolved` SSE.
6. For a count conflict created by offline sync, open the same issue route. D13 keeps recorded and uploaded times distinct. Accept the driver count, accept the store count, or request a recount. Accepting the store count creates a short-claim issue for separate D10 review. Original events and receipt evidence remain unchanged.

The seeded S1 generate → confirm → publish → checker path was verified locally. API tests use synthetic SQLite fixtures. Browser checks exercised all eight dispatcher screens and their interactions using synthetic responses. The combined live four-role walkthrough on Azure/Postgres remains the lead's acceptance check; this report does not claim it has passed.

## 3. Partial or not done — exact stopping points

| Area | Exact stopping point |
|---|---|
| CP-SAT quality | Feasible improvement in chilled/reefer utilisation; the prototype's 79 served / 21 chilled result was not reached within the bounded production model. The eight-worker search varies between runs. |
| Live ETA risk | Stop statuses update from the lead's projections. Risk and swap forecasts use planned departures/travel ratios, rather than recalculating a vehicle's live departure delay. |
| Recount | Resolution, both notifications and next 09:00 deadline are recorded. Collecting the recount and enforcing its follow-up workflow are not implemented in the dispatcher track. |
| Credit | The issue/event records the commercial decision and affected case count. No external billing or refund integration exists. |
| Loading pick note | Loader notifications and the decision event's `pick_note` / `pick_date` are produced. The lead must connect them to the actual pick-note display. |
| Full field integration | Driver/store issue creation belongs to the lead. Their latest branches must be merged and the deployed walkthrough run. Store report payload shape was inspected for compatibility. |
| Stretch | Drag-and-drop editing and the Orders tab remain disabled under approved departures. No new stretch work started after freeze. |

## 4. S1 result

The latest CP-SAT S1 run recorded in #17 generated, confirmed and published through the API. The same local allocation was checked again during handover:

```text
FEASIBILITY: PASSED - every rule satisfied.
orders served: 72 / 85
chilled served: 17 / 26
reefer volume used: 134.632 / 172.4 m³
deferrals: 13
solve time: 11.604 seconds including setup and explanations
solver_status: FEASIBLE
```

The CP search budget is 10 seconds with eight workers; preparation and explanation add time. Observed bounded runs returned 72–73 served and 16–18 chilled, so do not present a fixed optimum. The prior greedy baseline was 72 served / 14 chilled. VEH036 splits and OUT074 is served. Allocation CSVs and all organiser data remain local and ignored.

## 5. API, OpenAPI and database

All new paths have the `/api/v1` prefix and require a depot-scoped dispatcher:

| Method | Path | Behavior |
|---|---|---|
| GET | /ops/{operating_date} | Published version, stop chains, KPIs and refreshed derived exceptions/notices |
| GET | /exceptions?status=open | Ranked depot-scoped exception list; also supports resolved |
| POST | /exceptions/{identifier}/apply-fix | Acknowledge pending sync or validate/apply the suggested stop swap |
| GET | /issues?status=open | Scoped issue list; also supports resolved |
| GET | /issues/{identifier} | Original evidence, item counts and decision context |
| POST | /issues/{identifier}/resolve | Store report: redeliver / credit / reject; count conflict: driver_stands / store_stands / recount |

Pydantic schemas were exported into `services/api/openapi.json` and regenerated into `apps/web/src/api/schema.d.ts`, including the merged sync routes. **No new migration.** Existing plan, issue, exception, notification, order and event tables are reused. Events remain append-only. The engine and API declare OR-Tools; the API image installs it through package dependencies.

Publication emits scoped `plan.published`; fixes emit `exception.updated`; issue decisions emit `issue.resolved`. Both issue parties also receive stored notifications. Loader damaged-stock notifications accompany the decision event. Operations GET refreshes derived exceptions/late notices as well as returning the view.

## 6. Figma fidelity and departures

[Eight-frame checklist and comparisons](qa/dev2-fidelity.md) covers D1/D3/Fleet/D4/D6/D5/D10/D13. The pass corrected trip bar placement and selected border, legend order, panel line heights, capacity track, Deferred checkbox/notice geometry, Fleet text/meter tokens, and Publish icon gaps. Comparisons use 1440 × 900 synthetic browser fixtures.

Approved DEP-3–8 remain in [the departure register](02-business-rules.md#departures-from-the-submitted-design): disabled editing and Orders controls; real windows/counts instead of unsupported probabilities; English-only notices; disabled dock call without a number; accurate loading-team notification wording until pick-note integration. Live quantities and identifiers differ from illustrative Figma values. No additional design departure was introduced.

## 7. Known risks and the next three lead actions

The pending-sync threshold is 15 minutes in dead-zone districts. Live risk uses the published forecast. The SSE broker is in-process and assumes one API instance. SQLite synthetic tests do not verify Postgres concurrency/triggers or real field clients. OR-Tools is a new image dependency; CI image builds verify installation. Resolve generated-contract conflicts by regeneration. A flaky exact-second repair assertion was fixed by injecting the same frozen Clock into its HTTP and direct-service paths.

1. **Merge #17 → #18 → #21 → #25 → this handover**, retaining branches. Incorporate the lead's store/UI/e2e work and regenerate the combined contract. Check CI on the final main commit rather than treating cancelled earlier merge runs as a failure.
2. **Run the deployed four-role walkthrough**: generate/publish, loader hold/repair/acknowledgement, driver sync and revision, D5, store report D10, offline count conflict D13, and store/driver decision notifications. Connect `pick_note` / `pick_date` to the loading view and confirm stale-version handling after stop swaps.
3. **Redeploy and submit by 22:00**. Use the smoke tests, confirm the public login and S1 feasibility, and show the real solver status and remaining departures in the demo. Prioritize submission over further optimiser tuning or editing.

## 8. Exact local verification commands

Run from the root in PowerShell with Python 3.12 and Node 22. After merging #17, install the engine/API together so the optimiser and image dependencies agree:

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
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
Pop-Location
.venv/Scripts/python.exe services/api/scripts/verify_s1.py
.venv/Scripts/python.exe datasets/check_allocation.py datasets/s1_allocation.csv
# The generated CSV stays in ignored datasets/.
git diff --check
```

For the live stack, preserve the existing `.env`, or copy `.env.example` on first setup, then run `docker compose up --build`. Open `http://localhost:8080` and `/api/docs`. See [deployment instructions](11-deployment.md) for the lead's Azure deployment. Docker is unavailable on the Dev 2 machine; image builds run in CI.

For synthetic planning/repair browser verification, run `npm --prefix apps/web run dev -- --host 127.0.0.1` in one terminal. In another, from root:

```powershell
npm install --prefix .venv/browser-qa playwright
$env:PLAYWRIGHT_MODULE = "$PWD/.venv/browser-qa/node_modules/playwright"
node apps/web/scripts/verify-planning.cjs
node apps/web/scripts/verify-repair.cjs
# D5/D10/D13 API regressions are also included in the full pytest run:
Push-Location services/api
../../.venv/Scripts/python.exe -m pytest tests/test_ops.py tests/test_issues.py
Pop-Location
```

Verification counts: #17 has 71 engine tests. Dispatcher issues adds eight API regressions and Live operations adds four; the combined sync/dispatcher API run has 56 tests. Web has 10 tests. All eight browser captures completed without page errors; typecheck/lint/format/build passed. Consult each PR for its final CI run after the integration updates.
