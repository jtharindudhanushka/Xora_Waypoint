# ADR-0003 · Append-only event log and immutable plan versions

- **Status:** Accepted · 2026-10-04
- **Context:** Offline devices resend; disputes need evidence; plans change after publishing (shortfalls) and every role must see the same version.
- **Decision:**
  - Field actions are **events** with a client-generated `event_id`, stored append-only (DB triggers block UPDATE and DELETE). Current state lives in projection tables updated in the same transaction.
  - **Published plan versions are immutable.** Changes create v(n+1), and acknowledgements are recorded.
- **Consequences:**
  - ✅ Idempotent sync; a full audit trail (who, when, why); conflicts detectable; diffs between versions are trivial.
  - ❌ More tables, and projection logic must be correct (covered by tests).
