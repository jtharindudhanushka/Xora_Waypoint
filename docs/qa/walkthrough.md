# Live judge walkthrough smoke

`e2e/walkthrough.spec.ts` exercises the actual UI and API against the Compose web
origin (default `http://127.0.0.1:8080`). It uses no intercepted responses or SQL
fixtures. Run it against a disposable local demo: it changes the demo clock, submits
S1-001, confirms deferrals and publishes a plan. It never resets the demo automatically.

Merge Store API #19 and Store UI #23 first. Start the stack with the organisers'
pack kept local, following README. For a new run, reset the demo yourself:

```sh
docker compose up --build -d
docker compose exec api python -m app.seed --reset-demo
npm install --prefix /tmp/xora-walkthrough --no-save @playwright/test@1.62.1
node /tmp/xora-walkthrough/node_modules/playwright/cli.js install chromium
PLAYWRIGHT_TEST_MODULE=/tmp/xora-walkthrough/node_modules/@playwright/test \
  node /tmp/xora-walkthrough/node_modules/playwright/cli.js test \
  --config=e2e/playwright.config.cjs
```

`WALKTHROUGH_URL` changes the origin. `PLAYWRIGHT_CHANNEL=msedge` or `chrome`
uses an installed browser instead of downloaded Chromium. The test password defaults
to the documented demo password; `WALKTHROUGH_PASSWORD` overrides it. Tokens are
kept in memory, never printed or written to tracked files.

The default serial phase checks docs/09 steps 1, 2–4 and 5. The quantity correction
must persist as S1-001, 80 cases, 7 Apr; the published plan must create OUT054's
notice; language switching and acknowledgement are checked through the UI.
Fresh browser contexts isolate accounts. No screenshots, traces or videos are saved,
so the live test does not produce competition-data images for publication.

Step 10 is intentionally separate. After the lead finishes steps 6–9 and the driver's
OUT001 counts have synced, run only the receipt phase against that same demo:

```sh
WALKTHROUGH_RECEIPTS=1 \
PLAYWRIGHT_TEST_MODULE=/tmp/xora-walkthrough/node_modules/@playwright/test \
  node /tmp/xora-walkthrough/node_modules/playwright/cli.js test \
  --config=e2e/playwright.config.cjs --grep 'step 10'
```

It requires an unconfirmed receipt with actual driver item counts, changes yoghurt
and fish counts, reports two damaged yoghurt cases plus one missing fish case, and
checks creation of a `store_report`. It does not fabricate driver evidence.

The final three checks cover merged loader, driver and live-operations landing
screens. They explicitly **skip** a screen labelled “Coming next”. These are landing
smokes, not coverage of shortfall repair, offline reconciliation or all driver actions.
Use `--grep 'merged role landing'` to run them after later role PRs merge.

## Verification status

- Playwright parsed the configuration and discovered seven tests with `--list`.
- The deterministic Store browser runner on #23 passed against original synthetic
  responses; see [Store QA](dev3-store/README.md).
- This machine has no Docker executable, so the live Compose run is **unverified**.
- The smoke suite is **not wired into CI**. Run and stabilize it on a Docker host
  before enabling it there. A skipped role or receipt phase is not a completed judge step.
