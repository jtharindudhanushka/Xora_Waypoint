# 12 · Work breakdown — Hackathon day (Sun 4 Oct 2026)

**Hard deadline 23:59 · internal submit 21:00 · feature freeze 19:00.** All times are Sri Lanka time.

## Team
| Person | Where | Owns |
|---|---|---|
| **Lead** (Tharindu) | In office | **Foundation** (WP-0) → integration → deployment → README/video |
| **Dev 2** | In office | **Engine** (WP-1) → dispatcher planning UI (WP-2) |
| **Dev 3** | WFH | **Loader + Driver** PWA with offline sync (WP-3) |
| **Dev 4** | WFH | **Store** UI (WP-4) → dispatcher ops/issues (WP-5) → e2e (WP-6) |

## Work packages
| WP | Scope | Depends on | Done when |
|---|---|---|---|
| **WP-0 Foundation** | Monorepo skeleton; `docker-compose.yml` (db, api, web) + `.env.example`; FastAPI app factory, config, logging, `/health`; SQLAlchemy + Alembic + **all tables from [04](04-data-model.md)**; seed (dataset validation + reference + S1 + demo extras); auth (login, JWT, role guards); Clock service + `/clock`; SSE endpoint; Vite React app shell with router, auth, header, tokens; generated API client; CI workflow | — | `docker compose up` → log in as all 4 roles → empty role homes |
| **WP-1 Engine** | `packages/engine`: models, rules (BR-01 to BR-12), trip time, greedy, CP-SAT, sequencing, likely window, explanations, repair, 2B export; tests | — (pure Python) | S1 plan passes `validate()` + `check_allocation.py`; repair returns A/B/C |
| **WP-2 Dispatcher planning** | API: generate, get plan, validate-move, edits, lock, deferrals confirm, publish-check, publish, fleet; UI: **D1** timeline + trip panel, Deferred tab, Fleet tab, Edit mode, Publish dialog; **D6** + repair API | WP-0, WP-1 | Walkthrough steps 2–4, 7 |
| **WP-3 Loader + Driver** | API: dock trips, load list, `/sync` + bootstrap, holds, acks, vehicle today; UI: **L1–L5** (phone + tablet), **R1–R5, R7**; Dexie outbox, sync banner, service worker | WP-0 (sync contract) | Steps 6, 8, 9, 12, 13 |
| **WP-4 Store** | API: usual items, order check, place order, next deliveries, driver note, receipt draft/confirm, issues, notifications; UI: **S1, S2, S5, S6, S8** | WP-0 | Steps 1, 5, 10 |
| **WP-5 Dispatcher ops** | API: ops, exceptions (ranked), apply fix, issues + resolve; UI: **D5, D10, D13** | WP-0, WP-3 events | Steps 11, 14 |
| **WP-6 E2E + polish** | Playwright walkthrough; empty/error states; fidelity pass against Figma | All | e2e green |
| **WP-7 Ship** | Deploy (Azure), README walkthrough + departures, AI disclosure, architecture/data-model diagrams, **5–8 min video**, submit the form | All | Form submitted |

## Timeline (today)
| Time | Milestone |
|---|---|
| 13:30–14:00 | Docs read by everyone; claim WPs; branches created |
| **14:00–16:00** | **WP-0 foundation** (Lead) ∥ **WP-1 engine** (Dev 2) ∥ Dev 3 and Dev 4 build UI against **mocked API types** from [05](05-api-contract.md) |
| **16:00** | **Foundation merged**: schema, seed, auth, client generated. Everyone rebases |
| 16:00–19:00 | WP-2 ∥ WP-3 ∥ WP-4 → WP-5 |
| **19:00** | **Feature freeze.** Only fixes after this |
| 19:00–20:00 | WP-6 e2e + fidelity fixes · Lead deploys (WP-7) |
| 20:00–20:45 | Record the video (all 4 roles + architecture), README final |
| **21:00** | **Submit** (buffer until 23:59) |

## Cut list if behind (in this order)
1. D10 store-report decision → read-only view.
2. Tablet split layouts (keep phone layouts, which are what's judged).
3. Repair option B (keep A and C).
4. si/ta translations → English + one language.
5. CP-SAT → greedy only (still rule-valid; it's labelled "Greedy" honestly).

**Never cut:** rule validity, deferral reasons, the publish gate, offline outbox + idempotent sync, `docker compose up` + seed, README walkthrough.
