# ADR-0004 · Offline-first PWA for drivers and loaders

- **Status:** Accepted · 2026-10-04
- **Context:** Coverage drops in the hill country, the Kandy corridor and rural districts (brief). Degradation and offline is 10% of the score. The brief requires a web app.
- **Decision:**
  - A PWA with a Workbox app shell.
  - IndexedDB (Dexie) for the cached plan and an **outbox** of events.
  - A batch `POST /sync`, idempotent by `event_id`.
  - Event time counts; received time is recorded.
  - Conflicts go to dispatch and are never overwritten.
- **Consequences:**
  - ✅ Work never blocks; there's a clear sync state.
  - ❌ Needs HTTPS in production (Caddy), and iOS storage limits (fine at our data sizes).
