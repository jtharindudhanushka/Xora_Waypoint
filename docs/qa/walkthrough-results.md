# Walkthrough results · live deployment

**Pass 1 (pre-dock)** · 2026-10-04 22:38–22:52 SLST · `https://xora-waypoint.southeastasia.cloudapp.azure.com`
after the lead's `--reset-demo`. Suite: [`e2e/walkthrough.spec.ts`](../../e2e/walkthrough.spec.ts),
run step by step with sessions a human captured via [`e2e/capture-sessions.cjs`](../../e2e/capture-sessions.cjs)
(the tooling never handles a password). Values below are read from the live API, not assumed.

| # | Who | Result | Real values / notes |
|---|---|---|---|
| 1 | Store OUT001 | ✅ Pass | S1-001 `placed`, 80 units, delivery 2026-04-07 |
| 2 | Dispatcher | ✅ Pass | Solver `FEASIBLE` in 11.6 s · **72 / 85 orders served · 17 / 26 chilled** · 18 stops at risk · 13 deferrals · value 970.9 · reefer 129.3 / 172.4 m³ · **30 trips on 17 vehicles** · limit: reefer trip slots 8 / 8. VEH036 has **2 trips** (T1 938.2 kg, T2 913.1 kg — docs/09's "1,096 kg > 1,040 kg" does not match). S1-001 → VEH036 T1 · S1-005/OUT003 → **VEH036 T2** · S1-083/OUT074 → **VEH007 T2** |
| 3 | Dispatcher | ✅ Pass | Fleet · 17 of 38: VEH038 "Switched off · No driver" |
| 4 | Dispatcher | ✅ Pass | 13 deferrals confirmed (repeat skips with a reason), v1 published |
| 5 | Store OUT054 | ❌ Fail | Notice exists (si, S1-058, `LOWER_PRIORITY`) but the notice screen crashes: `RangeError: Invalid time value` (bug B1) |
| 6 | Loader | ⏭ UI skipped · API stand-in ✅ | Loader screens pending Dev 3. `shortfall_reported` via `/sync` as loader.dock2: S1-005 missing 2 of 42 on VEH036 T2 → trip on hold |
| 7 | Dispatcher | ⚠️ Pass with deviation | D6 offered **only B** (recommended, "Hold van ~25 min for re-pick") **and C** ("Send 40, move 2 to Wed", flagged "Breaks OUT003's rule"). **No option A** (bug B3). Applied B → **v2 published** |
| 8 | Loader | ⏭ UI skipped · API stand-in ✅ | `trip_acknowledged` on v2 as loader.dock2 → hold released |
| 9 | Driver VEH036 | ✅ Pass | "Plan changed to v2" banner · acknowledged v2 · OUT001 = T1 stop 1, store note shown first, plan + likely clocks · OUT003 = T2 stop 1 · both records uploaded |
| 10 | Store OUT001 | ✅ Pass | Driver evidence 80 cases → store counted 77; report: yoghurt ×2, fish ×1 → `store_report` |
| 11 | Dispatcher | ✅ Pass | Store report reached from Live ops → **Redeliver** → "Decision recorded · redeliver". Exceptions list shows duplicates (bug B4) |
| 12 | Driver VEH007 | ❌ Fail (test race, fixed) | Offline record of 205 saved ("Saved on this phone"), but the test recorded before acknowledging v2 → rejected BR-32 on sync. The rejection is shown with conflict copy (bug B5) |
| 13 | Store OUT074 → driver | ◐ Partial | Store confirmed **200 cases** (S1-083, 205 delivered) while the driver was offline ✅; driver half blocked by step 12 |
| 14 | Dispatcher | ⏭ Blocked | No count conflict without step 13; re-run after the 23:05 reset |

## Bugs filed

| ID | Step | Owner | Summary |
|---|---|---|---|
| B1 | 5 | Lead | Notice page crash: `next_run` stored as `str(datetime)` (`planning/service.py:518`), store UI appends a time to it (`store/api.ts:94`) |
| B2 | 5 | Lead | Notice body shows raw `2026-04-07 22:00:00+00:00` |
| B3 | 7 | Dev 2 | D6 offers no option A (move 2 to the other trip); docs/09 step 7 cannot be shown as written |
| B4 | 11 | Dev 2 | Every late-risk / pending-sync exception listed twice in `/exceptions` and Live ops |
| B5 | 12 | Lead | Driver can record before acknowledging; a BR-32 rejection is shown as "Your count and the store's differ" |
| F1 | 2 | Dev 2 | docs/09 step 2 numbers (VEH036 "1,096 kg > 1,040 kg", OUT003 on T1) differ from the live plan; explanation text says "greedy plan" on a CP-SAT FEASIBLE result |

## Test fixes in this branch

- Sessions from captured `storageState`; API calls reuse the session token (no passwords in the run).
- Fleet label is "Switched off · No driver"; wait for the plan to load before choosing Generate / Re-run.
- D6 takes A when offered, otherwise the engine's recommendation (logged).
- Report-problem row and Live-ops cards matched by their real text (`S1-001`, not `OUT001`).
- Driver offline step waits for the acknowledgement to upload before going offline.
- Headed Edge fallback + keeper window for the capture script (bundled headed Chromium fails to spawn on this laptop).

**Pass 2 (full four-role, after the 23:05 deploy)** — pending.
