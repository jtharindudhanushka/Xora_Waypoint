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

## Git workflow (team rules)
We show our engineering process, so the history matters as much as the code.

| Rule | Detail |
|---|---|
| **Never commit to `main` directly** | All work happens on a branch, and lands through a pull request |
| **One branch per slice** | `feat/<area>-<short>`, `fix/<area>-<short>`, `docs/<topic>`, `chore/<topic>`, `test/<area>`. Stack a branch on its parent if it depends on unmerged work, and say so in the PR |
| **Small, regular commits** | One logical step per commit. Never one giant commit. Conventional messages: `feat(planning): add publish gate (BR-22)` |
| **Open a PR early** | Open a draft PR as soon as the branch exists; mark it ready when CI is green |
| **The author never merges their own PR** | A teammate reviews and merges. The lead's PRs are merged by a teammate |
| **Merge with a merge commit** | Use "Create a merge commit" (not squash, not rebase), so every commit stays visible in `main` |
| **Never delete branches** | Keep every branch after merging; it's part of the record of how we worked. Untick "delete branch" on GitHub |
| **Stacked PRs merge in order** | Merge the parent first; the child PR's base then moves to `main` automatically |
| **Rebase only your own unmerged branch** | Never rewrite `main` or a branch someone else has pulled; never force-push `main` |
| **No AI co-author trailers — strictly** | Commit messages and PR descriptions must **not** contain `Co-Authored-By: Claude`, `Generated with …`, or any other AI-agent attribution or signature. Commits are authored by the team member who made them. AI use is disclosed in one place only: [`docs/ai-disclosure.md`](docs/ai-disclosure.md) |

### Day-to-day
1. Pick your work package in [`docs/12-work-breakdown.md`](docs/12-work-breakdown.md).
2. Create the branch from `main`:
   ```bash
   git checkout main && git pull && git checkout -b feat/<area>-<short>
   ```
3. Commit small steps as you go; push often:
   ```bash
   git push -u origin HEAD
   ```
4. Open the PR with the template, link the WP and the BR ids, and ask a teammate to merge.

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
