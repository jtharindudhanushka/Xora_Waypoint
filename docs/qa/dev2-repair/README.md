# D6 visual and interaction checks

[shortfall.png](shortfall.png) compares Figma **156:283** (left) and the application
(right), each at 1440 × 900. The app uses original synthetic test identifiers and
illustrative quantities, never competition-data output.

Checked against the frame and its rationale: 56 px app bar with Live ops active,
64 px hold strip, waiting and departure clocks, heading, 480 px report pane,
standing store rule above the option matrix, 130 px labels, 96 px option headings,
56 px effect rows, selected orange rule and radio, recommended marker, store-rule
conflict marker, and 72 px publish footer. The app uses the existing design tokens,
IBM Plex Sans/Mono, Button primitive and exported Figma icons.

Approved departures: actual likely arrival-window changes replace uncalibrated
probabilities (DEP-5); Call the dock is visible and disabled because no phone
number is supplied (DEP-7). All live values and recommendations come from the API.

`apps/web/scripts/verify-repair.cjs` captures the synthetic comparison and verifies
that recommendation never applies automatically, changing the selection changes
the publish action, and applying the chosen option navigates to the revised plan.
Unit tests also cover no feasible options. Loading and API errors have visible
states. Backend tests verify conservation, hard rules, store rules, stale quotes,
unchanged published v1, linked top-up, v2 publication, scoped SSE, and active hold.

The shared dispatcher bar was corrected to the frame's nav padding, depot type
and user type; the four planning comparisons were refreshed after that correction.
