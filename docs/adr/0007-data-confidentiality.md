# ADR-0007 · Competition data stays out of the repository

- **Status:** Accepted · 2026-10-04
- **Context:** The repo is public. The T&C forbid sharing or publishing the datasets **or any derivatives**, on pain of disqualification. The brief asks for seeding with the shared datasets.
- **Decision:**
  - `datasets/` is gitignored, and the README tells judges to place the organisers' pack there.
  - The seed validates the layout and fails with clear guidance.
  - Derived artefacts (travel ratios, model files, dumps) are computed at seed time into the DB and never committed.
  - The deployed instance is seeded from a copy uploaded directly to the server.
  - Our own invented demo fields (items, names, store rules) are committed.
  - CI uses hand-written synthetic fixtures.
- **Consequences:** a fresh clone needs the pack (judges have it). If the organisers allow committing the data, this becomes a one-line `.gitignore` change.
