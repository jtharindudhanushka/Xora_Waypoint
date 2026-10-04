# ADR-0006 · Injectable clock with demo override

- **Status:** Accepted · 2026-10-04
- **Context:** The walkthrough spans Mon 14:50 → Tue 07:52 (the 16:00 cutoff, the 03:30 pre-dawn lane). Judges test at arbitrary real times.
- **Decision:**
  - All domain time comes from a `Clock` dependency. `clock_settings.demo_now` overrides it.
  - The dispatcher can set or advance it, and changes are broadcast over SSE.
  - Device `event_time` on field devices is taken from server-synced time (offset learned on bootstrap) so offline events line up with the demo clock.
- **Consequences:** never call `datetime.now()` or `Date.now()` in domain code (lint rule / review checklist).
