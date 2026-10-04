# Video: code and architecture segment

Target: about 75 seconds at a conversational pace. Use the deployed app and the
merged source. Do not show dataset contents or credentials.

## Screen cues

| Time | Show |
|---|---|
| 0-15 s | `docs/03-architecture.md`, system/deployment Mermaid diagram |
| 15-35 s | `packages/engine/src/xora_engine/cpsat.py`, then `validation.py` |
| 35-50 s | `services/api/app/modules/repair/service.py`, v2/hold transfer |
| 50-65 s | `apps/web/src/features/field/outbox.ts`, then sync event model |
| 65-80 s | `docs/04-data-model.md`, ER diagram; briefly return to the running app |

## Spoken script

“Xora runs as a modular monolith: a React PWA, one FastAPI service and PostgreSQL.
On our Azure VM, Caddy provides HTTPS; nginx serves the app and proxies the API
and server-sent events.

The planning engine is a separate Python library. Greedy gives CP-SAT a feasible
starting point. CP-SAT allocates compatible orders under capacity, time, fuel and
locked-trip constraints. After sequencing, the shared rule validator checks the
result. If solving fails or gives no valid improvement, we retain greedy. The
screen reports the actual solver status and measured KPIs.

A loading shortfall creates a hold. Dispatch compares repairs against the store's
split rule, then explicitly chooses one. Applying it creates published version
two, preserves version one, and moves the hold to the new trip. The loader must
acknowledge that version before the hold releases.

Drivers and loaders save actions in an IndexedDB outbox first. Sync deduplicates
client event IDs and retains device and received timestamps. Store receipts are
independent evidence; conflicting counts become issues for dispatch, preserving
both records. PostgreSQL keeps the audit trail, while scoped SSE signals tell
clients to refetch current state.”

## Rehearsal notes

- Preserve the deployed solver configuration and VM size. Read `solver_status`;
  72 served alone does not prove a greedy fallback.
- For the lead-confirmed greedy demo, OUT003/S1-005 is on VEH036 T1. Always inspect
  the actual published plan before the shortfall segment; CP-SAT may place it on
  T2. Use the conditional steps 6-9 in `docs/09-seed-and-demo.md` and PR #29.
- SSE uses an in-process broker, not PostgreSQL LISTEN/NOTIFY. The deployed API
  uses one Uvicorn worker. Do not claim distributed event fan-out or a job queue.
