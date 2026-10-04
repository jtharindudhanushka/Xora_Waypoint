/** Live docs/09 smoke. Requires a freshly seeded disposable Compose demo.
 * No mocked routes, direct SQL, competition data exports or committed artifacts.
 */
const { test, expect } = require(
  process.env.PLAYWRIGHT_TEST_MODULE || "@playwright/test",
);

const password = process.env.WALKTHROUGH_PASSWORD || "demo1234";
async function signIn(page, email, destination) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(destination));
}
async function dispatcherClock(request, now) {
  const signed = await request.post("/api/v1/auth/login", {
    data: { email: "dispatch.peliyagoda@waypoint.demo", password },
  });
  expect(signed.status(), "Dispatcher demo account must be seeded").toBe(200);
  const session = await signed.json();
  const result = await request.put("/api/v1/clock", {
    headers: { Authorization: `Bearer ${session.access_token}` },
    data: { demo_now: now },
  });
  expect(result.status(), "Demo clock must be enabled (BR-56)").toBe(200);
}
async function storeToken(request, email) {
  const signed = await request.post("/api/v1/auth/login", {
    data: { email, password },
  });
  expect(signed.status()).toBe(200);
  return { Authorization: `Bearer ${(await signed.json()).access_token}` };
}

test.describe.serial("docs/09: Store first, then merged role coverage", () => {
  test("step 1: S1-001 correction and submission (BR-40/42)", async ({
    page,
    request,
  }) => {
    await dispatcherClock(request, "2026-04-06T14:50:00+05:30");
    const headers = await storeToken(request, "store.out001@waypoint.demo");
    const draft = await request.get("/api/v1/orders/S1-001", { headers });
    expect(
      draft.status(),
      "Merge Store API and UI before running this smoke",
    ).toBe(200);
    expect(
      (await draft.json()).submission_status,
      "Reset demo before repeating this test",
    ).toBe("draft");
    await signIn(page, "store.out001@waypoint.demo", "/store");
    await page.getByRole("button", { name: /New order for/ }).click();
    await page.getByRole("button", { name: "Use 20", exact: true }).click();
    await expect(page.getByLabel("Set yoghurt 1 kg cases")).toHaveValue("20");
    await page
      .getByRole("button", { name: "Review order", exact: true })
      .click();
    const submitted = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/orders") && r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Submit order", exact: true })
      .click();
    expect((await submitted).status()).toBe(200);
    await expect(page).toHaveURL(/\/store$/);
    const saved = await request.get("/api/v1/orders/S1-001", { headers });
    const order = await saved.json();
    expect(order.submission_status).toBe("placed");
    expect(order.units).toBe(80);
    expect(order.delivery_date).toBe("2026-04-07");
  });

  test("steps 2–4: generate, fleet, deferrals and publish", async ({
    page,
    request,
  }) => {
    await dispatcherClock(request, "2026-04-06T16:05:00+05:30");
    await page.setViewportSize({ width: 1440, height: 900 });
    await signIn(page, "dispatch.peliyagoda@waypoint.demo", "/dispatch/plan");
    await page
      .getByRole("button", { name: "Generate plan", exact: true })
      .click();
    await page.getByRole("button", { name: /^Fleet/ }).click();
    await expect(
      page.getByText("VEH038", { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page.getByText("No driver", { exact: true }).first(),
    ).toBeVisible();
    await page.getByRole("button", { name: /^Deferred/ }).click();
    for (const input of await page
      .getByLabel("Reason for another deferral")
      .all()) {
      await input.fill(
        "Smoke demo: dispatcher reviewed peak-day capacity and next-run priority.",
      );
    }
    for (const box of await page
      .getByRole("checkbox", { name: /^Confirm S1-/ })
      .all()) {
      if (await box.isEnabled()) await box.check();
    }
    const confirm = page.getByRole("button", {
      name: /^Confirm \d+ deferrals$/,
    });
    if (await confirm.isEnabled()) {
      const confirmed = page.waitForResponse(
        (r) =>
          r.url().endsWith("/deferrals/confirm") &&
          r.request().method() === "POST",
      );
      await confirm.click();
      expect((await confirmed).status()).toBe(200);
    }
    await page.getByRole("button", { name: /Review & publish/ }).click();
    const publish = page
      .getByRole("dialog")
      .getByRole("button", { name: /^Publish plan v/ });
    await expect(publish).toBeEnabled();
    const published = page.waitForResponse(
      (r) => r.url().endsWith("/publish") && r.request().method() === "POST",
    );
    await publish.click();
    expect((await published).status()).toBe(200);
  });

  test("step 5: OUT054 deferral and acknowledgement (BR-41/44)", async ({
    page,
    request,
  }) => {
    await dispatcherClock(request, "2026-04-06T16:25:00+05:30");
    const headers = await storeToken(request, "store.out054@waypoint.demo");
    const result = await request.get("/api/v1/notifications", { headers });
    expect(result.status()).toBe(200);
    const notices = await result.json();
    const notice = notices.find((n) => n.kind === "deferral");
    expect(
      notice,
      "Published S1 must produce the OUT054 deferral notice",
    ).toBeTruthy();
    await signIn(page, "store.out054@waypoint.demo", "/store");
    await page.goto(`/store/notices/${notice.id}`);
    await expect(
      page.getByRole("button", { name: "Got it", exact: true }),
    ).toBeVisible();
    await expect(page.locator('[lang="si"]').first()).toBeVisible();
    await page.getByRole("button", { name: "தமிழ்", exact: true }).click();
    await expect(page.locator('[lang="ta"]').first()).toBeVisible();
    await page.getByRole("button", { name: "English", exact: true }).click();
    const acknowledged = page.waitForResponse(
      (r) => r.url().endsWith("/read") && r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Got it", exact: true }).click();
    expect((await acknowledged).status()).toBe(200);
    await expect(page).toHaveURL(/\/store$/);
  });
});

test("step 10: real driver evidence → damaged/missing report (BR-46/47)", async ({
  page,
  request,
}) => {
  test.skip(
    process.env.WALKTHROUGH_RECEIPTS !== "1",
    "Run after the lead completes driver walkthrough step 9; see docs/qa/walkthrough.md",
  );
  await dispatcherClock(request, "2026-04-07T05:40:00+05:30");
  const headers = await storeToken(request, "store.out001@waypoint.demo");
  const result = await request.get("/api/v1/orders/S1-001/receipt-draft", {
    headers,
  });
  expect(result.status()).toBe(200);
  const evidence = await result.json();
  expect(
    evidence.can_confirm,
    "Driver item counts must already be synced",
  ).toBe(true);
  expect(evidence.confirmed, "Use a fresh receipt for this phase").toBe(false);
  await signIn(page, "store.out001@waypoint.demo", "/store");
  await page.goto("/store/orders/S1-001/receipt");
  await page
    .getByRole("button", { name: "Decrease Set yoghurt 1 kg" })
    .click({ clickCount: 2 });
  await page.getByRole("button", { name: "Decrease Fish, fillet" }).click();
  await page
    .getByRole("button", { name: "Report a problem", exact: true })
    .click();
  await page.getByRole("button", { name: /Set yoghurt 1 kg/ }).click();
  await page.getByLabel("Problem", { exact: true }).selectOption("damaged");
  await page.getByRole("button", { name: "Save problem", exact: true }).click();
  const sent = page.waitForResponse(
    (r) => r.url().endsWith("/issues") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Send to dispatch", exact: true })
    .click();
  const response = await sent;
  expect(response.status()).toBe(200);
  expect((await response.json()).kind).toBe("store_report");
});

for (const role of [
  { email: "loader.dock2@waypoint.demo", route: "/dock" },
  { email: "driver.veh036@waypoint.demo", route: "/driver" },
  { email: "dispatch.peliyagoda@waypoint.demo", route: "/dispatch/ops" },
]) {
  test(`merged role landing: ${role.route}`, async ({ page }) => {
    await signIn(
      page,
      role.email,
      role.route === "/dispatch/ops" ? "/dispatch/plan" : role.route,
    );
    await page.goto(role.route);
    await expect(page.locator("h1,h2").first()).toBeVisible();
    test.skip(
      (await page.getByText("Coming next", { exact: true }).count()) > 0,
      "Role screen remains a placeholder; this is not walkthrough coverage",
    );
    await expect(page.getByRole("heading").first()).toBeVisible();
  });
}
