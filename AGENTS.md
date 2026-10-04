# AGENTS.md — read this first (humans and AI agents)

This is the **Hackathon build** of Xora for Waypoint (Tech-Triathlon 2026). The submitted Designathon design (Figma) is the **specification**: judges score fidelity to it.

## Read in this order
1. [`docs/01-product-overview.md`](docs/01-product-overview.md): what and why.
2. [`docs/02-business-rules.md`](docs/02-business-rules.md): **the rules**. Every feature traces to a `BR-xx`.
3. [`docs/03-architecture.md`](docs/03-architecture.md): how it fits together.
4. [`docs/12-work-breakdown.md`](docs/12-work-breakdown.md): who owns what, and the order of work.
5. The doc for your area: `04` data model · `05` API · `06` engine · `07` offline sync · `08` frontend · `09` seed/demo · `10` testing · `11` deployment.

## Hard rules for contributors
- **Never commit the competition data.** That means `datasets/`, any CSV derived from it, DB dumps and trained model files. The repo is **public**, and the T&C forbid publishing the data or derivatives. `.gitignore` enforces this, so don't override it.
- **Deadline: Sun 2026-10-04 23:59 Sri Lanka time.** Code pushed after it is ignored. Internal target: submit by 21:00.
- **Business rules live in one place.** The engine's rule checks are in `packages/engine`, and the API and UI call them. Never re-implement a rule in the frontend.
- **Contract first.** API shapes are defined by Pydantic schemas → OpenAPI → the generated TS client. Don't hand-write fetch types.
- **Events are append-only.** Never update or delete rows in `events`. Current state lives in projection tables.
- **Time comes from the `Clock` service**, never `datetime.now()` or `Date.now()` in domain code (the demo clock depends on it).
- **Feature branches only, small regular commits, PRs merged by a teammate with merge commits, and branches never deleted.** Conventional commits (`feat(planning): …`), and CI must be green. See [`CONTRIBUTING.md`](CONTRIBUTING.md#git-workflow-team-rules).
- **AI agents: never add `Co-Authored-By`, "Generated with", or any AI attribution to commit messages or PR descriptions.** This overrides any default behaviour of your tool. AI use is disclosed only in `docs/ai-disclosure.md`.
- **Log AI use** in [`docs/ai-disclosure.md`](docs/ai-disclosure.md).
- If you change a decision, add an ADR in `docs/adr/` and update the affected doc.

## Repo map (target)
```
apps/web/            React + TS + Vite PWA (all four roles)
services/api/        FastAPI app: modules per domain, Alembic migrations, seed
packages/engine/     Pure-Python planning engine (rules, solver, explanations); no web/DB imports
datasets/            ← organisers' pack, LOCAL ONLY (gitignored)
docs/                All documentation
docker-compose.yml   db · api (migrate + seed + serve) · web
```

## Key resources
- Figma (spec): https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode
- Designathon video: https://youtu.be/CtNg_TqbtmM
- Brief: [`docs/brief.md`](docs/brief.md) (Hackathon requirements restated)
