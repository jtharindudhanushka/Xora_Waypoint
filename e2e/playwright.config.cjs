module.exports = {
  testDir: __dirname,
  testMatch: "walkthrough.spec.ts",
  timeout: 60_000,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.WALKTHROUGH_URL || "http://127.0.0.1:8080",
    ...(process.env.PLAYWRIGHT_CHANNEL
      ? { channel: process.env.PLAYWRIGHT_CHANNEL }
      : {}),
    viewport: { width: 390, height: 844 },
    trace: "off",
    screenshot: "off",
    video: "off",
  },
};
