# 12 · Work breakdown — Hackathon day (Sun 4 Oct 2026), two developers

**Hard deadline 23:59 · internal submit 21:00 · feature freeze 19:00.** All times are Sri Lanka time. Both developers work with AI agents (see [14-ai-handoff.md](14-ai-handoff.md)).

## Team
| Person | Owns | Why this split |
|---|---|---|
| **Lead** (Tharindu) | ✅ WP-0 Foundation (done) → **Field apps**: driver + loader with offline sync → **Store** screens → deployment → README walkthrough, video, submission | The lead built the backend foundation and seed, so they know the models, clock and broker that the field apps need |
| **Dev 2** | **Engine** (WP-1) → **Dispatcher planning API + UI** (WP-2) → **Shortfall repair, D6** | The planning engine is the critical path (20% of the score) and the hero screen (D1). It's self-contained, so it can start immediately |

## Integration contract between the two tracks
The **published plan version** is the hand-off point:
- **Dev 2 writes** `plans` → `plan_versions` (status `published`) → `trips` → `stops` → `stop_orders` + `deferrals` (tables already exist; see [04](04-data-model.md)).
- **Lead reads** published versions for the loader, driver and store screens, and writes `events`, `holds` and `shortfalls`.
- **Milestone M1 (target 16:45): Dev 2 opens a mergeable "generate + publish" PR; the lead merges it with the greedy planner.** Before M1, the lead builds the screens against a published version created by a small dev helper (`python -m app.dev.fake_plan`, built by the lead and clearly marked dev-only), then switches to the real planner at M1.

## Task list — Dev 2 (in order)
| # | Task | Branch | Done when | Target | Status |
|---|---|---|---|---|---|
| 2.1 | **Engine core:** `packages/engine` (pyproject, `src/xora_engine`), dataclass models, **rules BR-01 to BR-12** as pure predicates, `trip_minutes()` (BR-08), `validate()`; unit tests incl. the worked examples (101 / 112 / 64 min) | `feat/engine-rules` | Tests green; `mypy --strict` clean | 15:45 | **Done** · #11 merged |
| 2.2 | **Greedy planner + explanations:** `plan()` = prune → priority (BR-13) → greedy first-fit by (brand, district) → sequence stops → plan times → likely window (travel ratios) → deferral reason codes (BR-15), unavoidable vs choice (BR-16), bottleneck + KPIs (BR-17). Export to Task 2B CSV, then run `datasets/check_allocation.py` → **PASSED** on S1 | `feat/engine-greedy` | S1 passes validate + the organisers' checker; VEH036 splits (1,096 > 1,040 kg); OUT074 served | 16:30 | **Done** · #12 ready |
| 2.3 | **Planning API:** adapter (DB rows ↔ engine), `POST /plans/{date}/generate`, `GET /plans/{date}`, `GET /fleet`, `PATCH /fleet/...`, `POST .../deferrals/confirm` (BR-21), `GET .../publish-check`, `POST .../publish` (BR-22, BR-23; SSE `plan.published`); export OpenAPI + regenerate the client | `feat/planning-api` | **M1:** generate + publish works on the seeded S1 | 16:45 | **Done** · #13 ready (M1) |
| 2.4 | **D1 Plan workspace UI** (Figma `196:383`): KPI header, "Limit today" strip + Why?, pre-dawn and daytime timelines, trip panel (D2) · **Deferred tab** (`197:440`) · **Fleet tab** (`198:274`) · **Publish dialog** (`197:682`) | `feat/dispatch-plan-ui` | Matches Figma; walkthrough steps 2–4 | 18:15 | **Done** · #14 ready; approved departures |
| 2.5 | **Shortfall repair + D6** (`156:283`): `repair()` options A/B/C with the store split rule (BR-28, BR-29), `GET /shortfalls/{id}/options`, `POST /apply` → v2 | `feat/dispatch-shortfall` | Walkthrough step 7 | 19:00 | **Done** · #15 ready |
| stretch | CP-SAT optimiser behind `plan()` · Edit trips with drag and drop (`205:342`, BR-19/20) | `feat/engine-cpsat`, `feat/dispatch-edit` | | after 2.5 | **Not started** · core PRs await lead merge |

## Task list — Lead (in order)
| # | Task | Branch | Done when | Target |
|---|---|---|---|---|
| 1.1 | **Run `docker compose up`** on a Docker machine, fix anything; **deploy early** to Azure (docs/11) so the URL exists | `fix/compose-*`, `chore/deploy` | Signed in on the public URL | 15:45 |
| 1.2 | Dev helper `fake_plan` (dev-only) + **sync API** (`/sync`, `/sync/bootstrap`, idempotent, conflicts) + `GET /vehicles/{code}/today` | `feat/sync-api` | Duplicate batch → `duplicate`; tests | 16:30 |
| 1.3 | **Driver UI** R1, R2, R3, R4, R5, R7 with the Dexie outbox and sync banner | `feat/driver-ui` | Walkthrough 9, 12, 13 (offline) | 17:30 |
| 1.4 | **Loader UI + API** L1, L2, L3 (→ hold), L4, L5 (ack releases the hold) | `feat/dock-ui` | Walkthrough 6, 8 | 18:15 |
| 1.5 | **Store** S1, S2 (cutoff + 3× check), S8 notice, S5 + S6 receipt and issues | `feat/store-ui` | Walkthrough 1, 5, 10 | 19:00 |
| 1.6 | Redeploy · README walkthrough + departures · AI disclosure · **video 5–8 min** · submit the form | `docs/submission` | Form submitted | 21:00 |

**Updated assignment:** D5, D10 and D13 are assigned to Dev 2 in the second track below. The lead owns the combined live walkthrough and deployment.

## Dev 2 — second assignment / final status (4 October)

The revised feature freeze is **20:30 Sri Lanka time**, submission **22:00**. After freeze, finish only work already in progress plus verification, merge fixes and handover. Original tasks 2.1–2.5 and their first handover are merged (#11–16); the earlier table records their original delivery checkpoints.

| Task | Branch | Status | PR / exact remaining work |
|---|---|---|---|
| 2.6 CP-SAT | feat/engine-cpsat | **Done** | #17 pushed; 71 engine tests; S1 checker passes. 72 served / 17 chilled in the latest recorded run; prototype 79/21 not reached. Lead merges. |
| 2.7 Live operations / D5 | feat/dispatch-live-ops | **Done with limitation** | #18 pushed; ranked exceptions, pending sync, validated stop swaps and immutable publication. Live departure-delay forecasting remains a gap. Lead verifies field projections. |
| 2.8 Store report / offline reconciliation | feat/dispatch-issues | **Done with integration gaps** | #21 pushed, stacked on #18; D10/D13, six resolutions, original evidence, notifications/SSE. Loading pick-note display, recount follow-up and external credit processing remain unconnected. |
| 2.9 Eight-screen fidelity pass | feat/dispatch-fidelity | **Done** | #25 pushed, stacked on #21; comparisons/checklist in docs/qa/dev2-fidelity.md. Existing approved departures retained. |
| Second handover | docs/dev2-handover-2 | **Done** | Separate PR targeting main, stacked on #25; eight-section report in docs/dev2-handover-2.md. |
| Drag-and-drop trip editing | feat/dispatch-edit | **Not started** | No new stretch work after freeze. |

The lead's merged sync/deployment contracts were integrated into #18/#21/#25 by regeneration. Lead field endpoints and driver/dock/store feature code were not modified by Dev 2. See [the second handover](dev2-handover-2.md) for merge order, checks, S1 metrics and verification commands.

## Timeline
| Time | Lead | Dev 2 |
|---|---|---|
| 15:00 | Docker check + deploy | Engine core (2.1) |
| 16:00 | Sync API + fake plan | Greedy + explanations (2.2) |
| **16:45** | ← switch to the real planner | **M1: generate + publish merged** |
| 17:00–19:00 | Driver → Loader → Store | D1 workspace → D6 repair |
| **19:00** | **Feature freeze**: fixes only | **Feature freeze** |
| 19:00–20:00 | Redeploy, README, final checks | Fidelity pass on dispatcher screens; help with fixes |
| 20:00–20:45 | Record the video (both) | Record the video (both) |
| **21:00** | **Submit** | |

## Cut list if behind (in this order)
1. D5 / D10 / D13 (unassigned already).
2. Tablet layouts for the loader (phone is what's judged).
3. Repair option B (keep A and C), then D6 entirely (shortfall shows "on hold" only).
4. si/ta translations (keep English plus the language switch).
5. CP-SAT (greedy is rule-valid and labelled honestly).

**Never cut:** rule validity, deferral reasons, the publish gate, offline outbox + idempotent sync, `docker compose up` + seed, the README walkthrough.
