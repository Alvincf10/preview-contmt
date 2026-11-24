/**
 * Record where every button on every screen goes.
 *
 * The preview is the reference for navigation: each button carries an onClick
 * that calls `go(...)`. This clicks every button and notes the screen that
 * appears, so the panel's own navigation can be checked against it instead of
 * against a guess.
 *
 * Usage: node nextion/tools/extract_nav.mjs [baseUrl]
 * Writes nextion/tools/nav.json.
 */
import { chromium } from 'playwright'
import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const BASE = process.argv[2] || 'http://localhost:5173/'

const SCREENS = {
  splash: 'pInit',
  userInfo: 'pUser',
  main: 'pMain',
  baselineMenu: 'pBase',
  newBaseline: 'pNewB',
  materialData: 'pMat',
  maturityData: 'pMatu',
  baselineResult: 'pBaseR',
  savedBaseline: 'pSaveB',
  kuatTekanMenu: 'pKuat',
  selectBaseline: 'pSelB',
  realtime: 'pRT',
  strengthResult: 'pStr',
  history: 'pHist',
  historyDetail: 'pHistD',
  settings: 'pSet',
  deviceInfo: 'pDev',
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 900, height: 1000 } })
const report = {}

for (const [screen, pageName] of Object.entries(SCREENS)) {
  await page.goto(`${BASE}?screen=${screen}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(300)

  const count = await page.locator('.phone button').count()
  const entries = []
  for (let i = 0; i < count; i++) {
    // Re-read the button each time: clicking may redraw the screen.
    await page.goto(`${BASE}?screen=${screen}`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(200)
    const button = page.locator('.phone button').nth(i)
    const info = await button.evaluate((el) => {
      const rect = el.getBoundingClientRect()
      const origin = document.querySelector('.phone').getBoundingClientRect()
      return {
        text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40),
        cls: typeof el.className === 'string' ? el.className : '',
        x: Math.round(rect.left - origin.left),
        y: Math.round(rect.top - origin.top),
        w: Math.round(rect.width),
        h: Math.round(rect.height),
      }
    }).catch(() => null)
    if (!info) continue

    let landed = null
    try {
      await button.click({ timeout: 1500 })
      await page.waitForTimeout(350)
      landed = new URL(page.url()).searchParams.get('screen')
    } catch {
      landed = null
    }
    entries.push({ ...info, to: landed })
  }
  report[pageName] = entries
  console.log(`${pageName.padEnd(8)} ${entries.length} buttons: ${entries.map((e) => `${e.text || e.cls.split(' ')[0] || '?'}->${e.to}`).join(', ')}`)
}

await browser.close()
const target = join(here, 'nav.json')
writeFileSync(target, JSON.stringify(report, null, 1) + '\n', 'utf8')
console.log('\nwrote', target)
