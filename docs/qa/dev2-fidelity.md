# Dispatcher fidelity review — task 2.9

Reviewed the frame geometry, copy, tokens, states and rationale against 1440 × 900 browser captures. Each comparison puts Figma on the left and the application on the right. Browser fixtures use synthetic identifiers and quantities; displayed operational data is expected to differ from the illustrative Figma data.

| Screen | Frame | Comparison | Result |
|---|---|---|---|
| D1 / trip panel | 196:383 | [Timeline](dev2-planning/timeline.png) | Corrected bar label placement, selected border, legend order and markers, panel line heights, capacity track and rule emphasis |
| D3 Deferred | 197:440 | [Deferred](dev2-planning/deferred.png) | Corrected checkbox primitive, group/row typography, next-run spacing and notice caption outside the bordered preview |
| Fleet | 198:274 | [Fleet](dev2-planning/fleet.png) | Corrected plain status text, monospace figures, caption sizes and fuel meter tokens |
| D4 Publish | 197:682 | [Publish](dev2-planning/publish.png) | Corrected check/warning icon spacing; gates and warnings remain functional |
| D6 Shortfall | 156:283 | [Shortfall](dev2-repair/shortfall.png) | Recommendation, explicit selection and publication navigation verified |
| D5 Live operations | 157:322 | [Live operations](dev2-ops/live-ops.png) | Exception cards, trip chains, pending-sync state and actions reviewed |
| D10 Store report | 250:409 | [Store report](dev2-issues/store-report.png) | Item/photo comparison, decision panel and required rejection reason verified |
| D13 Offline reconciliation | 201:307 | [Count conflict](dev2-issues/count-conflict.png) | Original counts/timestamps, decision options and confirmation reviewed |

Existing approved departures remain: disabled trip editing and Orders tab; real arrival windows/counts instead of unsupported probabilities; English-only notices; disabled dock call without a number; loading-team notification wording until the lead connects the damaged-stock note to the pick-note view. See the departure register in [business rules](../02-business-rules.md). The fidelity pass introduces no new departure.

Checks: web typecheck, lint, 10 tests and production build passed. All eight captures completed without browser page errors. Planning and repair checks are reproducible with `apps/web/scripts/verify-planning.cjs` and `verify-repair.cjs` against the development server; D5/D10/D13 captures use synthetic API responses. These are visual/interaction checks, not a claim that the lead's field applications have been integrated end to end.
