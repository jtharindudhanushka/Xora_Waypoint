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

## Pass 2 · full four-role walkthrough (recorded)

2026-10-04 23:11–23:14 SLST, after the 23:04 deploy (loader UI #33, D6 fix #29, R7 store-first
fix #31) and `--reset-demo`; all 7 sessions re-captured by a human. Run with loader UI steps on
(`WALKTHROUGH_LOADER_UI=1`), so the API stand-ins were skipped. **10 passed · 1 failed · 2 skipped (stand-ins).**
This run is the demo footage.

| # | Who | Result | Real values |
|---|---|---|---|
| 1 | Store OUT001 | ✅ | S1-001 `placed`, 80 units, 2026-04-07 |
| 2 | Dispatcher | ✅ | Solver `FEASIBLE` in 12.8 s · **72 / 85 served · 14 / 26 chilled** · 20 at risk · 13 deferrals · value 955.2 · reefer 102.5 / 172.4 m³ · **27 trips on 15 vehicles** · limit: reefer trip slots 7 / 8. VEH036: **2 trips** (T1 766.7 kg, T2 713.9 kg). S1-001 → VEH036 T1 · **S1-005/OUT003 → VEH036 T1** · S1-083/OUT074 → **VEH007 T2** |
| 3 | Dispatcher | ✅ | VEH038 "Switched off · No driver" |
| 4 | Dispatcher | ✅ | 13 deferrals confirmed, **v1 published** |
| 5 | Store OUT054 | ❌ | **No deferral notice**: OUT054 is served (VEH006 T1) in this plan. Deferred outlets: OUT002, 009, 013, 030, 043, 044, 046, 060, 062, 065, 066, 067, 070 — none has a demo account (bug B6) |
| 6 | Loader (UI) | ✅ | Dock 2 → VEH036 T1 → load → Report a problem: S1-005 missing 2, short from chiller pick → **Departure on hold** |
| 7 | Dispatcher | ✅ | D6 offered **A (recommended) "Send 40 now, 2 more on Trip 2 this morning"**, B "Hold van ~25 min for re-pick", C "Send 40, move 2 to Wed" (**Breaks OUT003's rule**). Applied A → **v2 published** |
| 8 | Loader (UI) | ✅ | Reviewed v2 → "Acknowledge v2 · release van" → hold released |
| 9 | Driver VEH036 | ✅ | "Plan changed to v2" → acknowledged · OUT001 = T1 stop 1 (store note first, plan + likely clocks) · OUT003 = T1 stop 2 with the loading shortfall pre-filled and locked · both uploaded |
| 10 | Store OUT001 | ✅ | Driver evidence 80 cases; store report (yoghurt, fish) → `store_report` |
| 11 | Dispatcher | ✅ | Store report from Live ops → **Redeliver** → "Decision recorded · redeliver" |
| 12 | Driver VEH007 | ✅ | VEH007 T2 stop 1 OUT074, offline: 205 cases → "Saved on this phone · Waiting for signal" |
| 13 | Store OUT074 → driver | ✅ | Store confirmed **200** while the driver was offline; driver back online → sync → **R7 "Your record is kept"** (205 vs 200) |
| 14 | Dispatcher | ✅ | **D13** "Two counts for OUT074" → Store count stands → `count_conflict` resolved; both records kept (driver 205, store 200) |

### New / still open after pass 2

| ID | Step | Owner | Status |
|---|---|---|---|
| B6 | 5 | Dev 2 | New: plan serves OUT054, so the docs/09 deferral-notice story has no account to show it |
| B1/B2 | 5 | Lead | Not re-verifiable this pass (no notice exists) |
| B3 | 7 | Dev 2 | **Fixed** — option A offered and recommended |
| B4 | 11 | Dev 2 | Not re-checked via API this pass; Live ops list showed no duplicates in the visible cards |
| B5 | 12 | Lead | Not hit (test acknowledges first) |
| F1 | 2 | Dev 2 | docs/09 numbers still differ (VEH036 766.7 / 713.9 kg; 14 / 26 chilled) |

## Post-submission QA pass (2026-10-05, branch `fix/post-submission-qa`)

Static and unit checks on `main` @ d7e374d, then read-only probes of the live deployment
(no demo reset, no writes).

| Check | Result |
|---|---|
| Web: `tsc -b`, oxlint, prettier, vitest | ✅ clean · 10 / 10 tests (3 lint warnings: fast-refresh exports) |
| Engine: pytest | ✅ 145 passed |
| API: pytest (SQLite) | ✅ all passed (+1 new regression test) |
| ruff check / format | ❌ → ✅ 2 E501 + 1 format issue in `scripts/hooks/check_commit_msg.py` fixed |
| Live auth/scope | ✅ store → dispatcher endpoints 403 · driver → other vehicle 403 · store → clock 403 · no token 401 |
| Live security headers | ✅ HSTS, nosniff, Referrer-Policy (no CSP / X-Frame-Options — noted, not changed) |
| Live crawl, every role route at 390 / 1440 | ✅ no crashes, no horizontal scroll |

| ID | Owner area | Finding | Status |
|---|---|---|---|
| B4 | ops | `GET /exceptions` kept open `late_risk`/`pending_sync` items for stop rows replaced by a newer version (live: 42 items, 19 titles duplicated). Live ops itself was filtered and unaffected | **Fixed** (`refresh()` resolves superseded-version stop exceptions) + regression test that fails without the fix |
| F1 | engine | Bottleneck explanation said "greedy plan" on CP-SAT results | **Fixed** (solver-neutral text) |
| Q1 | dock | Unknown trip while online showed "Connect to download this trip" and polled every 5 s forever | **Fixed** (server message shown, polling stops on server errors; offline path unchanged — verified in a browser against the live API) |
| Q2 | docs | README "limit: reefer space" and docs/09 "1,096 kg > 1,040 kg" contradicted both live runs (reefer trip slots; ~767 / 714 kg) | **Fixed** |
| Q3 | dispatcher | "Outlook" nav item has no route and silently lands on Plan | Open — Figma shell item; needs a product decision (hide, disable or build) |
| Q5 | sync | Malformed driver payloads (non-list `orders`, non-object lines) returned **500**, so the phone kept the batch queued and retried forever; boolean / 10¹² case counts and a non-integer `cases_handed_over` were **accepted** and the latter would later break the store receipt draft (`int()`). Boolean shortfall `qty` passed as 1 | **Fixed** + 11 regression tests (fail without the fix) |
| Q6 | auth/config | Default `jwt_secret` placeholder was accepted with `ENVIRONMENT=production` | **Fixed**: API refuses to start in production with a placeholder or < 32-char secret (**check the VM `.env` before deploying**) + tests |
| Q4 | deploy | No Content-Security-Policy / X-Frame-Options headers | Open — low risk, deploy config |

Not re-run: the full write walkthrough (needs a `--reset-demo`); fixes above are not deployed.
