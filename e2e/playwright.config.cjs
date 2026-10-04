const slowMo = Number(process.env.WALKTHROUGH_SLOWMO || 0);

module.exports = {
  testDir: __dirname,
  testMatch: "walkthrough.spec.ts",
  timeout: slowMo ? 300_000 : 120_000,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.WALKTHROUGH_URL || "http://127.0.0.1:8080",
    ...(process.env.PLAYWRIGHT_CHANNEL
      ? { channel: process.env.PLAYWRIGHT_CHANNEL }
      : {}),
    ...(slowMo ? { launchOptions: { slowMo } } : {}),
    viewport: { width: 390, height: 844 },
    trace: "off",
    screenshot: "only-on-failure",
    video: "off",
  },
};
