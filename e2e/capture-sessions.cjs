/** Capture demo sessions for the live walkthrough without the script ever handling a password.
 * Opens a headed browser per account at <WALKTHROUGH_URL>/login with the email pre-filled;
 * a human types the password. Once the app leaves /login and the stored session belongs to the
 * expected account, the storageState is written to WALKTHROUGH_AUTH_DIR (outside the repo).
 *
 *   WALKTHROUGH_URL=https://... node e2e/capture-sessions.cjs [account ...]
 */
const path = require("path");
const fs = require("fs");
const { chromium } = require(
  process.env.PLAYWRIGHT_TEST_MODULE || "@playwright/test",
);

const ACCOUNTS = [
  "dispatch.peliyagoda",
  "loader.dock2",
  "driver.veh036",
  "driver.veh007",
  "store.out001",
  "store.out054",
  "store.out074",
];
const baseURL = process.env.WALKTHROUGH_URL;
const authDir =
  process.env.WALKTHROUGH_AUTH_DIR ||
  path.resolve(__dirname, "..", "..", "demo-footage", "auth");

(async () => {
  if (!baseURL) throw new Error("Set WALKTHROUGH_URL");
  const wanted = process.argv.slice(2).length ? process.argv.slice(2) : ACCOUNTS;
  fs.mkdirSync(authDir, { recursive: true });
  // Headed bundled Chromium can fail to spawn on Windows; fall back to installed Edge.
  const channel = process.env.PLAYWRIGHT_CHANNEL;
  const browser = await chromium
    .launch({ headless: false, ...(channel ? { channel } : {}) })
    .catch(() => chromium.launch({ headless: false, channel: "msedge" }));
  // A branded browser exits when its last window closes; keep one blank window open.
  const keeper = await browser.newContext();
  await keeper.newPage();
  for (const account of wanted) {
    const email = `${account}@waypoint.demo`;
    const context = await browser.newContext({ baseURL });
    const page = await context.newPage();
    await page.goto("/login");
    await page.getByLabel("Work email").fill(email);
    console.log(`\n>> Sign in as ${email} in the browser window (10 min limit)…`);
    await page.waitForFunction(
      (expected) => {
        if (location.pathname.startsWith("/login")) return false;
        try {
          const s = JSON.parse(localStorage.getItem("xora.session") || "null");
          return s && s.user && s.user.email === expected;
        } catch {
          return false;
        }
      },
      email,
      { timeout: 600_000, polling: 500 },
    );
    const file = path.join(authDir, `${account}.json`);
    await context.storageState({ path: file });
    console.log(`   saved ${file} (landed on ${new URL(page.url()).pathname})`);
    await context.close();
  }
  await browser.close();
  console.log("\nAll sessions captured.");
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
