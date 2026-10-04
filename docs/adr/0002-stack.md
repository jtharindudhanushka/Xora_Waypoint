# ADR-0002 · Technology stack

- **Status:** Accepted · 2026-10-04
- **Decision:**
  - **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic.
  - **Database:** PostgreSQL 16.
  - **Solver:** OR-Tools CP-SAT.
  - **Frontend:** React 18 + TypeScript + Vite PWA, TanStack Query, Dexie, Workbox, Tailwind, dnd-kit.
  - **Tests:** pytest, Hypothesis, Vitest, Playwright.
  - **Ops:** Docker Compose, GitHub Actions, Caddy.
- **Why:**
  - The engine and models are Python, so the backend is Python too. That gives one language for the domain rules, and the Datathon reuses the engine.
  - FastAPI generates OpenAPI, so the TS client is generated and the contract is typed end to end.
  - React has the richest ecosystem for drag and drop, timelines and offline PWA, the team knows it, and AI tools produce it most reliably.
- **Rejected:**
  - NestJS: the rules would exist in two languages.
  - Next.js: server rendering fights offline-first.
  - SvelteKit/Vue: smaller ecosystem for our widgets; less team familiarity.
  - Flutter/React Native: the brief requires a web app; a desktop timeline is awkward.
