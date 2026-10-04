# Dev 3 handover · 4 Oct 2026

Prepared before the **20:30 Sri Lanka feature freeze**. Internal submission target:
22:00; competition cutoff: 23:59. The lead reviews and merges, using merge commits
and retaining branches. This is an implementation handover, not a claim that the
whole four-role Docker walkthrough has passed.

## 1. PRs and merge order

| PR | Branch | Dependency | Scope | Status |
|---|---|---|---|---|
| [#19](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/19) | feat/store-api | existing main | Orders, cutoff/quantity confirmation, per-van tracking, notices, receipts and store reports | Ready; API/Web/engine/image CI green |
| [#23](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/23) | feat/store-ui | #19 | S1, S2, S5, S6, S8 and synthetic browser/fidelity evidence | Draft; all CI green; two interaction decisions pending |
| [#24](https://github.com/jtharindudhanushka/Xora_Waypoint/pull/24) | test/e2e-walkthrough | #19/#23 at runtime | Staged live judge smoke, execution instructions and this report | Draft; Playwright discovery verified; live Docker unverified |

#23 contains the API dependency while #19 remains unmerged. Rebase after preceding
merges; regenerate the contract on generated-client conflicts, never hand-merge it.
No author merges, branch deletion, attribution trailers or competition data commits.

## 2. What works and the Store demo path

1. Reset only a disposable demo. Start at Mon 6 Apr 14:50. Sign in as
   `store.out001@waypoint.demo` / `demo1234`. S1 lists drafts/recent deliveries and
   uses the API clock and ordering window.
2. **New order** opens S1-001. Seeded yoghurt is 60; the API flags **3× your usual**.
   **Use 20**, review, then submit. S1-001 becomes placed, 80 cases, Tue 7 Apr.
   Keeping 60 instead requires an explicit checkbox; the server independently enforces it.
   Item removal and addition are supported; removing items changes the submitted total.
3. Once a plan is published, S1 reads each stop/van, predicted arrival window and
   real event status. It never writes driver events. Top-up allocations remain separate.
4. After dispatcher publication, sign in as `store.out054@waypoint.demo` and open
   the delivery update. S8 reads reason, next run and priority from the notice/plan.
   Sinhala/Tamil reason templates and acknowledgement work; native review is pending.
5. After OUT001 driver evidence arrives, open `/store/orders/S1-001/receipt`.
   Driver counts remain unchanged while the Store edits its own counts. Confirm all OK,
   or decrease yoghurt by two and fish by one → **Report a problem** → edit yoghurt
   to **Damaged** → **Send to dispatch**. An open `store_report` and D10 exception are created.

Loading, empty, server failure/retry and offline controls exist. Failed order retries
reuse the same request UUID. Receipt confirmation is idempotent. Driver shortages
already excluded from delivered counts are not subtracted twice by Store reports.

## 3. Partial or not started

| Area | Exact state |
|---|---|
| S8 calling | `VITE_DISPATCH_PHONE` is read at web build time; no verified number exists. Without it the button reports that dispatch contact is unconfigured. Approval/number requested. |
| S6 photo capture | Per-line photo URLs and driver evidence links work. Binary upload/camera destination is not supplied; the current URL editor needs approval or replacement. |
| Native-language copy | Reason/protection/source templates are present; English structural labels remain; no native-speaker approval claimed. |
| Live Docker smoke | Docker executable unavailable here. No complete Compose/Postgres or four-role walkthrough claimed. |
| CI walkthrough | Deliberately not enabled; a live Docker run is required first. |
| Other roles | No driver/dock/dispatch implementation files or engine modules were changed. Their pending screens are explicit skips in the smoke suite. |

## 4. Verification results

- **53 API tests passed**, including **20 synthetic Store regression tests**.
  Ruff lint/format and mypy passed across 64 API modules.
- **10 Web tests passed**; lint, formatting, TypeScript and production PWA build passed.
- All five Store screens were exercised at **390 × 844** in a real browser against
  original synthetic responses. Checks cover item removal, explicit confirmation,
  correction, idempotent failed-send retry, count changes, two-line reports, notice
  acknowledgement, loading, empty, error recovery and disabled receipt send while offline.
- The live Playwright suite parses and discovers **seven tests**; execution against
  Docker remains unverified. Receipt phase requires real synced driver evidence.
- API and UI GitHub CI runs completed successfully, including Docker image builds.
  Building images does not establish live database or role integration.

## 5. API/contract and data integration

All Store endpoints are under `/api/v1`, authenticated with existing role/scoping
helpers. Pydantic → OpenAPI → generated TS client is preserved. No migrations added.

| Endpoint | Purpose |
|---|---|
| GET /stores/me/orders; GET /orders/{ref} | Scoped orders, ordering clock/window, status and per-van tracking |
| GET /outlets/{code}/usual-items | Catalogue and usual cases |
| POST /orders/check; POST /orders | BR-40 calendar/cutoff and BR-42 warnings/explicit confirmation; draft or new submission |
| GET /notifications; GET /notifications/{id} | Scoped notices; optional language en/si/ta |
| POST /notifications/{id}/read; /ack | Idempotent acknowledgement and append-only audit |
| GET /orders/{ref}/receipt-draft | Driver evidence, separate Store counts and receipt state |
| POST /orders/{ref}/receipt | Confirm Store counts; discrepancies create count conflicts |
| POST /orders/{ref}/issues/check; /issues | Shared server-side good-case preview and item report/exception |
| POST /stores/me/driver-note | Store access note with scoped event |

Lead sync writes `outcome_recorded`, `trip_loaded`, stop/trip projections and item
counts. Store tracking reads published plan stops plus append-only events. D10 reads
`Issue(kind=store_report)` and linked exception rows. Receipt lines retain driver and
Store counts separately. No event row is updated or deleted by Store code.

New orders use original catalogue case measurement estimates documented in ADR-0008;
review those estimates before presenting arbitrary newly added items as operationally
calibrated. The seeded S1-001 correction preserves original 80-case order weight/volume.

## 6. Figma verification and decisions

All five supplied frames and rationale nodes were read through Figma before coding.
Comparisons and the docs/13 checklist are in [docs/qa/dev3-store](qa/dev3-store/README.md)
and attached in #23. Exported SVG assets and IBM Plex Sans/Mono are used with shared
colour tokens and StatusBadge/BR-54 vocabulary. Real counts/dates may differ from
illustrative Figma values: the seeded draft includes fish and totals 120 before the
correction; the S2 reference illustrates four items totalling 112.

The two unanswered interaction decisions above are logged as **pending**, not approved
departures, in [02-business-rules](02-business-rules.md). Keep #23 draft until resolved.

## 7. Risks and the lead's next three actions

1. Review/merge #19, then decide S8 contact behaviour and S6 photo handling before
   marking #23 ready. Supply the phone at build time and rebuild the web image if used.
2. Run migrations/seed and the live smoke on a Docker host. Verify published-plan
   tracking with lead sync, partial item counts, top-ups, late uploaded records and D10.
3. Complete the driver/dock steps, run the separate receipt smoke, review translated
   copy, and update this report with real outcomes before the 22:00 submission target.

Do not enable unverified walkthrough CI just before freeze. Do not claim screenshots
with synthetic responses demonstrate real seeded cross-role integration.

## 8. Reproduce / exact commands

```sh
.venv/bin/python services/api/scripts/export_openapi.py
cd apps/web
npm run gen:api
npm exec prettier -- --write src/api/schema.d.ts
npm run lint && npm run format:check && npm run typecheck && npm test && npm run build
```

From `services/api`:

```sh
../../.venv/bin/ruff check app tests
../../.venv/bin/ruff format --check app tests
../../.venv/bin/mypy app
../../.venv/bin/pytest -q
```

Synthetic phone browser command: [Store QA](qa/dev3-store/README.md).
Compose setup, reset, live smoke and separate receipt command:
[Walkthrough QA](qa/walkthrough.md). Use a disposable local demo; no test resets it automatically.
