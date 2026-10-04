const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const fs = require('fs')
const path = require('path')
const fixture = JSON.parse(fs.readFileSync('apps/web/src/features/dispatch/planning/planning.fixture.json', 'utf8'))
;(async () => {
 const browser = await chromium.launch({headless:true,channel:'msedge'})
 const page = await browser.newPage({viewport:{width:1440,height:900}})
 page.on('pageerror',e=>console.error('PAGE ERROR',e.message))
 page.on('console',m=>{if(m.type()==='error')console.error('CONSOLE',m.text())})
 await page.addInitScript(() => localStorage.setItem('xora.session',JSON.stringify({accessToken:'synthetic',expiresAt:1999999999999,user:{id:'test',name:'Kasun F.',role:'dispatcher',depot:'Peliyagoda',email:'test@example.test',vehicle:null,outlet:null,locale:'en'}})))
 await page.route('**/api/v1/**',async route=> {
  const url=route.request().url()
  let body={}
  if(url.includes('/clock'))body={now:'2026-04-06T16:12:00+05:30',demo:true}
  else if(url.includes('/deferrals/confirm')) {fixture.plan.deferrals.forEach(d=>d.confirmed=true);body=fixture.plan}
  else if(url.includes('/publish-check'))body={can_publish:true,violations:[],unconfirmed_deferrals:[],late_risk_order_refs:['TEST111','TEST112','TEST211','TEST212','TEST311','TEST312']}
  else if(url.includes('/fleet'))body=fixture.fleet
  else body=fixture.plan
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)})
 })
 await page.goto('http://127.0.0.1:5173/dispatch/plan')
 await page.getByRole('heading',{name:'Plan for Tue 7 Apr'}).waitFor()
 await page.evaluate(()=>document.fonts.ready)
 await page.screenshot({path:'.venv/ui-timeline.png'})
 await page.getByRole('button',{name:'Deferred · 4',exact:true}).click()
 await page.screenshot({path:'.venv/ui-deferred.png'})
 await page.getByRole('button',{name:'Confirm 4 deferrals'}).click()
 await page.getByRole('button',{name:'Confirm 0 deferrals'}).waitFor()
 await page.getByRole('button',{name:'Fleet · 7 of 7',exact:true}).click()
 await page.screenshot({path:'.venv/ui-fleet.png'})
 await page.getByRole('button',{name:'Timeline',exact:true}).click()
 await page.getByRole('button',{name:'Review & publish'}).click()
 await page.getByRole('dialog').waitFor()
 await page.getByRole('button',{name:'Publish plan v1',exact:true}).isEnabled()
 await page.waitForFunction(()=>!document.querySelector('dialog button:last-child').disabled)
 await page.screenshot({path:'.venv/ui-publish.png'})
 await browser.close()
 console.log('Four synthetic dispatcher screenshots captured; no page errors.')
})().catch(e=>{console.error(e);process.exit(1)})

