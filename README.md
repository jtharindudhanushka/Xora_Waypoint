# Xora · Waypoint — explainable delivery planning

> Tech-Triathlon 2026 (Rootcode) · Hackathon submission · Team **Xora**

Waypoint Group runs three retail brands (Fresh, Style, Tech) with 120 outlets, 60 vehicles and two depots. On most days the fleet can't serve every order. **Xora** connects ordering, planning, loading, delivery and receipt across four roles. It plans inside every hard rule, explains every deferral, and keeps working when the signal drops.

| Role | Device | Lands on |
|---|---|---|
| Dispatcher | Desktop | Plan workspace: one-click plan, deferrals with reasons, publish gate, live exceptions |
| Loader | Dock tablet / phone | Load in reverse stop order, report shortfalls, acknowledge plan revisions |
| Driver | Phone, offline-first | Acknowledge the plan, record outcome and proof offline, sync later |
| Store manager | Phone / desktop | Order before the 16:00 cutoff, honest arrival windows, confirm receipt, report issues |

> 🤖 **Teammates and AI agents: start with [`AGENTS.md`](AGENTS.md), then [`docs/`](docs/README.md).**

---

## Quick start (local)

**Prerequisites:** Docker 24+ with Compose v2, and the organisers' **Tech-Triathlon 2026 dataset pack**.

1. **Add the dataset pack.** The competition data is confidential and is **never committed** to this public repo. Copy the organisers' pack into `./datasets/` so the layout is:
   ```
   datasets/
     check_allocation.py
     data/General Data/outlets.csv, vehicles.csv, calendar.csv, district_travel.csv, service_allowance.csv, ...
     data/Test Data/task2b_peak_day_scenarios.csv, task2b_peak_day_fleet.csv, ...
     data/Training Data/...
   ```
   `datasets/` is gitignored. Seeding checks this layout first and stops with a clear message if anything is missing.
2. **Configure:**
   ```bash
   cp .env.example .env
   ```
3. **Run the whole stack** (database, migrations, seed, API, web):
   ```bash
   docker compose up --build
   ```
4. Open **http://localhost:8080**.

> Status: 🚧 under construction (Hackathon day). See [`docs/12-work-breakdown.md`](docs/12-work-breakdown.md).

## Seeded accounts
| Role | Email | Password | Lands on |
|---|---|---|---|
| Dispatcher · Peliyagoda DC | `dispatch.peliyagoda@waypoint.demo` | `demo1234` | D1 Plan workspace |
| Loader · Dock 2 | `loader.dock2@waypoint.demo` | `demo1234` | L1 Loading trips |
| Driver · VEH036 | `driver.veh036@waypoint.demo` | `demo1234` | R1 Today's trip |
| Store manager · OUT001 | `store.out001@waypoint.demo` | `demo1234` | S1 Home |

The demo clock starts at **Mon 6 Apr 2026, 14:50** (the day before peak-day scenario S1). Advance it from the clock control in the header.

## Judge walkthrough
The full numbered walkthrough is in [`docs/09-seed-and-demo.md`](docs/09-seed-and-demo.md#judge-walkthrough). It's filled in as the build completes.

## Deployed app
- URL: _TBD_
- The deployed database is seeded from the organisers' dataset pack.

## Documentation
| Doc | What |
|---|---|
| [Product overview](docs/01-product-overview.md) | Problem framing, evidence, scope |
| [Business rules](docs/02-business-rules.md) | Every rule the system enforces, traced to the submitted design |
| [Architecture](docs/03-architecture.md) | C4 diagrams, modules, key flows, quality attributes, scale |
| [Data model](docs/04-data-model.md) | Entities and relationships |
| [API contract](docs/05-api-contract.md) | Endpoints, events, errors |
| [Planning engine](docs/06-planning-engine.md) | Rules, objective, solver, explanations |
| [Offline sync](docs/07-offline-sync.md) | Outbox, idempotency, conflicts |
| [Frontend](docs/08-frontend.md) | Routes per role, state, tokens |
| [Seed & demo](docs/09-seed-and-demo.md) | Dataset loading, demo clock, walkthrough |
| [Testing & quality](docs/10-testing-and-quality.md) | Test pyramid, CI, conventions |
| [Deployment](docs/11-deployment.md) | Azure VM (primary), Render + Neon (fallback) |
| [Work breakdown](docs/12-work-breakdown.md) | Who builds what, tonight |
| [ADRs](docs/adr/) | Architecture decisions |
| [AI disclosure](docs/ai-disclosure.md) | How AI tools were used |

## Departures from the submitted design
Tracked in [`docs/02-business-rules.md` → Departures](docs/02-business-rules.md#departures-from-the-submitted-design).

## Tech stack
React + TypeScript + Vite (PWA) · FastAPI + Pydantic + SQLAlchemy 2 + Alembic · PostgreSQL 16 · OR-Tools CP-SAT · Docker Compose · GitHub Actions. The reasoning is in [ADR-0001](docs/adr/0001-modular-monolith.md) and [ADR-0002](docs/adr/0002-stack.md).

## Design
Figma (submitted Designathon file): https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode · Demo video: https://youtu.be/CtNg_TqbtmM
