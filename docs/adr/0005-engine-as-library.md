# ADR-0005 · Planning engine as a pure library

- **Status:** Accepted · 2026-10-04
- **Decision:** `packages/engine` has no web or DB imports. It takes dataclasses in and returns dataclasses out. The API adapts rows ↔ engine types. The **same rule predicates** are used for validation (drag and drop, publish gate) and inside the solver.
- **Why:**
  - Correctness is checkable in isolation, and against the organisers' `check_allocation.py`.
  - It can be reused by Datathon Task 2B.
  - It can be built in parallel with the API.
- **Consequences:** an adapter layer in `services/api/app/modules/planning/adapter.py`.
