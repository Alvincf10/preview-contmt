import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const outDir = path.join(root, 'compare-out')
fs.mkdirSync(outDir, { recursive: true })

const screens = [
  ['splash', 'initialization.png'],
  ['main', 'main-menu.png'],
  ['userInfo', 'user-info.png'],
  ['baselineMenu', 'baseline.png'],
  ['newBaseline', 'new-baseline.png'],
  ['materialData', 'material-data.png'],
  ['maturityData', 'maturity-data.png'],
  ['baselineResult', 'baseline-result.png'],
  ['savedBaseline', 'saved-baseline.png'],
  ['kuatTekanMenu', 'kuat-tekan.png'],
  ['selectBaseline', 'select-baseline.png'],
  ['realtime', 'realtime.png'],
  ['strengthResult', 'strength-result.png'],
  ['history', 'test-history.png'],
  ['historyDetail', 'result-detail.png'],
  ['settings', 'settings.png'],
  ['deviceInfo', 'device-info.png'],
]

async function loadPng(filePath) {
  // Prefer sharp if available; fallback to raw via playwright screenshot only
  return filePath
}

function diffStats(aBuf, bBuf) {
  // PNG buffers not raw — use playwright screenshot already same size and simple pixel via canvas in page
  return null
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({
  viewport: { width: 560, height: 900 },
  deviceScaleFactor: 1,
})

await page.goto('http://127.0.0.1:5173/?screen=main', { waitUntil: 'networkidle' })

const results = []

for (const [screen, designName] of screens) {
  await page.goto(`http://127.0.0.1:5173/?screen=${screen}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(screen === 'splash' ? 3200 : 350)
  const phone = page.locator('.phone')
  const box = await phone.boundingBox()
  if (!box) throw new Error(`No .phone for ${screen}`)

  const shotPath = path.join(outDir, `${screen}.png`)
  await phone.screenshot({ path: shotPath })

  const metrics = await page.evaluate(() => {
    const phone = document.querySelector('.phone')
    const panel = document.querySelector('.panel')
    const brand = document.querySelector('.brand-bar')
    const pr = phone.getBoundingClientRect()
    const pan = panel?.getBoundingClientRect()
    const br = brand?.getBoundingClientRect()
    return {
      phone: { w: Math.round(pr.width), h: Math.round(pr.height) },
      brandH: br ? Math.round(br.height) : null,
      panel: pan
        ? {
            x: Math.round(pan.left - pr.left),
            y: Math.round(pan.top - pr.top),
            w: Math.round(pan.width),
            h: Math.round(pan.height),
          }
        : null,
    }
  })

  // Pixel diff in page using canvas
  const designUrl = `/design/${designName}`
  const diff = await page.evaluate(async ({ designUrl, screen }) => {
    const phone = document.querySelector('.phone')
    const canvas = document.createElement('canvas')
    canvas.width = 480
    canvas.height = 800
    const ctx = canvas.getContext('2d')

    // capture phone via draw? can't easily — use design vs live screenshot fetched
    const live = await new Promise(async (resolve) => {
      // render phone to canvas using html2canvas-less approach: not available
      resolve(null)
    })
    return { designUrl, screen, note: 'metrics-only' }
  }, { designUrl, screen })

  // Node-side pixel compare with pure decode via playwright screenshot already saved
  // Use Python externally; here store metrics
  results.push({ screen, designName, box, metrics, shotPath })
  console.log(
    `${screen.padEnd(16)} phone=${metrics.phone.w}x${metrics.phone.h} brand=${metrics.brandH} panel=${JSON.stringify(metrics.panel)}`,
  )
}

fs.writeFileSync(path.join(outDir, 'metrics.json'), JSON.stringify(results, null, 2))
await browser.close()

// Python pixel diffs
import { spawnSync } from 'node:child_process'
const py = `
from pathlib import Path
from PIL import Image
import json, numpy as np
root = Path(${JSON.stringify(root)})
out = root/'compare-out'
design = root/'public'/'design'
rows=[]
for item in json.loads((out/'metrics.json').read_text()):
    live = Image.open(item['shotPath']).convert('RGB').resize((480,800))
    ref = Image.open(design/item['designName']).convert('RGB')
    a=np.asarray(live).astype(np.int16)
    b=np.asarray(ref).astype(np.int16)
    d=np.abs(a-b).mean(axis=2)
    # ignore tiny antialias
    mismatch=(d>28).mean()*100
    mae=float(d.mean())
    # write heat overlay
    heat=np.zeros_like(a)
    heat[:,:,0]=np.clip(d*3,0,255)
    heat[:,:,1]=np.clip(255-d*2,0,80)
    blend=((0.55*a + 0.45*heat).astype(np.uint8))
    Image.fromarray(blend).save(out/f"{item['screen']}-diff.png")
    rows.append((item['screen'], round(mae,2), round(mismatch,2)))
rows.sort(key=lambda x: -x[2])
print('screen | MAE | mismatch%')
for r in rows:
    print(f'{r[0]:16} {r[1]:7.2f} {r[2]:7.2f}%')
print('AVG mismatch', round(sum(x[2] for x in rows)/len(rows),2))
`
spawnSync('python3', ['-c', py], { stdio: 'inherit' })
