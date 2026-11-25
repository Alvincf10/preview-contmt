/**
 * Read the preview's own layout, so the panel's fields land where the design
 * draws them.
 *
 * The React preview is the design: it loads the same background picture and
 * puts every label and value in its place with CSS. So instead of guessing from
 * the PNG's pixels, this walks the live DOM and records each visible element's
 * box relative to the 480x800 canvas.
 *
 * Usage: node nextion/tools/extract_layout.mjs [baseUrl]
 * Writes nextion/tools/layout.json.
 */
import { chromium } from 'playwright'
import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const BASE = process.argv[2] || 'http://localhost:5173/'

/** Preview screen id -> the page name this repo uses for the panel. */
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

// The preview keeps its sample data in localStorage, and a click changes it: a
// SELECT marks a card, a BACK moves the list. Left alone, a second run would read
// a screen with five cards where the first read four, and everything below them
// would differ by one card's height. Each load therefore starts from the same
// stored state.
const RESET_STATE = () => {
  window.localStorage.clear()
  window.sessionStorage.clear()
}
await page.addInitScript(RESET_STATE)

// The preview draws a live clock and a live session, so its sample text would
// change on every run. A fixed clock and a seeded random make the extraction
// repeatable, which is what lets the layout mapping match on that text.
const FIXED_NOW = new Date('2026-09-28T08:00:00Z')
await page.addInitScript((iso) => {
  const fixed = new Date(iso).valueOf()
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
  // eslint-disable-next-line no-global-assign
  window.Date = FakeDate
  // A stable pseudo random, so live temperature jitter is the same every run.
  let seed = 42
  Math.random = () => {
    seed = (seed * 1103515245 + 12345) % 2147483648
    return seed / 2147483648
  }
}, FIXED_NOW.toISOString())

const report = {}

for (const [screen, pageName] of Object.entries(SCREENS)) {
  await page.goto(`${BASE}?screen=${screen}`, { waitUntil: 'networkidle' })
  // Let the clock and the splash timers settle, so nothing is mid-transition.
  await page.waitForTimeout(400)

  const data = await page.evaluate(() => {
    const canvas = document.querySelector('.phone')
    if (!canvas) return { error: 'no .phone' }
    const origin = canvas.getBoundingClientRect()

    /** Everything worth a field: text, inputs, buttons, pictures, tap areas. */
    const isVisible = (el) => {
      const style = getComputedStyle(el)
      if (style.display === 'none' || style.visibility === 'hidden') return false
      if (Number(style.opacity) === 0) return false
      const rect = el.getBoundingClientRect()
      return rect.width > 1 && rect.height > 1
    }

    /** The nearest element that actually holds text, not a wrapper. */
    const ownText = (el) => {
      let text = ''
      for (const node of el.childNodes) {
        if (node.nodeType === Node.TEXT_NODE) text += node.textContent
      }
      return text.trim()
    }

    const box = (el) => {
      const rect = el.getBoundingClientRect()
      return {
        x: Math.round(rect.left - origin.left),
        y: Math.round(rect.top - origin.top),
        w: Math.round(rect.width),
        h: Math.round(rect.height),
      }
    }

    const out = []
    const seen = new Set()

    const record = (el, kind, text, extra = {}) => {
      if (!isVisible(el)) return
      const b = box(el)
      // A button the design draws past the edge is still a button the design
      // intends: keeping it lets the check name the overflow. A field past the
      // edge is not a field, though, so fields stay bounded.
      if (kind !== 'button' && (b.x < -2 || b.y < -2 || b.x + b.w > 482 || b.y + b.h > 802)) return
      if (b.w < 6 || b.h < 6) return
      const key = `${kind}:${b.x},${b.y},${b.w},${b.h}:${text}`
      if (seen.has(key)) return
      seen.add(key)
      out.push({ kind, text: text.slice(0, 60), ...b, ...extra })
    }

    // Text-bearing leaves: the label and value strings the design shows.
    const textSelector =
      'button, input, select, strong, b, em, h1, h2, h3, p, span, small, label, li, td, th, div'
    for (const el of document.querySelectorAll(textSelector)) {
      // A select holds its options as children, so it must not be skipped by
      // the wrapper test below: its own shown text is the chosen option.
      if (el.tagName !== 'SELECT' && el.children.length > 0 && ownText(el) === '') continue
      const tag = el.tagName.toLowerCase()
      let text = ownText(el)
      if (tag === 'input') text = el.value
      if (tag === 'select') {
        // A closed select shows its chosen option, not its options' text.
        text = el.value || el.options?.[el.selectedIndex]?.textContent || ''
      }
      if (!text && tag !== 'input' && tag !== 'select') continue
      const cls = typeof el.className === 'string' ? el.className : ''
      let kind = 'text'
      if (tag === 'button') kind = 'button'
      else if (tag === 'input' || tag === 'select') kind = 'input'
      record(el, kind, text.replace(/\s+/g, ' '), { cls })
    }

    // Tap targets that carry no text of their own, such as an icon button.
    for (const el of document.querySelectorAll('button, [role="button"], a')) {
      record(el, 'button', (el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40), {
        cls: typeof el.className === 'string' ? el.className : '',
      })
    }

    // Pictures the design draws.
    for (const el of document.querySelectorAll('img, svg.chart')) {
      record(el, el.tagName.toLowerCase() === 'svg' ? 'chart' : 'image', '', {
        cls: typeof el.className === 'string' ? el.className : '',
        src: el.getAttribute('src') || '',
      })
    }

    return {
      size: { w: Math.round(origin.width), h: Math.round(origin.height) },
      background: getComputedStyle(document.querySelector('.screen-bg') || document.body).backgroundImage,
      elements: out,
    }
  })

  report[pageName] = data
  console.log(`${pageName.padEnd(8)} ${screen.padEnd(15)} ${data.elements ? data.elements.length : 0} elements`)
}

await browser.close()
const target = join(here, 'layout.json')
writeFileSync(target, JSON.stringify(report, null, 1) + '\n', 'utf8')
console.log('\nwrote', target)
