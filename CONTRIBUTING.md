# Contributing

## Setup
1. Put the organisers' dataset pack in `./datasets/`. It's gitignored, so **never commit it**.
2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```
3. Start everything:
   ```bash
   docker compose up --build
   ```
4. Install the commit hooks (once):
   ```bash
   pip install pre-commit && pre-commit install
   ```

## Workflow
1. Pick your work package in [`docs/12-work-breakdown.md`](docs/12-work-breakdown.md).
2. Branch: `feat/<area>-<short>` (e.g. `feat/engine-greedy`, `feat/driver-outbox`).
3. Commit with **conventional commits**: `feat(planning): add publish gate (BR-22)`.
4. Open a PR to `main` using the template. **CI must be green.** Squash-merge.
5. Rebase often. `main` moves fast today.

## Rules of the road
- Business rules live in `packages/engine` (planning) or the API service layer. **Never** only in the UI. Reference `BR-xx`.
- API shapes come from Pydantic → OpenAPI. Regenerate the TS client:
  ```bash
  npm run gen:api
  ```
- Don't call `datetime.now()` or `Date.now()` in domain code. Use the `Clock`.
- Never `UPDATE`/`DELETE` the `events` table.
- No CSV/PDF/data files in commits. A pre-commit hook blocks them.
- Log meaningful AI help in [`docs/ai-disclosure.md`](docs/ai-disclosure.md).

## Code style
- **Python:** ruff (format + lint), mypy; type hints everywhere.
- **TypeScript:** strict; eslint + prettier.
- **Naming:** `snake_case` (Python, DB), `camelCase` (TS), `PascalCase` (components).
