# ADR-0001 · Modular monolith

- **Status:** Accepted · 2026-10-04
- **Context:** ~140 orders/day, ~200 users, 1–2k events/day. One team, one day to build, with engineering quality scored (25%).
- **Decision:** One FastAPI service with strict internal modules (router → service → repository), one React PWA, one Postgres. Modules talk only through service interfaces.
- **Consequences:**
  - ✅ One deployable; simple local = production parity; transactions across modules.
  - ✅ Clear seams to split later (planning solves → worker).
  - ❌ Shared failure domain, which is acceptable at this scale.
- **Rejected:**
  - Microservices: network failure modes and ops cost without a scale need.
  - BaaS (Supabase/Firebase): would push rules and sync into glue code.
