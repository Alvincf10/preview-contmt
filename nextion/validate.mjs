#!/usr/bin/env node
/**
 * Validate nextion/ build kit completeness.
 * Usage: node nextion/validate.mjs
 * Exit 0 = ready to assemble on Windows.
 */
import { readFileSync, existsSync, readdirSync, writeFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const errors = []
const warnings = []

function must(cond, msg) {
  if (!cond) errors.push(msg)
}

function readJson(rel) {
  const p = join(root, rel)
  must(existsSync(p), `missing ${rel}`)
  if (!existsSync(p)) return null
  try {
    return JSON.parse(readFileSync(p, 'utf8'))
  } catch (e) {
    errors.push(`invalid JSON ${rel}: ${e.message}`)
    return null
  }
}

const proj = readJson('project.json')
must(proj?.pages?.length === 17, `expected 17 pages, got ${proj?.pages?.length ?? 0}`)
must(proj?.display?.width === 480 && proj?.display?.height === 800, 'display must be 480x800')

const hotspotRows = [['page', 'objname', 'label', 'x', 'y', 'w', 'h', 'event_file', 'event_code']]
const usedAssets = new Set()
const eventFiles = new Set()

for (const entry of proj?.pages ?? []) {
  const page = readJson(entry.file)
  must(existsSync(join(root, entry.asset)), `missing asset ${entry.asset}`)
  usedAssets.add(entry.asset.replace(/^assets\/pages\//, ''))
  must(page?.name === entry.name, `${entry.file}: name mismatch (${page?.name} vs ${entry.name})`)

  const comps = page?.components ?? []
  const hasClock = comps.some((c) => c.objname === 'tClock')
  const hasBatt = comps.some((c) => c.objname === 'tBatt')
  if (entry.name !== 'pInit') {
    must(hasClock, `${entry.name}: missing tClock`)
    must(hasBatt, `${entry.name}: missing tBatt`)
  }

  const eventsMap = page?.events ?? {}
  for (const c of comps) {
    if (c.type !== 'TouchCap') continue
    const key = `${c.objname}.touchpress`
    const evFile = eventsMap[key]
    let code = ''
    if (evFile) {
      const fp = join(root, evFile)
      must(existsSync(fp), `${entry.name}: missing event file ${evFile}`)
      eventFiles.add(evFile)
      if (existsSync(fp)) code = readFileSync(fp, 'utf8').trim().replace(/\r?\n/g, ' | ')
    } else {
      code = (c.events?.touchpress ?? '').replace(/\r?\n/g, ' | ')
      if (!code) warnings.push(`${entry.name}.${c.objname}: TouchCap has no event`)
    }
    hotspotRows.push([
      entry.name,
      c.objname,
      c.label ?? '',
      c.x,
      c.y,
      c.w,
      c.h,
      evFile ?? '',
      code,
    ])
  }
}

// Required UI fields for latest screens
const pRT = readJson('pages/pRT.json')
for (const id of ['tM', 'tFcLive', 'tPctLive', 'tPourDate', 'tInitTemp', 'mAddDay', 'mNext', 'tL0']) {
  must(pRT?.components?.some((c) => c.objname === id), `pRT missing ${id}`)
}
const pStr = readJson('pages/pStr.json')
for (const id of ['tFc', 'tPct', 'tAvg', 'tM']) {
  must(pStr?.components?.some((c) => c.objname === id), `pStr missing ${id}`)
}
const pHist = readJson('pages/pHist.json')
for (const id of ['tH0', 'mRow0', 'mDetail']) {
  must(pHist?.components?.some((c) => c.objname === id), `pHist missing ${id}`)
}
const pHistD = readJson('pages/pHistD.json')
for (const id of ['tFc', 'tL0', 'tTestId']) {
  must(pHistD?.components?.some((c) => c.objname === id), `pHistD missing ${id}`)
}

for (const doc of ['BUILD.md', 'SERIAL.md', 'CHECKLIST.md', 'FLOW.md', 'README.md', 'MANIFEST.json']) {
  must(existsSync(join(root, doc)), `missing ${doc}`)
}

// Orphan assets in pages/
const assetDir = join(root, 'assets', 'pages')
if (existsSync(assetDir)) {
  for (const f of readdirSync(assetDir)) {
    if (!f.endsWith('.png')) continue
    if (!usedAssets.has(f)) warnings.push(`orphan asset assets/pages/${f} (move to assets/_unused/)`)
  }
}

// Regenerate hotspots.csv
const csv = hotspotRows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n') + '\n'
writeFileSync(join(root, 'hotspots.csv'), csv)

console.log(`pages: ${proj?.pages?.length ?? 0}`)
console.log(`hotspots: ${hotspotRows.length - 1}`)
console.log(`event refs: ${eventFiles.size}`)
if (warnings.length) {
  console.log('\nWarnings:')
  for (const w of warnings) console.log(`  ⚠ ${w}`)
}
if (errors.length) {
  console.log('\nErrors:')
  for (const e of errors) console.log(`  ✖ ${e}`)
  process.exit(1)
}
console.log('\nOK — nextion kit ready to assemble on Windows (see BUILD.md)')
