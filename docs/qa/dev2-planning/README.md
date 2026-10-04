# Dispatcher planning visual checks

Each PNG places the original Figma frame on the left and the application on the right,
both at 1440 × 900. The application uses **original synthetic fixtures**; these images
contain no competition-data output. The references are the submitted Figma designs.

| View | Figma node | Comparison |
|---|---|---|
| Timeline | 196:383 | [timeline.png](timeline.png) |
| Deferred | 197:440 | [deferred.png](deferred.png) |
| Fleet | 198:274 | [fleet.png](fleet.png) |
| Publish | 197:682 | [publish.png](publish.png) |

Checked: section order, 56 px app bar, 100 px tab strip, timeline ruler/64 px vehicle
rows, 380 px trip panel, capacity meters, stop rows, rule banner, 560 px publish
dialog at y=180, tokens, exported icons, IBM Plex Sans/Mono and button dimensions.
Business values and synthetic identifiers differ intentionally. Real S1 values come
from the API. Fleet shows featured vehicles with the remaining fleet expandable;
the deferred list scrolls when more orders are returned. Selecting a choice reveals
its Serve instead action and engine displacement preview.

Approved departures DEP-3–6 are recorded in `docs/02-business-rules.md`: editing
and Orders disabled; no invented late probability; English-only notices. The API
supplies notice copy and capacity violations. No business rule is implemented only
in the browser. Loading, empty and API error states are included.

Verification: engine 55 tests; API 24 synthetic tests; web 7 tests, lint, formatting,
types and build. Headless Edge captured all four screens without page errors.
Interactions cover repeat-skip reasons, hard publish gates and workshop switching.

To reproduce the application captures, start the web preview on port 5173, install
Playwright in a separate QA environment with Edge available, and run from repo root:
`node apps/web/scripts/verify-planning.cjs`. Set `PLAYWRIGHT_MODULE` to the installed
Playwright module path when it is outside the repo. Captures remain in ignored
`.venv/ui-*.png`; route interception supplies the committed synthetic fixture and
does not need a dataset or running API.
