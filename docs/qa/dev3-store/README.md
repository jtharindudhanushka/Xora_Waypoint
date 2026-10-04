# Store fidelity review · 390 × 844

Figma frames and rationale texts were read through the connector before implementation:
S1 `152:2` / `152:108`; S2 `276:3245` / `152:218`; S5 `153:138` /
`153:263`; S6 `204:110` / `204:182`; S8 `153:52` / `153:137`.
The reference is left and the running app is right in each comparison.
All app screenshots use original synthetic fixtures; no competition data or derivatives
are included. Illustrated quantities, dates and identifiers are fixture values.

| Screen | Comparison | Result |
|---|---|---|
| S1 home + tracking | [s1.png](s1.png) | Section order, per-van tracking, tokens, type, notes, recent receipts and bottom navigation reviewed |
| S2 new order | [s2.png](s2.png) | Item removal, warning/Use 20, type selector, counts and 56 px action reviewed |
| S5 confirm receipt | [s5.png](s5.png) | Driver evidence, separate counts, spacing and actions reviewed |
| S6 report a problem | [s6.png](s6.png) | Per-line summary, 77 good cases from API preview, and report action reviewed; photo input decision pending |
| S8 deferral notice | [s8.png](s8.png) | Reason, next date, protection, language controls and actions reviewed; dispatch contact decision pending |

## docs/13 checklist

- [x] Supplied-frame headings, labels, helpers and button copy reviewed; real values come from API.
- [x] Sections and spacing reviewed at 390 × 844 against the exported frames.
- [x] Colours use shared tokens; no raw hex in Store CSS.
- [x] IBM Plex Sans/Mono and supplied Figma SVG assets used.
- [x] StatusBadge and BR-54 vocabulary reused.
- [x] Loading, empty, error/retry and offline states implemented and exercised.
- [x] Five side-by-side comparisons linked from the UI PR.
- [x] Production pages use the generated API client; fixtures exist only in the QA runner.
- [ ] S8 Call dispatch: supply `VITE_DISPATCH_PHONE` or approve an unavailable demo action.
- [ ] S6: approve URL-based photo evidence or specify a binary upload destination.

The unresolved interactions are recorded under pending Store fidelity decisions in
[02-business-rules](../../02-business-rules.md). This review does not claim exact
fidelity approval while those decisions are outstanding. Native-speaker review of
Sinhala/Tamil reason templates and live Docker integration are also outstanding.

## Reproduce the synthetic browser check

Start `npm run dev` in `apps/web`. With Playwright and an installed browser:

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/playwright PLAYWRIGHT_CHANNEL=msedge \
  node apps/web/scripts/verify-store.cjs
```

`STORE_QA_URL` defaults to `http://127.0.0.1:5173`. A locally installed `playwright`
module can be used without `PLAYWRIGHT_MODULE`; default browser channel is Chrome.
The runner writes screenshots under `.venv/store-design/` (ignored). It checks item
removal, the explicit keep-quantity gate, correction to usual quantity, failed submit
retry retaining the request ID, receipt count changes, two-line damage/missing report,
notice acknowledgement, loading, empty, failure/retry and offline submission controls.
This is a deterministic mocked-API browser check, separate from the live walkthrough.
