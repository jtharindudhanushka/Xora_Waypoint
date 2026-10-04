# 10 · Testing and quality

## Test pyramid
| Layer | Tool | Scope | Owner |
|---|---|---|---|
| Engine unit + property | pytest + Hypothesis | Every BR-01 to BR-12 rule; trip-time worked examples; `plan()` output always passes `validate()`; S1 regression | Engine |
| API | pytest + httpx `AsyncClient` against a test Postgres (testcontainers or the compose DB) | Auth and scopes, cutoff, publish gate, hold/ack, sync idempotency, conflicts | Each module owner |
| Web unit | Vitest + Testing Library | Outbox, formatters, key components | Frontend owners |
| End-to-end | Playwright | **The judge walkthrough** (steps 1–14), incl. `setOffline` for R4/R5 | Store owner |
| Dataset gate | the organisers' `check_allocation.py` | S1 engine plan exported to 2B CSV → `PASSED` (runs only when `datasets/` is present: locally, and on the deploy box) | Engine |

The minimum before submitting: **engine tests green, API smoke tests green, e2e walkthrough green locally.**

## Tooling and conventions
| Area | Tool / rule |
|---|---|
| Python format + lint | **ruff** (format + lint), line length 100 |
| Python types | **mypy --strict** on `packages/engine`; standard on `services/api` |
| TS lint/format | **eslint** (typescript-eslint, react-hooks) + **prettier** |
| TS types | `tsc --noEmit` (strict) |
| Pre-commit | `pre-commit` hooks: ruff, prettier, end-of-file, no large files, **no CSV/PDF** |
| Commits | **Conventional commits**: `feat(planning): …`, `fix(sync): …`, `docs: …` |
| Branches | `feat/<area>-<short>` → PR → `main` (squash merge). No direct pushes once CI exists |
| PRs | Template: what/why, BR ids touched, screenshots, tests. One reviewer (or self-review checklist under time pressure) |
| Rule traceability | Reference `BR-xx` in code comments and test names |

## CI (GitHub Actions, `.github/workflows/ci.yml`)
Jobs run on every PR and push to `main`:
1. **engine:** ruff, mypy, pytest.
2. **api:** ruff, mypy, pytest (Postgres service container).
3. **web:** npm ci, lint, `tsc`, vitest, build.
4. **compose:** `docker compose build` (and smoke `/health` if time allows).

CI has **no access to the dataset** (public repo). Tests that need it use small **hand-written synthetic fixtures** in `tests/fixtures/` (our own invented outlets and vehicles, not derived from the data). The `check_allocation` gate runs locally and on the deploy box.

## Definition of done (per feature)
- [ ] Matches the Figma frame (layout, copy, states).
- [ ] Rules enforced server-side, with BR ids referenced.
- [ ] Loading, empty, error and offline states handled.
- [ ] Tests added; CI green.
- [ ] Docs touched if behaviour or the contract changed.
