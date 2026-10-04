# Xora · Waypoint — explainable delivery planning

> Tech-Triathlon 2026 (Rootcode) · Hackathon submission · Team **Xora**

Waypoint Group runs three retail brands (Fresh, Style, Tech) with 120 outlets, 60 vehicles and two depots. On most days the fleet can't serve every order. **Xora** connects ordering, planning, loading, delivery and receipt across four roles. It plans inside every hard rule, explains every deferral, and keeps working when the signal drops.

| Role | Device | Lands on |
|---|---|---|
| Dispatcher | Desktop | Plan workspace: one-click plan, deferrals with reasons, publish gate, shortfall repair, live exceptions |
| Loader | Phone (dock) | Trips in departure order, load in reverse stop order, report shortfalls, acknowledge revisions |
| Driver | Phone, offline-first | Acknowledge the plan, record outcome and proof offline, sync later |
| Store manager | Phone | Order before the 16:00 cutoff, honest arrival windows, confirm receipt, report issues |

> Teammates and AI agents: start with [`AGENTS.md`](AGENTS.md), then [`docs/`](docs/README.md).

## Live deployment
**https://xora-waypoint.southeastasia.cloudapp.azure.com** (Azure VM, Docker Compose + Caddy HTTPS; API docs at [`/api/docs`](https://xora-waypoint.southeastasia.cloudapp.azure.com/api/docs)). Seeded from the organisers' dataset pack and kept live through review and the finals.

## Accounts (password `demo1234` for every account)
| Role | Email | Scope / story |
|---|---|---|
| **Dispatcher** | `dispatch.peliyagoda@waypoint.demo` | Peliyagoda DC |
| **Loader** | `loader.dock2@waypoint.demo` | Peliyagoda Dock 2 |
| **Driver** | `driver.veh036@waypoint.demo` | VEH036 (shortfall → repair story) |
| **Store manager** | `store.out001@waypoint.demo` | OUT001 (order + receipt) |
| Driver | `driver.veh007@waypoint.demo` | VEH007 (offline + count conflict) |
| Store manager | `store.out074@waypoint.demo` | OUT074 (count conflict) |
| Store manager | `store.out054@waypoint.demo` | OUT054 (deferral notice) |

The first four are the one-account-per-role set the brief asks for. The other three make the offline and deferral stories easy to show.

## Run it locally
**Prerequisites:** Docker 24+ with Compose v2, and the organisers' **Tech-Triathlon 2026 dataset pack**.

1. **Add the dataset pack.** The competition data is confidential and is **never committed** to this public repo. Copy the pack into `./datasets/`:
   ```
   datasets/
     check_allocation.py
     data/General Data/…   data/Test Data/…   data/Training Data/…
   ```
2. **Configure and run** (database → migrations → seed → API → web):
   ```bash
   cp .env.example .env
   docker compose up --build
   ```
3. Open **http://localhost:8080**. Verified on a fresh clone on 4 Oct 2026: the stack starts with seed data (85 orders, 7 accounts).

**Configuration** ([`.env.example`](.env.example)): `POSTGRES_PASSWORD`, `JWT_SECRET`, `DATASET_DIR` (host path of the pack), `DEMO_START` (demo clock start, default Mon 6 Apr 2026 14:50 Colombo), `SEED_RESET_DEMO`, `CORS_ORIGINS`, and `PUBLIC_HOST` (production only). Production adds Caddy for HTTPS: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` ([docs/11](docs/11-deployment.md)).

**Reset the demo** to a clean seed: `docker compose exec api python -m app.seed --reset-demo`.

## Demo clock (BR-56)
The whole system runs on one server clock. The **dispatcher header clock is a menu**: click the time (top right) and pick **Mon 14:50 · Mon 16:05 · Tue 04:15 · Tue 05:30 · Tue 07:45**. Store, loader and driver phones follow the server clock, so recorded event times match the demo day.

## Judge walkthrough
Scenario S1: orders for **Tue 7 Apr 2026**, Peliyagoda DC. Use a phone-sized window (390 px) for store, loader and driver; desktop for the dispatcher. Sign out between roles (dispatcher: name button, top right; driver: **Me** tab; store: **Account** tab).

> **The plan is computed live, so trip assignments can vary between runs.** On the 1-vCPU demo VM the optimiser usually returns the greedy plan: **72/85 orders served, 14/26 chilled, limit: reefer space, 13 deferrals**, with VEH036 T1 = OUT001 (S1-001, 80 cases) → OUT003 (S1-005, 42 cases) and VEH007 T2 = OUT074 (S1-083, 205 cases). If a run differs, follow the order refs (S1-001, S1-005, S1-083), not the trip numbers.

| # | Clock | Who | Do | Expect |
|---|---|---|---|---|
| 1 | Mon 14:50 | Store OUT001 | **New order for Tue 7 Apr** → Chilled → yoghurt shows 60 → "3× your usual. Did you mean 20?" → **Use 20** → **Review order** → **Submit order** | S1-001 placed at **80 cases**; S1 shows the next chilled delivery and the cutoff countdown (BR-40, BR-42) |
| 2 | → Mon 16:05 | Dispatcher | Clock menu → **Mon 16:05** → **Generate plan** (≈15 s) | Draft: 72/85 served, 14/26 chilled, "Limit today: Reefer space · Why?"; pre-dawn and daytime timelines; OUT074 on VEH007. Generating before 16:00 is refused (BR-40) |
| 3 | 16:10 | Dispatcher | **Fleet** tab | VEH038 "Switched off · No driver"; workshop vehicles locked off (BR-10) |
| 4 | 16:12 | Dispatcher | **Deferred · 13** → read groups, reasons, priorities → **Confirm 13 deferrals** → **Review & publish** → **Publish plan v1** | "Published v1"; affected stores notified (BR-21 to BR-23) |
| 5 | 16:25 | Store OUT054 | Open the notice | S8: what moved, why, and when it comes (BR-44) |
| 6 | → Tue 04:14 | Loader Dock 2 | **L1** trips in departure order → open VEH036's trip carrying **S1-005** (T1 on the greedy plan) → **Load** (L2, reverse stop order) → **Report a problem** → OUT003 · S1-005 → Missing → **2** → Short from chiller pick → **Send to dispatcher** | **L4**: van on hold (BR-24 to BR-27) |
| 7 | 04:19 | Dispatcher | Live ops → the hold (or `/dispatch/shortfalls/<id>`) → **D6**: A is recommended ("Send 40 now, 2 more on Trip 2 this morning"); B re-picks all 42 (+25 min); C (40 now, 2 Wednesday) is flagged against OUT003's same-morning rule → **Apply A** | v2 published; v1 unchanged (BR-28 to BR-30) |
| 8 | 04:27 | Loader | Reopen the same trip (it resolves to the latest version) → **L5 Review v2**: T1 OUT003 42 → 40, T2 gains a linked OUT003 +2 stop → **Acknowledge v2 · release van** → check every order → **Mark loaded** | Hold released → van **Loaded**; acknowledging v1 can't release it (BR-31) |
| 9 | 04:36 | Driver VEH036 | **Acknowledge v2 and start** → stop 1 OUT001 (store note "Front shutter shut till 07:00" at the top) → **Arrived** → **Save delivery** (80) → stop 2 OUT003: "2 cases short at loading · already reported", locked, 40 loaded / 42 ordered | Two clocks per stop (plan + likely window); every action saved on the phone first (BR-32 to BR-35, BR-39) |
| 10 | Tue 05:40 | Store OUT001 | **Confirm what arrived** → change yoghurt and fish counts → **Report a problem** (2 damaged, 1 missing) | Separate receipt; per-line issue sent to dispatch (BR-46, BR-47) |
| 11 | 06:14 | Dispatcher | **Live ops** → exceptions ranked by impact → the store report (D10) → decide | Decision recorded and the store is told (BR-48, BR-51) |
| 12 | 06:52 | Driver VEH007 | Go **offline** (DevTools → Network → Offline, or flight mode) → **Trip 2 · Puttalam** link → OUT074 → **Arrived** → **Save delivery** (205) | R4 "Saved on this phone · uploads by itself"; the sync bar says "No signal · keep working" (BR-35) |
| 13 | 07:10 → 07:48 | Store OUT074, then the driver | Store: **Confirm what arrived** → 200 (the van hasn't synced yet) → confirm. Driver goes back online | The 205 upload is a **conflict**: R7 "Your record is kept" with 205 vs 200 and both times; nothing is overwritten (BR-36, BR-37, BR-52) |
| 14 | 07:52 | Dispatcher | **D13**: both counts and evidence → decide | Resolved; both records kept (BR-52) |

**If CP-SAT puts S1-005 on VEH036 T2:** report the shortfall on that trip. A is offered only if a later compatible trip exists; otherwise apply the recommended **B** (all 42, departure +25 min). The loader acknowledges the v2 trip and the driver sees 42 loaded / 42 ordered with no outstanding shortage.

## Significant departures from the Designathon submission
Full list with reasons: [`docs/02-business-rules.md` → Departures](docs/02-business-rules.md#departures-from-the-submitted-design).

- **Optimiser result on the demo VM.** The CP-SAT optimiser with a greedy warm start runs within a 10 s budget. On the 1-vCPU demo VM it doesn't beat the greedy plan and falls back, labelled with its real `solver_status`. On a multi-core machine it returned 72–75 served / 16–18 chilled versus greedy 72 / 14.
- **Real numbers instead of illustrative ones.** Fleet counts, deferral sets, priorities and live-ops counts are computed by the engine on S1 (5 workshop reefers, not 6) (DEP-1, DEP-2).
- **Late risk as windows, not probabilities.** D4 and D6 show real likely-late counts and arrival-window changes; there's no calibrated probability model (DEP-5).
- **Disabled controls with no design or data behind them:** D1 Edit trips and Orders tab (DEP-3, DEP-4); D6 "Call the dock" and S8 "Call dispatch" (no phone numbers supplied) (DEP-7).
- **Notices in English only.** Store notices use the English template; Sinhala/Tamil delivery isn't built (DEP-6).
- **Photo evidence is optional and not uploaded.** The loader's L3 shortfall photo and the store's S6 photo are optional and recorded as references; binary photo upload isn't built. The driver's R3 photo is captured on the phone and only its time is recorded.
- **Loader screens are phone-first.** The dock tablet layouts (Figma 203:106 and others) aren't built.
- **Store receipt before the driver syncs.** S1 offers "Confirm what arrived" once the order is on a published trip, so step 13 works while the van is offline. The receipt starts from the ordered cases and the store's counts stay separate.

## Known gaps (stated honestly)
- **Plans vary between runs.** CP-SAT runs on a wall-clock budget with parallel workers, so trip assignments can differ between generations (see the walkthrough note).
- **Offline is shown with browser offline mode.** The service worker precaches the app, but the walkthrough uses DevTools/flight mode on a live session rather than a cold offline start.
- **Photos.** L3, R3 and S6 photos are optional; only a reference or the time taken is recorded and no image is uploaded.
- **D1 editing and the Orders tab** are disabled, as above.
- **SSE broker is in-process** (single API instance); multi-instance would need Postgres LISTEN/NOTIFY.
- **Verification.** Steps 1–4 and 9 (online) were clicked on the live URL, and steps 12–13 were clicked on a local seeded stack. Results from the full four-role QA run are in [`docs/qa/walkthrough-results.md`](docs/qa/walkthrough-results.md) when present.

## Architecture and documentation
**Modular monolith.** A React PWA (four roles) calls FastAPI (`/api/v1`; Pydantic → OpenAPI → generated TypeScript client), backed by PostgreSQL. A pure-Python planning engine (`packages/engine`: shared rule predicates, CP-SAT with a validated greedy fallback, repair options) does the planning. `events` are append-only, with projection tables for current state. SSE carries live updates, and field phones use a Dexie (IndexedDB) outbox with idempotent `POST /sync`. Diagrams: [docs/03](docs/03-architecture.md). Data model: [docs/04](docs/04-data-model.md).

| Doc | What |
|---|---|
| [Product overview](docs/01-product-overview.md) | Problem framing, evidence, scope |
| [Business rules](docs/02-business-rules.md) | Every rule (BR-xx) and the departures |
| [Architecture](docs/03-architecture.md) | C4 diagrams, modules, flows |
| [Data model](docs/04-data-model.md) | Entities and relationships |
| [API contract](docs/05-api-contract.md) | Endpoints, events, errors |
| [Planning engine](docs/06-planning-engine.md) | Rules, objective, solver, explanations |
| [Offline sync](docs/07-offline-sync.md) | Outbox, idempotency, conflicts |
| [Seed & demo](docs/09-seed-and-demo.md) | Dataset loading, demo clock |
| [Testing](docs/10-testing-and-quality.md) | Tests and CI |
| [Deployment](docs/11-deployment.md) | Azure VM and operations |
| [AI disclosure](docs/ai-disclosure.md) | How AI tools were used, per developer |

## Tech stack
React 19 + TypeScript + Vite (PWA, Dexie) · FastAPI + Pydantic + SQLAlchemy 2 + Alembic · PostgreSQL 16 · OR-Tools CP-SAT · Docker Compose + Caddy · GitHub Actions CI. Reasoning: [ADR-0001](docs/adr/0001-modular-monolith.md), [ADR-0002](docs/adr/0002-stack.md).

## Design
Figma (submitted Designathon file, the specification): https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode · Designathon video: https://youtu.be/CtNg_TqbtmM
