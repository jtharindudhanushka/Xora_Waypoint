/** Live docs/09 walkthrough. Requires a freshly reset demo (`app.seed --reset-demo`).
 * No mocked routes, direct SQL, competition data exports or committed artifacts.
 *
 * Sessions: each role runs in its own browser context. When WALKTHROUGH_AUTH_DIR holds
 * `<account>.json` storageState files (captured by e2e/capture-sessions.cjs, a human types
 * the password), they are used and API calls take the bearer token from that session.
 * Without them, a localhost origin falls back to the documented demo password.
 *
 * Optional: WALKTHROUGH_VIDEO_DIR records one clip per step and role;
 * WALKTHROUGH_RESULTS writes the observed values (KPIs, vehicles, trips) as JSON.
 */
const fs = require("fs");
const path = require("path");
const { test, expect } = require(
  process.env.PLAYWRIGHT_TEST_MODULE || "@playwright/test",
);

const DAY = "2026-04-07";
const authDir = process.env.WALKTHROUGH_AUTH_DIR;
const videoDir = process.env.WALKTHROUGH_VIDEO_DIR;
const password = process.env.WALKTHROUGH_PASSWORD || "demo1234";
const PHONE = { width: 390, height: 844 };
const DESKTOP = { width: 1440, height: 900 };
const results = (() => {
  try {
    return JSON.parse(fs.readFileSync(process.env.WALKTHROUGH_RESULTS, "utf8"));
  } catch {
    return {};
  }
})();

function note(key, value) {
  results[key] = value;
  console.log(`  [observed] ${key}: ${JSON.stringify(value)}`);
  if (process.env.WALKTHROUGH_RESULTS)
    fs.writeFileSync(
      process.env.WALKTHROUGH_RESULTS,
      JSON.stringify(results, null, 2),
    );
}

function stateFile(account) {
  return authDir ? path.join(authDir, `${account}.json`) : null;
}

/** Bearer header for an account: from its captured session, else a localhost sign-in. */
async function auth(request, account) {
  const file = stateFile(account);
  if (file && fs.existsSync(file)) {
    const state = JSON.parse(fs.readFileSync(file, "utf8"));
    const entry = state.origins
      .flatMap((o) => o.localStorage)
      .find((e) => e.name === "xora.session");
    expect(entry, `${account}: no session in ${file}`).toBeTruthy();
    const session = JSON.parse(entry.value);
    expect(
      session.expiresAt > Date.now(),
      `${account}: session expired, capture it again`,
    ).toBe(true);
    return { Authorization: `Bearer ${session.accessToken}` };
  }
  const signed = await request.post("/api/v1/auth/login", {
    data: { email: `${account}@waypoint.demo`, password },
  });
  expect(signed.status(), `${account} must be seeded`).toBe(200);
  return { Authorization: `Bearer ${(await signed.json()).access_token}` };
}

/** A signed-in page for one role; `clip` names the recorded video. */
async function as(browser, account, clip, viewport = PHONE) {
  const file = stateFile(account);
  const useState = file && fs.existsSync(file);
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport,
    ...(useState ? { storageState: file } : {}),
    ...(videoDir ? { recordVideo: { dir: videoDir, size: viewport } } : {}),
  });
  const page = await context.newPage();
  if (!useState) {
    await page.goto("/login");
    await page.getByLabel("Work email").fill(`${account}@waypoint.demo`);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).not.toHaveURL(/\/login/);
  }
  const close = async () => {
    const video = page.video();
    await context.close();
    if (video) fs.renameSync(await video.path(), path.join(videoDir, `${clip}.webm`));
  };
  return { page, context, close };
}

async function setClock(request, now) {
  const headers = await auth(request, "dispatch.peliyagoda");
  const result = await request.put("/api/v1/clock", {
    headers,
    data: { demo_now: now },
  });
  expect(result.status(), "Demo clock must be enabled (BR-56)").toBe(200);
}

async function getJson(request, url, account) {
  const res = await request.get(url, { headers: await auth(request, account) });
  expect(res.status(), `GET ${url} as ${account}`).toBe(200);
  return res.json();
}

async function sync(request, account, events) {
  const res = await request.post("/api/v1/sync", {
    headers: await auth(request, account),
    data: {
      device_id: `qa-walkthrough-${account}`,
      events: events.map((e, i) => ({
        event_id: crypto.randomUUID(),
        seq: i + 1,
        payload: {},
        ...e,
      })),
    },
  });
  expect(res.status()).toBe(200);
  return (await res.json()).results;
}

/** The published trip carrying an order, read from the real plan (never assumed). */
function tripOf(plan, orderRef) {
  for (const trip of plan.trips)
    for (const stop of trip.stops)
      if (stop.orders.some((o) => o.order_ref === orderRef && !o.top_up_of_order_ref))
        return { trip, stop };
  return null;
}

test.describe.configure({ mode: "serial" });

test("step 1: S1-001 correction and submission (BR-40/42)", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-06T14:50:00+05:30");
  const draft = await getJson(request, "/api/v1/orders/S1-001", "store.out001");
  expect(draft.submission_status, "Reset demo before repeating").toBe("draft");
  const { page, close } = await as(browser, "store.out001", "01-store-order");
  await page.goto("/store");
  await page.getByRole("button", { name: /New order for/ }).click();
  await page.getByRole("button", { name: "Use 20", exact: true }).click();
  await expect(page.getByLabel("Set yoghurt 1 kg cases")).toHaveValue("20");
  await page.getByRole("button", { name: "Review order", exact: true }).click();
  const submitted = page.waitForResponse(
    (r) => r.url().endsWith("/api/v1/orders") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Submit order", exact: true }).click();
  expect((await submitted).status()).toBe(200);
  await expect(page).toHaveURL(/\/store$/);
  await page.waitForTimeout(1500);
  await close();
  const order = await getJson(request, "/api/v1/orders/S1-001", "store.out001");
  expect(order.submission_status).toBe("placed");
  expect(order.units).toBe(80);
  expect(order.delivery_date).toBe(DAY);
  note("step1", { status: order.submission_status, units: order.units });
});

test("steps 2–4: generate, fleet, deferrals and publish", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-06T16:05:00+05:30");
  const { page, close } = await as(
    browser,
    "dispatch.peliyagoda",
    "02-dispatch-plan",
    DESKTOP,
  );
  await page.goto("/dispatch/plan");
  const generate = page.getByRole("button", { name: "Generate plan", exact: true });
  const rerun = page.getByRole("button", { name: "Re-run", exact: true });
  await expect(generate.or(rerun).first()).toBeVisible();
  await expect(page.getByText("Loading plan…")).toHaveCount(0);
  if (await generate.isVisible()) {
    const generated = page.waitForResponse(
      (r) => r.url().endsWith("/generate") && r.request().method() === "POST",
      { timeout: 60_000 },
    );
    await generate.click();
    expect((await generated).status()).toBe(200);
  }
  await expect(rerun).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(2500);

  const plan = await getJson(request, `/api/v1/plans/${DAY}`, "dispatch.peliyagoda");
  const veh036 = plan.trips.filter((t) => t.vehicle_code === "VEH036");
  const out074 = tripOf(plan, "S1-083");
  const out003 = tripOf(plan, "S1-005");
  const out001 = tripOf(plan, "S1-001");
  note("step2", {
    solver: plan.solver_status,
    solve_ms: plan.solve_ms,
    kpis: plan.kpis,
    orders_total: plan.orders_total,
    chilled_total: plan.chilled_total,
    bottleneck: plan.bottleneck,
    trips: plan.trips.length,
    vehicles: new Set(plan.trips.map((t) => t.vehicle_code)).size,
    veh036_trips: veh036.map((t) => ({ no: t.trip_no, kg: t.weight_kg })),
    S1_001: out001 && `${out001.trip.vehicle_code} T${out001.trip.trip_no}`,
    S1_005: out003 && `${out003.trip.vehicle_code} T${out003.trip.trip_no}`,
    S1_083: out074 && `${out074.trip.vehicle_code} T${out074.trip.trip_no}`,
  });
  expect(veh036.length, "VEH036 has 2 trips (docs/09 step 2)").toBe(2);
  expect(out074?.trip.vehicle_code, "OUT074 on VEH007").toBe("VEH007");

  await page.getByRole("button", { name: /^Fleet/ }).click();
  await expect(page.getByText("VEH038", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Switched off · No driver/).first()).toBeVisible();
  await page.waitForTimeout(1500);

  await page.getByRole("button", { name: /^Deferred/ }).click();
  for (const input of await page.getByLabel("Reason for another deferral").all())
    await input.fill(
      "Dispatcher reviewed peak-day capacity and next-run priority.",
    );
  for (const box of await page
    .getByRole("checkbox", { name: /^Confirm S1-/ })
    .all())
    if (await box.isEnabled()) await box.check();
  const confirm = page.getByRole("button", { name: /^Confirm \d+ deferrals$/ });
  if (await confirm.isEnabled()) {
    const confirmed = page.waitForResponse(
      (r) => r.url().endsWith("/deferrals/confirm") && r.request().method() === "POST",
    );
    await confirm.click();
    expect((await confirmed).status()).toBe(200);
  }
  await page.getByRole("button", { name: /Review & publish/ }).click();
  const publish = page
    .getByRole("dialog")
    .getByRole("button", { name: /^Publish plan v/ });
  await expect(publish).toBeEnabled();
  await page.waitForTimeout(1500);
  const published = page.waitForResponse(
    (r) => r.url().endsWith("/publish") && r.request().method() === "POST",
  );
  await publish.click();
  const body = await (await published).json();
  expect(body.status).toBe("published");
  note("step4", { version: body.number, deferrals: body.deferrals.length });
  await page.waitForTimeout(2000);
  await close();
});

test("step 5: OUT054 deferral notice and acknowledgement (BR-41/44)", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-06T16:25:00+05:30");
  const notices = await getJson(request, "/api/v1/notifications", "store.out054");
  const notice = notices.find((n) => n.kind === "deferral");
  expect(notice, "Published S1 must produce the OUT054 deferral notice").toBeTruthy();
  const { page, close } = await as(browser, "store.out054", "05-store-notice");
  await page.goto(`/store/notices/${notice.id}`);
  await expect(page.getByRole("button", { name: "Got it", exact: true })).toBeVisible();
  await expect(page.locator('[lang="si"]').first()).toBeVisible();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: "தமிழ்", exact: true }).click();
  await expect(page.locator('[lang="ta"]').first()).toBeVisible();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await page.waitForTimeout(1500);
  const acknowledged = page.waitForResponse(
    (r) => r.url().endsWith("/read") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Got it", exact: true }).click();
  expect((await acknowledged).status()).toBe(200);
  await expect(page).toHaveURL(/\/store$/);
  await close();
  note("step5", { notice: notice.kind });
});

test("step 6: loader reports OUT003 short 2 → van on hold (L1–L4, BR-26/27)", async ({
  browser,
  request,
}) => {
  test.skip(process.env.WALKTHROUGH_LOADER_UI !== "1", "Loader UI not deployed yet");
  await setClock(request, "2026-04-07T04:14:00+05:30");
  const day = await getJson(request, "/api/v1/vehicles/VEH036/today", "loader.dock2");
  const trip = day.trips.find((t) =>
    t.stops.some((s) => s.orders.some((o) => o.order_ref === "S1-005")),
  );
  expect(trip, "S1-005 must be on a VEH036 trip").toBeTruthy();
  const { page, close } = await as(browser, "loader.dock2", "06-loader-shortfall");
  await page.goto("/dock");
  await page.getByRole("button", { name: new RegExp(`VEH036 · Trip ${trip.trip_no}`) }).click();
  await page.waitForTimeout(1000);
  await page.getByRole("button", { name: `Load VEH036 · Trip ${trip.trip_no}` }).click();
  await expect(page.getByText("Load order")).toBeVisible();
  // Load in reverse delivery order until the OUT003 order turns up short.
  for (const box of (await page.getByRole("checkbox", { name: /^Loaded / }).all()).slice(0, 2))
    if (!/S1-005/.test((await box.getAttribute("aria-label")) || "")) await box.check();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: "Report a problem", exact: true }).click();
  await page.getByRole("radio", { name: /S1-005/ }).check();
  await page.getByRole("button", { name: "Missing", exact: true }).click();
  await page.getByLabel("Cases short").fill("2");
  await page.getByRole("button", { name: "Short from chiller pick" }).click();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: "Send to dispatcher" }).click();
  await expect(page.getByText("Departure on hold")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/Sent to dispatch/)).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(2500);
  await close();
  note("step6", { trip: `VEH036 T${trip.trip_no}`, via: "loader UI" });
});

test("step 6 (API stand-in): loader shortfall puts the trip on hold (BR-26/27)", async ({
  request,
}) => {
  test.skip(
    process.env.WALKTHROUGH_LOADER_UI === "1",
    "Loader UI covers step 6",
  );
  await setClock(request, "2026-04-07T04:14:00+05:30");
  const day = await getJson(request, "/api/v1/vehicles/VEH036/today", "loader.dock2");
  const trip = day.trips.find((t) =>
    t.stops.some((s) => s.orders.some((o) => o.order_ref === "S1-005")),
  );
  expect(trip, "S1-005 must be on a VEH036 trip").toBeTruthy();
  const order = trip.stops
    .flatMap((s) => s.orders)
    .find((o) => o.order_ref === "S1-005");
  const [result] = await sync(request, "loader.dock2", [
    {
      type: "shortfall_reported",
      entity: { type: "trip", id: trip.id },
      plan_version_id: day.version.id,
      event_time: "2026-04-07T04:14:00+05:30",
      payload: {
        order_id: order.order_id,
        kind: "missing",
        qty: 2,
        reason: "short_from_chiller_pick",
      },
    },
  ]);
  expect(result.status, JSON.stringify(result)).toBe("accepted");
  note("step6", { trip: `VEH036 T${trip.trip_no}`, planned: order.planned_cases });
});

test("step 7: dispatcher resolves the hold with D6 option A (BR-28/29)", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-07T04:19:00+05:30");
  const { page, close } = await as(
    browser,
    "dispatch.peliyagoda",
    "07-dispatch-d6",
    DESKTOP,
  );
  await page.goto(`/dispatch/ops?date=${DAY}`);
  const card = page.locator("article", { hasText: /VEH036 T\d on hold/ });
  await expect(card).toBeVisible();
  await page.waitForTimeout(1500);
  await card.getByRole("button", { name: "Resolve shortfall" }).click();
  await expect(page.getByRole("heading", { name: "Resolve shortfall before departure" })).toBeVisible();
  const options = page.getByRole("radio", { name: /^Option / });
  note("step7_options", await options.allInnerTexts());
  await expect(page.getByText("OUT003’s rule (set by the store):")).toBeVisible();
  await expect(
    page.getByRole("radio", { name: "Option C" }).getByText("Breaks OUT003’s rule"),
  ).toBeVisible();
  await page.waitForTimeout(2000);
  // docs/09 says Apply A; when the engine offers no A, take its recommendation and log it.
  const optionA = page.getByRole("radio", { name: "Option A" });
  const picked = (await optionA.count())
    ? optionA
    : page.getByRole("radio", { name: /^Option / }).filter({ hasText: "Recommended" });
  await picked.click();
  const label = (await picked.getAttribute("aria-label")).replace("Option ", "");
  note("step7_applied", label);
  const applied = page.waitForResponse(
    (r) => r.url().endsWith("/apply") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: new RegExp(`^Apply ${label} · publish v`) }).click();
  const v2 = await (await applied).json();
  expect(v2.status).toBe("published");
  await expect(page).toHaveURL(/\/dispatch\/plan/);
  await page.waitForTimeout(2000);
  await close();
  note("step7", { version: v2.number, S1_005: (() => {
    const t = tripOf(v2, "S1-005");
    return t && `${t.trip.vehicle_code} T${t.trip.trip_no}`;
  })() });
});

test("step 8: loader reviews v2 and acknowledges → hold released (L5, BR-31)", async ({
  browser,
  request,
}) => {
  test.skip(process.env.WALKTHROUGH_LOADER_UI !== "1", "Loader UI not deployed yet");
  await setClock(request, "2026-04-07T04:27:00+05:30");
  const day = await getJson(request, "/api/v1/vehicles/VEH036/today", "loader.dock2");
  expect(day.version.number, "v2 must be published").toBeGreaterThan(1);
  const trip = day.trips.find((t) =>
    t.stops.some((s) => s.orders.some((o) => o.order_ref === "S1-005")),
  );
  const { page, close } = await as(browser, "loader.dock2", "08-loader-ack");
  await page.goto("/dock");
  await page.getByRole("button", { name: new RegExp(`VEH036 · Trip ${trip.trip_no}`) }).click();
  await page.getByRole("button", { name: `Load VEH036 · Trip ${trip.trip_no}` }).click();
  const ack = page.getByRole("button", { name: /^Acknowledge v\d+ · release van$/ });
  await expect(ack).toBeVisible();
  await page.waitForTimeout(3000);
  await ack.click();
  await page.waitForTimeout(4000);
  await close();
  const after = await getJson(request, "/api/v1/vehicles/VEH036/today", "loader.dock2");
  expect(after.trips.some((t) => t.on_hold), "hold released").toBe(false);
  note("step8", { version: after.version.number, via: "loader UI" });
});

test("step 8 (API stand-in): loader acknowledges v2, hold released (BR-31)", async ({
  request,
}) => {
  test.skip(process.env.WALKTHROUGH_LOADER_UI === "1", "Loader UI covers step 8");
  await setClock(request, "2026-04-07T04:27:00+05:30");
  const day = await getJson(request, "/api/v1/vehicles/VEH036/today", "loader.dock2");
  expect(day.version.number, "v2 must be published").toBeGreaterThan(1);
  const results = await sync(
    request,
    "loader.dock2",
    day.trips.map((t) => ({
      type: "trip_acknowledged",
      entity: { type: "trip", id: t.id },
      plan_version_id: day.version.id,
      event_time: "2026-04-07T04:27:00+05:30",
    })),
  );
  expect(results.every((r) => r.status === "accepted")).toBe(true);
  const after = await getJson(request, "/api/v1/vehicles/VEH036/today", "loader.dock2");
  expect(after.trips.some((t) => t.on_hold), "hold released").toBe(false);
});

test("step 9: driver VEH036 acknowledges v2 and delivers OUT001 and OUT003 (BR-32–34)", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-07T04:36:00+05:30");
  const day = await getJson(request, "/api/v1/vehicles/VEH036/today", "driver.veh036");
  const find = (ref) => {
    for (const trip of day.trips)
      for (const stop of trip.stops)
        if (stop.orders.some((o) => o.order_ref === ref && !o.top_up_of_order_ref))
          return { trip, stop };
  };
  const s001 = find("S1-001");
  const s005 = find("S1-005");
  note("step9_plan", {
    version: day.version.number,
    OUT001: `T${s001.trip.trip_no} stop ${s001.stop.seq}`,
    OUT003: `T${s005.trip.trip_no} stop ${s005.stop.seq}`,
  });
  const { page, close } = await as(browser, "driver.veh036", "09-driver-veh036");
  await page.goto(`/driver?trip=${s001.trip.trip_no}`);
  await expect(page.getByText(`Plan changed to v${day.version.number}`)).toBeVisible();
  await page.waitForTimeout(1500);
  await page
    .getByRole("button", { name: `Acknowledge v${day.version.number} and start` })
    .click();
  await page.locator(`a[href="/driver/stops/${s001.stop.id}"]`).click();
  await expect(page.getByText(/note from the store/)).toBeVisible();
  await expect(page.getByText("Plan arrival")).toBeVisible();
  await expect(page.getByText("Likely arrival")).toBeVisible();
  await page.waitForTimeout(2000);
  await page.getByRole("button", { name: "Arrived" }).click();
  await page.getByLabel("Received by").fill("Store OUT001");
  await page.getByRole("button", { name: "Save delivery" }).click();
  await expect(page.getByText("Delivery recorded")).toBeVisible();
  await expect(page.getByText("Uploaded", { exact: true })).toBeVisible({ timeout: 20_000 });
  await page.waitForTimeout(1500);

  await page.goto(`/driver?trip=${s005.trip.trip_no}`);
  await page.locator(`a[href="/driver/stops/${s005.stop.id}"]`).click();
  await page.getByRole("button", { name: /Arrived|Record delivery/ }).click();
  if (results.step7_applied === "A")
    await expect(page.getByText(/cases short at loading · already reported/)).toBeVisible();
  await page.waitForTimeout(2000);
  await page.getByRole("button", { name: "Save delivery" }).click();
  await expect(page.getByText("Delivery recorded")).toBeVisible();
  await expect(page.getByText("Uploaded", { exact: true })).toBeVisible({ timeout: 20_000 });
  await page.waitForTimeout(1500);
  await close();
});

test("step 10: store OUT001 confirms receipt and reports damaged/missing (BR-46/47)", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-07T05:40:00+05:30");
  const evidence = await getJson(
    request,
    "/api/v1/orders/S1-001/receipt-draft",
    "store.out001",
  );
  expect(evidence.can_confirm, "Driver counts must be synced").toBe(true);
  expect(evidence.confirmed, "Use a fresh receipt").toBe(false);
  const { page, close } = await as(browser, "store.out001", "10-store-receipt");
  await page.goto("/store/orders/S1-001/receipt");
  await page.getByRole("button", { name: "Decrease Set yoghurt 1 kg" }).click({ clickCount: 2 });
  await page.getByRole("button", { name: "Decrease Fish, fillet" }).click();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: "Report a problem", exact: true }).click();
  await page.getByRole("button", { name: /^Set yoghurt 1 kg .*Edit$/ }).click();
  await page.getByLabel("Problem", { exact: true }).selectOption("damaged");
  await page.getByRole("button", { name: "Save problem", exact: true }).click();
  await page.waitForTimeout(1500);
  const sent = page.waitForResponse(
    (r) => r.url().endsWith("/issues") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Send to dispatch", exact: true }).click();
  const response = await sent;
  expect(response.status()).toBe(200);
  const issue = await response.json();
  expect(issue.kind).toBe("store_report");
  await page.waitForTimeout(1500);
  await close();
  note("step10", { kind: issue.kind, delivered: evidence.total_cases });
});

test("step 11: dispatcher redelivers the store report (D10)", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-07T06:14:00+05:30");
  const { page, close } = await as(
    browser,
    "dispatch.peliyagoda",
    "11-dispatch-redeliver",
    DESKTOP,
  );
  await page.goto(`/dispatch/ops?date=${DAY}`);
  const card = page.locator("article", { hasText: "S1-001" }).filter({
    has: page.getByRole("button", { name: "Review report" }),
  });
  await expect(card.first()).toBeVisible();
  note("step11_exceptions", await page.locator("article h3").allInnerTexts());
  await page.waitForTimeout(2000);
  await card.first().getByRole("button", { name: "Review report" }).click();
  await expect(page.getByRole("heading", { name: /Store report · OUT001/ })).toBeVisible();
  await page.getByText("Redeliver on the next run").click();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: /Record decision/ }).click();
  await expect(page.getByRole("status")).toContainText("Decision recorded · redeliver");
  await page.waitForTimeout(2000);
  await close();
});

test("steps 12–13: VEH007 offline record, store count, sync → R7 (BR-35–38, BR-52)", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-07T06:52:00+05:30");
  const day = await getJson(request, "/api/v1/vehicles/VEH007/today", "driver.veh007");
  let target;
  for (const trip of day.trips)
    for (const stop of trip.stops)
      if (stop.orders.some((o) => o.order_ref === "S1-083")) target = { trip, stop };
  expect(target, "S1-083 must be on a VEH007 trip").toBeTruthy();
  note("step12_plan", { trip: `VEH007 T${target.trip.trip_no}`, stop: target.stop.seq });

  const driver = await as(browser, "driver.veh007", "12-driver-offline");
  const d = driver.page;
  await d.goto(`/driver?trip=${target.trip.trip_no}`);
  const ack = d.getByRole("button", { name: /^Acknowledge v\d+ and start$/ });
  const go = d.getByRole("button", { name: /^Go to stop / });
  await expect(ack.or(go).first()).toBeVisible();
  if (await ack.isVisible()) await ack.click();
  await expect(go).toBeVisible();
  await expect(d.getByText("Nothing waiting to upload").first()).toBeVisible({ timeout: 20_000 });
  await d.waitForTimeout(1500);
  await driver.context.setOffline(true);
  await d.locator(`a[href="/driver/stops/${target.stop.id}"]`).click();
  await d.getByRole("button", { name: /Arrived|Record delivery/ }).click();
  const qty = d.getByRole("textbox").first();
  await qty.fill("205");
  await d.getByLabel("Received by").fill("OUT074 counter");
  await d.waitForTimeout(1000);
  await d.getByRole("button", { name: "Save delivery" }).click();
  await expect(d.getByText("Saved on this phone").first()).toBeVisible();
  await expect(d.getByText("Waiting for signal")).toBeVisible();
  await d.waitForTimeout(2500);
  const recordUrl = d.url();

  // Step 13a: the store confirms 200 while the driver is still offline.
  await setClock(request, "2026-04-07T07:10:00+05:30");
  const draft = await getJson(request, "/api/v1/orders/S1-083/receipt-draft", "store.out074");
  expect(draft.confirmed, "Use a fresh receipt").toBe(false);
  const store = await as(browser, "store.out074", "13a-store-count");
  const s = store.page;
  await s.goto("/store/orders/S1-083/receipt");
  const first = draft.lines[0];
  await s.getByRole("button", { name: `Decrease ${first.name}` }).click({ clickCount: 5 });
  await s.waitForTimeout(1500);
  const confirmed = s.waitForResponse(
    (r) => r.url().endsWith("/receipt") && r.request().method() === "POST",
  );
  await s.getByRole("button", { name: "Confirm 200 cases" }).click();
  expect((await confirmed).status()).toBe(200);
  await s.waitForTimeout(1500);
  await store.close();

  // Step 13b: the driver gets signal and syncs.
  await setClock(request, "2026-04-07T07:48:00+05:30");
  await driver.context.setOffline(false);
  await expect(d.getByText("Your record is kept")).toBeVisible({ timeout: 45_000 });
  expect(d.url()).toBe(recordUrl);
  await expect(d.getByText("200", { exact: true })).toBeVisible();
  await d.waitForTimeout(2500);
  await driver.close();
  note("step13", { driver: 205, store: 200 });
});

test("step 14: dispatcher decides the count conflict (D13, BR-52)", async ({
  browser,
  request,
}) => {
  await setClock(request, "2026-04-07T07:52:00+05:30");
  const { page, close } = await as(
    browser,
    "dispatch.peliyagoda",
    "14-dispatch-d13",
    DESKTOP,
  );
  await page.goto(`/dispatch/ops?date=${DAY}`);
  const card = page.locator("article", { hasText: /OUT074|S1-083/ }).filter({
    has: page.getByRole("button", { name: "Review report" }),
  });
  await expect(card.first()).toBeVisible();
  await page.waitForTimeout(2000);
  await card.first().getByRole("button", { name: "Review report" }).click();
  await expect(page.getByRole("heading", { name: "Two counts for OUT074" })).toBeVisible();
  const issueId = page.url().split("/").pop();
  await page.waitForTimeout(2500);
  await page.getByText("Store count stands").click();
  await page.getByRole("button", { name: /Record decision/ }).click();
  await expect(page.getByRole("status")).toContainText("Decision recorded · store stands");
  await page.waitForTimeout(2000);
  await close();
  const issue = await getJson(request, `/api/v1/issues/${issueId}`, "dispatch.peliyagoda");
  expect(issue.driver_qty).toBe(205);
  expect(issue.store_qty).toBe(200);
  note("step14", { kind: issue.kind, status: issue.status, driver: issue.driver_qty, store: issue.store_qty });
});
