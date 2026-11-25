/**
 * Screenshot every preview screen at its 480x800 phone size.
 *
 * These pictures become the Nextion backgrounds: the DOM is the reference, so a
 * screenshot of it is the only way the panel can look exactly like the preview.
 * The field boxes are cleaned later where the MCU writes a value.
 *
 * Usage: node nextion/tools/screenshot_web.mjs [baseUrl]
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const root = join(here, '..', '..')
const outDir = join(root, 'nextion', 'assets', 'web')
mkdirSync(outDir, { recursive: true })

const BASE = process.argv[2] || 'http://127.0.0.1:5173/'

const SCREENS = {
  splash: '00_init',
  userInfo: '01_user_info',
  main: '02_main_menu',
  baselineMenu: '03_baseline',
  newBaseline: '04_new_baseline',
  materialData: '05_material_data',
  maturityData: '06_maturity_data',
  baselineResult: '07_baseline_result',
  savedBaseline: '08_saved_baseline',
  kuatTekanMenu: '09_kuat_tekan',
  selectBaseline: '10_select_baseline',
  realtime: '11_realtime',
  strengthResult: '12_strength_result',
  history: '13_history',
  historyDetail: '14_history_detail',
  settings: '15_settings',
  deviceInfo: '16_device_info',
}

const browser = await chromium.launch({
  channel: 'chrome',
  headless: true,
  args: ['--no-sandbox', '--disable-gpu'],
})
const page = await browser.newPage({
  viewport: { width: 900, height: 1000 },
  deviceScaleFactor: 1,
})

await page.addInitScript(() => {
  window.localStorage.clear()
  window.sessionStorage.clear()
  const fixed = new Date('2026-09-28T08:00:00Z').valueOf()
  const RealDate = Date
  class FakeDate extends RealDate {
    constructor(...args) {
      if (args.length === 0) super(fixed)
      else super(...args)
    }
    static now() {
      return fixed
    }
  }
  window.Date = FakeDate
  let seed = 42
  Math.random = () => {
    seed = (seed * 1103515245 + 12345) % 2147483648
    return seed / 2147483648
  }
})

for (const [screen, picture] of Object.entries(SCREENS)) {
  await page.goto(`${BASE}?screen=${screen}`, { waitUntil: 'networkidle' })
  await page.addStyleTag({
    content: `
      .size-badge { display: none !important; }
      .design-overlay { display: none !important; }
      * { scrollbar-width: none !important; }
      *::-webkit-scrollbar { display: none !important; }
    `,
  })
  // Let fonts, images and the first clock tick settle without letting a splash
  // transition move on to the next screen.
  await page.waitForTimeout(screen === 'splash' ? 450 : 550)
  const target = join(outDir, `${picture}.png`)
  await page.locator('.phone').screenshot({ path: target, animations: 'disabled' })
  console.log(`${screen.padEnd(15)} -> ${target}`)
}

await browser.close()
console.log('done')
