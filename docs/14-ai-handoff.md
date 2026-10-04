# 14 · Picking up work with a fresh AI chat

Each teammate starts a **new AI session** (Claude Code or any coding agent) in their clone of this repo. The repo carries all the context, so the agent should read it rather than you re-explaining.

## 1. Set up (once, ~5 min)
```bash
git clone https://github.com/jtharindudhanushka/Xora_Waypoint.git && cd Xora_Waypoint
# Put the organisers' dataset pack in ./datasets (never commit it)
cp .env.example .env
docker compose up --build            # → http://localhost:8080, sign in with a demo account
pip install pre-commit && pre-commit install   # hooks: no data files, no AI trailers, commit format
```
**Figma access for your agent (for pixel-exact UI):**
- **Claude Code / Claude desktop:** enable the **Figma connector** (or the Figma MCP server). The agent can then read frames directly (design context + screenshots) from the links in [13-figma-screen-map.md](13-figma-screen-map.md).
- **No connector:** open each frame link, export it as PNG (right-click → Copy/Export as PNG, 2×), and give the image to the agent together with the frame's rationale text.

## 2. Start the chat with this prompt (copy, then fill in your track)
```
You are joining the Xora Waypoint Hackathon build (Tech-Triathlon 2026). Deadline: today
23:59 Sri Lanka time; feature freeze 19:00.

1. Read AGENTS.md, then docs/12-work-breakdown.md, docs/02-business-rules.md and
   docs/13-figma-screen-map.md. Then read the docs listed for my work package below.
2. My track is: <Dev 2 | Lead> (see docs/12). Only build that scope.
3. The UI must match the Figma frames EXACTLY (copy, layout, spacing, tokens, states).
   For each screen, read the frame (Figma connector, or the PNG I attach) and its rationale
   text before writing code. Use only the design tokens and existing UI primitives in
   apps/web/src/ui. If something can't match, stop and tell me; don't improvise.
4. Business rules live in the API/engine, never only in the UI. Reference BR ids in code
   and test names.
5. Git rules (CONTRIBUTING.md): create a feature branch from main, small conventional commits,
   push and open a PR; never commit to main; never delete branches. NEVER add
   "Co-Authored-By", "Generated with" or any AI attribution to commits or PRs.
6. Never commit anything from datasets/ or any CSV/PDF/model file.
7. After each screen: run the tests and lint, take a screenshot at the Figma frame size,
   and compare it side by side with the frame before committing.
Start by summarising the plan for my WP and the screens/endpoints you'll build, then wait
for my go.
```

## 3. Who does what (two developers)
The full task lists, targets and milestone are in [12-work-breakdown.md](12-work-breakdown.md).

| Person | Track | Read (besides AGENTS, 02, 12, 13) | Screens (Figma nodes in 13) |
|---|---|---|---|
| **Dev 2** | Engine → dispatcher planning → shortfall repair | [06-planning-engine](06-planning-engine.md), [04-data-model](04-data-model.md), [05-api-contract](05-api-contract.md) › Planning, Fleet, Repair, [08-frontend](08-frontend.md) | D1 (Timeline + trip panel), D3 Deferred tab, Fleet tab, D4 Publish dialog, D6; stretch: Edit trips |
| **Lead** | Deploy → sync API → driver → loader → store → submission | [07-offline-sync](07-offline-sync.md), [05](05-api-contract.md) › Sync, Driver, Loading, Orders, Receipts, [09-seed-and-demo](09-seed-and-demo.md), [11-deployment](11-deployment.md) | R1–R5, R7 · L1–L5 · S1, S2, S5, S6, S8 |

**Integration point:** Dev 2 writes published plan versions (trips, stops, deferrals); the lead's screens read them. **Milestone M1 at about 16:45:** Dev 2 merges "generate + publish". Until then the lead uses a dev-only `fake_plan` helper.

### First prompt for Dev 2 (paste into the fresh chat after the generic prompt above)
```
My track is Dev 2: planning engine → dispatcher planning → shortfall repair.
Work through these tasks IN ORDER, one branch and one PR each (docs/12-work-breakdown.md
› "Task list — Dev 2"):

2.1 feat/engine-rules: create packages/engine (pyproject, src/xora_engine, tests) as a pure
    Python library with no FastAPI or SQLAlchemy imports (ADR-0005). Dataclass models, rules
    BR-01 to BR-12 as pure predicates, trip_minutes() (BR-08) with the worked checks
    101/112/64 min as tests, validate(). Must pass ruff and mypy --strict.
2.2 feat/engine-greedy: plan() = prune → priority (BR-13 formula in docs/06) → greedy
    first-fit grouped by (brand, district) → sequence stops → plan times → likely window from
    travel ratios → deferral reason codes (BR-15), unavoidable vs choice (BR-16), bottleneck
    + KPIs (BR-17). Add a Task 2B CSV export, run it on scenario S1 from ./datasets, and
    check with `python datasets/check_allocation.py <csv>`: it must print PASSED.
    Never commit the CSV.
2.3 feat/planning-api: services/api/app/modules/planning (router → service → repository +
    an adapter between DB rows and engine types). Endpoints from docs/05 › Planning and
    Fleet: generate, get plan, fleet list/switch, deferrals confirm (BR-21), publish-check
    (BR-22), publish (BR-23, immutable version + SSE "plan.published"). Then run
    `python services/api/scripts/export_openapi.py` and `npm run gen:api`. Tests with
    synthetic fixtures. This is milestone M1: tell me as soon as it's mergeable.
2.4 feat/dispatch-plan-ui: D1 Plan workspace EXACTLY as Figma 196:383 (KPI header, Limit
    today strip + Why?, pre-dawn and daytime timelines, trip panel), Deferred tab 197:440,
    Fleet tab 198:274, Publish dialog 197:682. Replace the RoleHome placeholder at
    /dispatch/plan.
2.5 feat/dispatch-shortfall: engine repair() options A/B/C with the store split rule
    (BR-28, BR-29) and D6 exactly as Figma 156:283; apply → new version v2.
Stretch only if all of the above is merged: CP-SAT behind plan(), then Edit trips (205:342).

Start with 2.1: show me the package layout and the rule list, then build it.
```

### First prompt for the Lead (paste after the generic prompt)
```
My track is Lead: Docker check + deploy → sync API → driver → loader → store → submission.
Follow docs/12-work-breakdown.md › "Task list — Lead" in order, one branch and one PR each.
Dev 2 owns the engine and the planning API; until milestone M1 is merged, build a dev-only
helper `python -m app.dev.fake_plan` that publishes a simple S1 plan version for the
driver, loader and store screens to read. Start with 1.1 (run docker compose, fix issues,
deploy per docs/11).
```

## 4. What already exists (don't rebuild it)
| Area | Where | Notes |
|---|---|---|
| Settings, logging, errors (RFC 7807), request ids | `services/api/app/core/` | Raise `DomainError(code, detail, rule_id=…)` from services |
| DB models for **every** table + migration | `services/api/app/modules/*/models.py`, `alembic/versions/0001_*` | Add a new Alembic revision if you change a model; the drift test fails otherwise |
| Seed (S1 + demo users + item lines) | `services/api/app/seed/` | `python -m app.seed --reset-demo` to start over |
| Auth + role guards | `app/core/deps.py` | `Depends(require_roles("dispatcher"))`, `CurrentUser`, `DbDep`, `ClockDep` |
| Demo clock | `app/core/clock.py` | Use `clock.now()`; never `datetime.now()` in domain code |
| Live updates | `app/modules/stream/broker.py` | `await broker.publish("plan.published", data, audience=lambda s: …)` |
| Web shell, sign-in, routing, tokens | `apps/web/src/` | Replace `RoleHome` placeholders in `app/router.tsx` with real screens |
| Typed API client | `apps/web/src/api/client.ts` | After API changes: `python services/api/scripts/export_openapi.py` then `cd apps/web && npm run gen:api` (CI checks the contract is current) |
| UI primitives | `apps/web/src/ui/` | `Button`, `StatusBadge`; add more here, and keep them token-based |

## 5. Definition of done for a PR
- CI green (API: ruff, mypy, pytest, contract · web: oxlint, prettier, tsc, vitest, build).
- Figma side-by-side screenshot(s) in the PR, plus the fidelity checklist from [13](13-figma-screen-map.md#fidelity-checklist-per-screen-before-opening-the-pr).
- BR ids listed in the PR; docs updated if behaviour or the contract changed.
- AI help logged in [ai-disclosure.md](ai-disclosure.md) (that's the **only** place AI is mentioned).
- A teammate merges with **"Create a merge commit"**, and the branch is kept.
