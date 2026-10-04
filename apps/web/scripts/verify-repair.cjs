const assert = require('node:assert/strict')
const fs = require('node:fs')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const fixture = JSON.parse(fs.readFileSync('apps/web/src/features/dispatch/repair/repair.fixture.json', 'utf8'))

;(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  let applied = null
  page.on('pageerror', e => errors.push(e.message))
  await page.addInitScript(() => localStorage.setItem('xora.session', JSON.stringify({
    accessToken: 'synthetic', expiresAt: 1999999999999,
    user: { id: 'test', name: 'Kasun F.', role: 'dispatcher', depot: 'Peliyagoda', email: 'test@example.test', vehicle: null, outlet: null, locale: 'en' },
  })))
  await page.route('**/api/v1/**', async route => {
    const url = route.request().url()
    let body = fixture
    if (url.includes('/clock')) body = { now: '2026-04-07T04:19:12+05:30', demo: true }
    if (url.includes('/apply')) {
      applied = route.request().postDataJSON()
      body = { operating_date: fixture.operating_date }
    }
    if (url.includes('/plans/')) body = require('../src/features/dispatch/planning/planning.fixture.json').plan
    if (url.includes('/fleet')) body = require('../src/features/dispatch/planning/planning.fixture.json').fleet
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
  await page.goto(`http://127.0.0.1:5173/dispatch/shortfalls/${fixture.id}`)
  await page.getByRole('heading', { name: 'Resolve shortfall before departure' }).waitFor()
  await page.evaluate(() => document.fonts.ready)
  assert.equal(await page.getByRole('radio', { name: 'Option A' }).getAttribute('aria-checked'), 'true')
  assert.equal(applied, null)
  assert.equal(await page.getByRole('button', { name: 'Call the dock' }).isDisabled(), true)
  await page.screenshot({ path: '.venv/ui-shortfall.png' })
  await page.getByRole('radio', { name: 'Option C' }).click()
  await page.getByText('Breaks TESTOUT2’s rule', { exact: true }).waitFor()
  await page.getByRole('button', { name: 'Apply C · publish v2' }).waitFor()
  await page.getByRole('radio', { name: 'Option B' }).click()
  await page.getByRole('button', { name: 'Apply B · publish v2' }).click()
  await page.waitForURL('**/dispatch/plan?date=2026-04-07')
  assert.deepEqual(applied, { option_id: fixture.options[1].id })
  assert.deepEqual(errors, [])
  await browser.close()
  console.log('D6 captured; recommendation, human selection and publish navigation verified.')
})().catch(e => { console.error(e); process.exit(1) })
