const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = path.resolve(__dirname, '../../..')
const ids = ['milk-1l', 'yoghurt-1kg', 'butter-200g', 'chicken-whole', 'fish-fillet']
const names = [
  'Fresh milk 1 L',
  'Set yoghurt 1 kg',
  'Butter 200 g',
  'Chicken, whole',
  'Fish, fillet',
]
const qty = [24, 20, 12, 16, 8]
const lines = ids.map((product_id, i) => ({
  id: `00000000-0000-4000-8000-00000000000${i}`,
  product_id,
  name: names[i],
  qty_ordered: qty[i],
  qty_delivered: qty[i],
  qty_received: null,
}))
const track = {
  stop_id: '00000000-0000-4000-8000-000000000021',
  stop_seq: 1,
  stop_count: 2,
  vehicle_code: 'VEH036',
  trip_no: 1,
  version: 2,
  planned_cases: 80,
  plan_arrival: '05:10:00',
  likely_from: '05:15:00',
  likely_to: '05:35:00',
  status: 'in_transit',
  basis: 'based on past runs',
  event_time: '2026-04-07T05:02:00+05:30',
  received_at: '2026-04-07T05:02:00+05:30',
}
const order = {
  ref: 'S1-001',
  outlet_code: 'OUT001',
  brand: 'Fresh',
  district: 'Colombo',
  temp_requirement: 'chilled',
  delivery_date: '2026-04-07',
  units: 80,
  status: 'in_transit',
  submission_status: 'planned',
  placed_at: '2026-04-06T14:50:00+05:30',
  receipt_confirmed: false,
  lines,
  tracking: [track],
}
const ordering = {
  warnings: [],
  delivery_date: '2026-04-08',
  cutoff_at: '2026-04-07T16:00:00+05:30',
  cutoff_seconds: 39480,
  after_cutoff: false,
}
const home = {
  outlet_code: 'OUT001',
  district: 'Colombo',
  brand: 'Fresh',
  now: '2026-04-07T05:02:00+05:30',
  ordering,
  window_open: '05:00:00',
  window_close: '07:30:00',
  orders: [
    order,
    {
      ...order,
      ref: 'S1-000',
      temp_requirement: 'ambient',
      units: 12,
      status: 'loaded',
      tracking: [
        {
          ...track,
          vehicle_code: 'VEH037',
          planned_cases: 12,
          likely_from: '05:20:00',
          likely_to: '05:45:00',
          status: 'loaded',
        },
      ],
    },
    {
      ...order,
      ref: 'TEST-RECENT',
      delivery_date: '2026-04-06',
      units: 46,
      status: 'delivered',
      receipt_confirmed: true,
      receipt_confirmed_at: '2026-04-06T06:10:00+05:30',
    },
    {
      ...order,
      ref: 'TEST-RECENT-2',
      delivery_date: '2026-04-06',
      units: 46,
      status: 'delivered',
      receipt_confirmed: true,
      receipt_confirmed_at: '2026-04-06T06:10:00+05:30',
    },
  ],
  driver_note: {
    text: 'Front shutter shut till 07:00 · unload at the side lane',
    sent_at: '2026-04-07T04:50:00+05:30',
  },
}
const draft = {
  order_ref: 'S1-001',
  outlet_code: 'OUT001',
  temp_requirement: 'chilled',
  vehicle_code: 'VEH036',
  delivered_at: '2026-04-07T05:31:00+05:30',
  receiver: 'N. Perera',
  photo_url: '/figma/store/test-photo.svg',
  driver_event_id: '05120000-0000-4000-8000-000000000051',
  can_confirm: true,
  confirmed: false,
  total_cases: 80,
  lines: lines.map((l) => ({
    order_line_id: l.id,
    product_id: l.product_id,
    name: l.name,
    ordered_qty: l.qty_ordered,
    driver_qty: l.qty_delivered,
    store_qty: l.qty_delivered,
  })),
}
const items = ids.map((product_id, i) => ({
  product_id,
  name: names[i],
  is_chilled: true,
  usual_qty: qty[i],
}))
const notice = {
  id: '00000000-0000-4000-8000-000000000081',
  kind: 'deferral',
  order_ref: 'S1-058',
  reason_code: 'NO_REEFER_CAPACITY',
  lang: 'en',
  title: 'Delivery update',
  body: 'Refrigerated trucks are full on Tuesday, the peak before New Year. Your order (16.5 m³) needs most of a truck, so we moved it whole instead of splitting it.',
  next_run: '2026-04-08T05:00:00+05:30',
  created_at: '2026-04-06T16:25:00+05:30',
  acked_at: null,
  source: 'Written from the plan',
  protection: 'First in line (moved once)',
}

;(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
  })
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
  })
  const errors = []
  const sent = []
  let holdHome = false
  let releaseHome
  let failOrderOnce = false
  let screen = 'home'
  let failing = false
  let empty = false
  page.on('pageerror', (e) => errors.push(e.message))
  await page.addInitScript(() =>
    localStorage.setItem(
      'xora.session',
      JSON.stringify({
        accessToken: 'synthetic',
        expiresAt: 1999999999999,
        user: {
          id: 'test',
          name: 'N. Perera',
          role: 'store_manager',
          depot: null,
          dock: null,
          vehicle_code: null,
          outlet_code: 'OUT001',
          email: 'synthetic@example.test',
        },
      }),
    ),
  )
  await page.route('**/figma/store/test-photo.svg', (route) =>
    route.fulfill({
      path: path.join(root, 'apps/web/public/figma/store/a9c0e.svg'),
      contentType: 'image/svg+xml',
    }),
  )
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const method = route.request().method()
    let body = home
    const now =
      screen === 'new'
        ? '2026-04-06T14:50:00+05:30'
        : screen === 'receipt'
          ? '2026-04-07T05:40:00+05:30'
          : screen === 'issue'
            ? '2026-04-07T05:44:00+05:30'
            : screen === 'notice'
              ? '2026-04-06T16:25:00+05:30'
              : home.now
    if (failing && url.pathname.endsWith('/stores/me/orders'))
      return route.fulfill({
        status: 503,
        contentType: 'application/problem+json',
        body: JSON.stringify({ detail: 'Store temporarily unavailable' }),
      })
    if (url.pathname.endsWith('/clock')) body = { now, is_demo: true }
    if (url.pathname.endsWith('/stores/me/orders')) {
      if (holdHome)
        await new Promise((resolve) => {
          releaseHome = resolve
        })
      body = JSON.parse(JSON.stringify(home))
      body.now = now
      if (empty) body.orders = []
      if (screen === 'new') {
        body.ordering = { ...ordering, delivery_date: '2026-04-07', cutoff_seconds: 4200 }
        body.orders = [
          {
            ...order,
            submission_status: 'draft',
            lines: lines
              .slice(0, 4)
              .map((l, i) => ({ ...l, qty_ordered: i === 1 ? 60 : l.qty_ordered })),
          },
        ]
      }
      if (screen === 'notice') {
        body.outlet_code = 'OUT054'
        body.district = 'Galle'
        body.orders = [
          { ...order, ref: 'S1-058', outlet_code: 'OUT054', units: 10, status: 'deferred' },
          { ...order, ref: 'S1-057', temp_requirement: 'ambient', outlet_code: 'OUT054' },
        ]
      }
    }
    if (url.pathname.endsWith('/usual-items')) body = items
    if (url.pathname.endsWith('/receipt-draft')) body = draft
    if (url.pathname.endsWith('/notifications')) body = []
    if (url.pathname.includes('/notifications/')) body = notice
    if (url.pathname.endsWith('/orders/check')) {
      const request = route.request().postDataJSON()
      body = {
        ...ordering,
        delivery_date: '2026-04-07',
        cutoff_seconds: 4200,
        warnings: request.lines
          .filter((l) => l.product_id === 'yoghurt-1kg' && l.qty >= 60)
          .map((l) => ({
            product_id: l.product_id,
            qty: l.qty,
            usual_qty: 20,
            message: '3× your usual. Did you mean 20?',
            rule_id: 'BR-42',
          })),
      }
    } else if (url.pathname.endsWith('/issues/check')) {
      body = { good_cases: 77 }
    } else if (method === 'POST') {
      sent.push({
        path: url.pathname,
        body: route.request().postData() ? route.request().postDataJSON() : null,
      })
      if (url.pathname.endsWith('/orders') && failOrderOnce) {
        failOrderOnce = false
        return route.fulfill({
          status: 503,
          contentType: 'application/problem+json',
          body: JSON.stringify({ detail: 'Try sending again' }),
        })
      }
      body = url.pathname.endsWith('/orders')
        ? [order]
        : {
            id: 'test',
            receipt_id: 'receipt',
            order_ref: 'S1-001',
            total_cases: 80,
            status: 'open',
          }
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
  })
  const base = process.env.STORE_QA_URL || 'http://127.0.0.1:5173'
  async function go(name, url) {
    screen = name
    await page.goto(base + url)
    await page.evaluate(() => document.fonts.ready)
  }
  async function capture(name) {
    await page.mouse.move(0, 0)
    await page.screenshot({
      animations: 'disabled',
      path: path.join(root, `.venv/store-design/app-${name}.png`),
    })
  }
  await go('home', '/store')
  await page.getByRole('heading', { name: 'Arriving 05:15–05:35' }).waitFor()
  await capture('s1')
  await go('new', '/store/orders/new')
  await page.getByRole('button', { name: 'Use 20' }).waitFor()
  await page.getByRole('button', { name: 'Review order' }).click({ trial: true })
  await capture('s2')
  await page.getByRole('button', { name: 'Review order' }).click()
  assert(await page.getByRole('button', { name: 'Submit order' }).isDisabled())
  await page.getByLabel('Keep this quantity').check()
  assert(await page.getByRole('button', { name: 'Submit order' }).isEnabled())
  await page.getByRole('button', { name: 'Back', exact: true }).last().click()
  await page.getByRole('button', { name: 'Remove Butter 200 g' }).click()
  await assert.rejects(() =>
    page.getByRole('button', { name: 'Remove Butter 200 g' }).waitFor({ timeout: 500 }),
  )
  await page.getByRole('button', { name: 'Use 20' }).click()
  await page.getByRole('button', { name: 'Review order' }).click()
  failOrderOnce = true
  await page.getByRole('button', { name: 'Submit order' }).click()
  await page.getByRole('dialog').getByText('Try sending again').waitFor()
  await page.getByRole('button', { name: 'Submit order' }).click()
  await page.waitForURL('**/store')
  const retries = sent.filter((x) => x.path.endsWith('/orders'))
  assert.equal(retries.length, 2)
  assert.deepEqual(retries[0].body, retries[1].body)
  const submitted = sent.find((x) => x.path.endsWith('/orders'))
  assert.equal(submitted.body.draft_ref, 'S1-001')
  assert.equal(submitted.body.lines.find((l) => l.product_id === 'yoghurt-1kg').qty, 20)
  assert.equal(
    submitted.body.lines.some((l) => l.product_id === 'butter-200g'),
    false,
  )
  await go('receipt', '/store/orders/S1-001/receipt')
  await page.getByRole('button', { name: 'Confirm 80 cases' }).waitFor()
  await capture('s5')
  await page.getByRole('button', { name: 'Decrease Set yoghurt 1 kg' }).click()
  await page.getByRole('button', { name: 'Decrease Set yoghurt 1 kg' }).click()
  await page.getByRole('button', { name: 'Decrease Fish, fillet' }).click()
  await page.getByRole('button', { name: 'Report a problem' }).click()
  screen = 'issue'
  await page.waitForURL('**/issue')
  await page.getByRole('heading', { name: 'Report a problem', exact: true }).waitFor()
  await page.reload()
  await page.getByRole('heading', { name: 'Report a problem', exact: true }).waitFor()
  await page.getByRole('button', { name: /Set yoghurt 1 kg/ }).click()
  await page.getByLabel('Problem', { exact: true }).selectOption('damaged')
  await page.getByLabel('Photo link (optional)').fill('/figma/store/test-photo.svg')
  await page.getByRole('button', { name: 'Save problem' }).click()
  await page.evaluate(() => document.fonts.ready)
  await page.getByRole('button', { name: 'Send to dispatch' }).click({ trial: true })
  await capture('s6')
  await page.getByRole('button', { name: 'Send to dispatch' }).click()
  await page.waitForURL('**/store')
  const report = sent.find((x) => x.path.endsWith('/issues'))
  assert.deepEqual(report.body.lines.map((l) => [l.problem, l.qty]).sort(), [
    ['damaged', 2],
    ['missing', 1],
  ])
  await go('notice', `/store/notices/${notice.id}`)
  await page.getByRole('button', { name: 'Got it' }).waitFor()
  await capture('s8')
  await page.getByRole('button', { name: 'Got it' }).click()
  await page.waitForURL('**/store')
  assert(sent.some((x) => x.path.endsWith('/read')))
  empty = true
  await go('home', '/store')
  await page.getByText('No orders yet', { exact: true }).waitFor()
  await capture('empty')
  empty = false
  failing = true
  await go('home', '/store')
  await page.getByText('Store temporarily unavailable', { exact: true }).waitFor()
  await capture('error')
  failing = false
  await page.getByRole('button', { name: 'Try again' }).click()
  await page.getByRole('heading', { name: 'Arriving 05:15–05:35' }).waitFor()
  holdHome = true
  await go('home', '/store')
  await page.getByText('Loading…', { exact: true }).waitFor()
  await capture('loading')
  releaseHome()
  holdHome = false
  await page.getByRole('heading', { name: 'Arriving 05:15–05:35' }).waitFor()
  await go('receipt', '/store/orders/S1-001/receipt')
  await page.getByRole('button', { name: 'Confirm 80 cases' }).waitFor()
  await page.context().setOffline(true)
  await page.getByText('No signal · reconnect to send changes', { exact: true }).waitFor()
  assert(await page.getByRole('button', { name: 'Confirm 80 cases' }).isDisabled())
  await page.context().setOffline(false)
  assert.deepEqual(errors, [])
  await browser.close()
  console.log(
    'Store: five screens captured; item removal, sanity correction, receipt counts, two-line report, acknowledgement and empty/error states verified.',
  )
})().catch((e) => {
  console.error(e)
  process.exit(1)
})
