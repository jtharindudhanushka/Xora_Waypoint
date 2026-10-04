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

## 2. Start the chat with this prompt (copy, then fill in your WP)
```
You are joining the Xora Waypoint Hackathon build (Tech-Triathlon 2026). Deadline: today
23:59 Sri Lanka time; feature freeze 19:00.

1. Read AGENTS.md, then docs/12-work-breakdown.md, docs/02-business-rules.md and
   docs/13-figma-screen-map.md. Then read the docs listed for my work package below.
2. My work package is: <WP-x · name>. Only build that scope.
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

## 3. Per work package: what to tell the agent to read
| WP | Owner | Read (besides AGENTS, 02, 12, 13) | Screens (Figma nodes in 13) | Branch names |
|---|---|---|---|---|
| **WP-1 Engine** | Dev 2 | [06-planning-engine](06-planning-engine.md), [04-data-model](04-data-model.md) | — | `feat/engine-rules`, `feat/engine-solver`, `feat/engine-explain`, `feat/engine-repair` |
| **WP-2 Dispatcher planning** | Dev 2 | [05-api-contract](05-api-contract.md) › Planning, Fleet, Repair · [08-frontend](08-frontend.md) | D1, D3, Fleet, Edit, D4, D6 | `feat/planning-api`, `feat/dispatch-plan-ui`, `feat/dispatch-shortfall` |
| **WP-3 Loader + Driver** | Dev 3 | [07-offline-sync](07-offline-sync.md), [05](05-api-contract.md) › Loading, Driver, Sync · [08](08-frontend.md) | L1–L5 (phone + tablet), R1–R5, R7 | `feat/sync-api`, `feat/dock-ui`, `feat/driver-ui`, `feat/offline-outbox` |
| **WP-4 Store** | Dev 4 | [05](05-api-contract.md) › Orders, Receipts · [08](08-frontend.md) · [09-seed-and-demo](09-seed-and-demo.md) | S1, S2, S5, S6, S8 | `feat/orders-api`, `feat/store-ui`, `feat/receipts` |
| **WP-5 Dispatcher ops** | Dev 4 | [05](05-api-contract.md) › Live ops, Issues · [07](07-offline-sync.md) › conflicts | D5, D10, D13 | `feat/ops-api`, `feat/dispatch-ops-ui` |
| **WP-6 E2E** | Dev 4 | [09](09-seed-and-demo.md) › Judge walkthrough · [10-testing](10-testing-and-quality.md) | all | `test/e2e-walkthrough` |

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
