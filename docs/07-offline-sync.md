# 07 · Offline sync (driver and loader)

Goal: **work never stops when the signal drops, nothing is duplicated, nothing is lost, and nothing is silently overwritten.** Rules BR-35 to BR-38, BR-52 and BR-53. Decision: [ADR-0004](adr/0004-offline-first-pwa.md).

## Client side (apps/web)
1. **Bootstrap:** on login and on plan acknowledgement, `GET /sync/bootstrap` caches today's plan version, trips, stops, outlet profiles, store notes and the pre-filled shortfall in **IndexedDB** (Dexie).
2. **App shell offline:** the Workbox service worker precaches the built app. Fonts are self-hosted.
3. **Every action is an event**, written to the **outbox** table first:
   ```ts
   type OutboxEvent = {
     event_id: string;            // crypto.randomUUID()
     type: 'trip_acknowledged' | 'load_checked' | 'shortfall_reported' | 'arrived' | 'outcome_recorded' | 'note_added';
     entity: { type: 'trip' | 'stop' | 'order'; id: string };
     plan_version_id: string;     // the version the user was looking at
     event_time: string;          // device time, ISO with +05:30 (the time that counts, BR-37)
     payload: Record<string, unknown>;
     attempts: number; status: 'queued' | 'sending' | 'accepted' | 'duplicate' | 'conflict';
   }
   ```
4. **The UI reads from local state**, so "Saved on this phone" is shown immediately (R4).
5. **Flush:** on `online`, on app focus, and every 30 s while queued. Events are sent **in order** in batches of up to 50, with exponential backoff (max 5 min).
6. **Sync banner** (all field screens): `Online · nothing waiting` / `No signal · N saved on this phone` / `Uploading N` / `Uploaded at HH:MM` / `1 needs review`.
7. **Auth offline (BR-38):** the token and user are cached. If the token has expired while offline, events stay queued and are sent after re-login. They are never dropped.

## Server side (`POST /api/v1/sync`)
```
for each event in order:
  if exists(event_id): result = duplicate                       # idempotent (BR-36)
  else:
    insert into events (append-only), received_at = clock.now()
    apply to projections (stop status, quantities, holds, acks)
    detect conflicts:
      stale_plan      : event.plan_version_id != current version AND the stop/order changed between them (BR-53)
      count_conflict  : outcome qty ≠ store receipt qty for the same order (BR-52)
    result = conflict(conflict_id) | accepted
commit per event (one bad event doesn't block the batch)
NOTIFY → SSE sync.applied / conflict.created
```
- **Ordering:** the server orders by the client sequence within a device. Event time is kept as recorded, and `received_at` is set by the server.
- **Conflicts never overwrite.** Both records stay. An `issues` row (`kind = count_conflict | stale_plan`) is opened for dispatch (D13). The driver sees R7.
- **Dead zones (BR-50):** a vehicle silent in a district flagged `is_dead_zone` shows **Pending sync** in D5, not an alarm.

## Testing offline
- Playwright `context.setOffline(true)`: record an outcome → assert R4 → go online → assert R5 and the server row exists exactly once.
- Unit test: posting the same batch twice gives the second result `duplicate` and no extra projection changes.
- Conflict test: a store receipt of 200, then a driver event of 205 → `conflict`, both kept.
