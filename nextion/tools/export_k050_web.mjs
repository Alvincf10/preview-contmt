import { execFileSync } from 'node:child_process'
import { chromium } from 'playwright'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const dist = join(repo, 'dist')
const url = 'http://conmt-preview.test/'
const output = join(repo, 'nextion/nxsrc-K050/pictures')
const python = process.env.CONMT_PYTHON || 'python3'
const generator = join(repo, 'nextion/tools/k050_protocol.py')
const screens = [
  ['pInit', 'splash', '00_init'],
  ['pUser', 'userInfo', '01_user_info'],
  ['pMain', 'main', '02_main_menu'],
  ['pBase', 'baselineMenu', '03_baseline'],
  ['pNewB', 'newBaseline', '04_new_baseline'],
  ['pMat', 'materialData', '05_material_data'],
  ['pMatu', 'maturityData', '06_maturity_data'],
  ['pBaseR', 'baselineResult', '07_baseline_result'],
  ['pSaveB', 'savedBaseline', '08_saved_baseline'],
  ['pKuat', 'kuatTekanMenu', '09_kuat_tekan'],
  ['pSelB', 'selectBaseline', '10_select_baseline'],
  ['pRT', 'realtime', '11_realtime'],
  ['pStr', 'strengthResult', '12_strength_result'],
  ['pHist', 'history', '13_history'],
  ['pHistD', 'historyDetail', '14_history_detail'],
  ['pSet', 'settings', '15_settings'],
  ['pDev', 'deviceInfo', '16_device_info'],
]

const dialogs = {
  pAddRow: '.add-day-btn',
  pSchedule: '.title-info-btn',
  pConfirm: '.row-del',
}

const layout = { pages: {}, pictures: [] }
const style = readFileSync(join(repo, 'nextion/tools/k050-preview.css'), 'utf8')
mkdirSync(output, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
try {
  const page = await browser.newPage({
    viewport: { width: 480, height: 800 },
    deviceScaleFactor: 1,
    timezoneId: 'Asia/Jakarta',
    reducedMotion: 'reduce',
  })
  await page.route(url + '**', (route) => {
    const file = join(dist, new URL(route.request().url()).pathname.slice(1) || 'index.html')
    return existsSync(file) ? route.fulfill({ path: file }) : route.fulfill({ status: 404 })
  })
  await page.addInitScript(() => {
    const stamp = Date.parse('2026-11-24T05:01:01Z')
    const ActualDate = Date
    window.Date = class extends ActualDate {
      constructor(...args) { super(...(args.length ? args : [stamp])) }
      static now() { return stamp }
    }
    Math.random = () => 0.5
    if (new URLSearchParams(location.search).get('screen') === 'maturityData') {
      const rows = Array.from({ length: 5 }, (_, day) => ({
        day, timeH: 24 * day, fcLab: day ? String(10 * day) : '', temperature: '26.1',
      }))
      localStorage.setItem('conmt:app-state:v7', JSON.stringify({ baselineDraft: { rows } }))
    } else {
      localStorage.clear()
    }
  })

  for (const [id, screen, picture] of screens) await renderDomain(page, id, screen, picture)
  await renderLocals(page)
  writeFileSync(join(repo, 'nextion/tools/k050_web_layout.json'), JSON.stringify(layout, null, 2) + '\n')
} finally {
  await browser.close()
}
if (process.argv.includes('--source')) execFileSync(python, [generator], { stdio: 'inherit' })

async function configure(page, id) {
  return page.locator('.phone').evaluate((phone, id) => {
    phone.classList.add('k050-export')
    phone.dataset.k050Page = id
    const screen = phone.querySelector('.screen')
    const root = phone.getBoundingClientRect()
    const map = { boxes: {}, regions: {}, hide: [] }
    const all = (selector) => [...phone.querySelectorAll(selector)]
    const one = (selector, i = 0) => {
      const el = all(selector)[i]
      if (!el) throw new Error(id + ' missing ' + selector + '[' + i + ']')
      return el
    }
    const box = (el) => {
      const r = el.getBoundingClientRect()
      const x = Math.round(r.left - root.left)
      const y = Math.round(r.top - root.top)
      return [x, y, Math.round(r.right - root.left) - x, Math.round(r.bottom - root.top) - y]
    }
    const add = (parent, tag, className, text = '') => {
      const el = document.createElement(tag)
      el.className = className
      el.textContent = text
      parent.append(el)
      return el
    }
    const mark = (name, el, { kind = 'text', target = el, align, width, height, hide = false } = {}) => {
      const [x, y, w, h] = box(target)
      const style = getComputedStyle(el)
      const font = parseFloat(style.fontSize)
      map.boxes[name] = {
        rect: [x, y, width ?? w, height ?? h], kind, font,
        align: align ?? (style.textAlign === 'center' ? 1 : style.textAlign === 'right' ? 2 : 0),
        color: style.color,
      }
      if (hide) el.classList.add('k050-value')
      return el
    }
    const action = (name, selector, i) => mark(name, one(selector, i), { kind: 'touch' })
    const value = (name, selector, i, options) => mark(name, one(selector, i), { hide: true, ...options })
    const fields = (names, selector, options) => names.forEach((name, i) => value(name, selector, i, options))
    const footer = (back, next) => {
      const buttons = id === 'pBaseR' ? '.br-save button' : '.panel-footer button'
      if (back) action(back, buttons, 0)
      if (next) action(next, buttons, back ? 1 : 0)
    }
    const dynamicBox = (name, el) => mark(name, el, { kind: 'paint' })
    const maskText = (parent) => {
      const span = document.createElement('span')
      // Keep the Web icon next to the label while the MCU fills the label.
      for (const node of [...parent.childNodes]) {
        if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) span.append(node)
      }
      parent.append(span)
      return span
    }
    const dims = (name, rect, props) => {
      map.boxes[name] = { rect, font: 17, align: 0, color: 'rgb(255, 255, 255)', kind: 'text', ...props }
    }
    const hideInBase = (el) => {
      el.dataset.k050Patch = '1'
      map.hide.push(el.className)
    }
    const resetLength = (selector, count) => all(selector).slice(count).forEach(el => el.remove())
    const status = one('.status-clock-value')
    const batt = one('.status-batt-pct')
    mark('tClock', status, { hide: true, align: 1 })
    mark('tBatt', batt, { hide: true, align: 1 })
    const clockBadge = box(one('.status-clock'))
    const icon = one('.status-batt-ico')
    const [ix, iy, iw, ih] = box(icon)
    const [tx, , tw] = map.boxes.tClock.rect
    map.boxes.tClock.rect = [tx, clockBadge[1], tw, clockBadge[3]]
    if (id === 'pUser' || id === 'pDev') {
      dims('mClockBadge', [clockBadge[0], clockBadge[1], tx - clockBadge[0], clockBadge[3]], { kind: 'touch' })
    }
    const [bx, , bw] = map.boxes.tBatt.rect
    const badge = box(one('.status-batt'))
    map.boxes.tBatt.rect = [bx, badge[1], bw, badge[3]]
    icon.querySelector('rect[opacity]').setAttribute('width', '0')
    map.regions.battery = {
      icon: [ix, iy, iw, ih],
      fill: [Math.round(ix + 4.2 * iw / 24), Math.round(iy + 8.7 * ih / 24),
        Math.round(12.5 * iw / 24), Math.round(6.6 * ih / 24)],
    }
    if (id !== 'pBaseR') {
      const notice = add(screen, 'div', 'k050-notice', ' ')
      mark('tNotice', notice, { align: 1 })
    }

    if (id === 'pInit') {
      const progress = one('.init-progress-track')
      map.regions.progress = box(progress)
      const fill = one('.init-progress-fill')
      fill.style.width = '100%'
      hideInBase(fill)
      value('tProgress', '.init-progress-head strong', 0, { width: 45, align: 2 })
      const [px, py, pw, ph] = box(one('.init-progress-head'))
      map.boxes.tProgress.rect = [px + pw - 50, py, 50, ph]
      for (const [i, name] of ['tReady', 'tChkClock', 'tChkSensors', 'tChkDevice'].entries()) {
        const li = one('.init-steps li', i)
        li.className = 'todo'
        const title = maskText(li)
        const [lx, ly, lw, lh] = box(li)
        const [sx] = box(title)
        mark(name, title, { hide: true })
        map.boxes[name].rect = [sx, ly, lx + lw - sx, lh]
      }
    }
    if (id === 'pUser') {
      fields(['tOp', 'tProj', 'tDate'], '.panel-body input')
      footer(null, 'mSave')
    }
    if (id === 'pMain') {
      ['mBase', 'mKuat', 'mSet', 'mDev'].forEach((name, i) => action(name, '.menu-row', i))
    }
    if (id === 'pBase') {
      action('mNew', '.menu-row', 0)
      action('mSaved', '.menu-row', 1)
      footer('mBack')
    }
    if (id === 'pKuat') {
      ['mStart', 'mHist', 'mBack'].forEach((name, i) => action(name, '.dark-menu-row', i))
    }
    if (id === 'pKuat' || id === 'pBase') {
      all('.temp-strip-cell').forEach((cell, i) => {
        const el = cell.querySelector('strong')
        mark('tS' + (i + 1), el, { hide: true, align: 1 })
        const [x, , w] = box(cell)
        const [, y, , h] = box(el)
        map.boxes['tS' + (i + 1)].rect = [x + 3, y, w - 6, h]
      })
    }
    if (id === 'pNewB') {
      fields(['tName', 'tFc'], '.panel-body input')
      value('tTemp', '.select-input')
      footer('mBack', 'mNext')
    }
    if (id === 'pMat') {
      fields(['tCem', 'tWat', 'tWC', 'tCoa', 'tFin'], '.material-row input')
      fields(['tRetP', 'tRetB', 'tAccP', 'tAccB', 'tFlyP', 'tFlyB'], '.admix-row input')
      footer('mBack', 'mNext')
    }
    if (id === 'pMatu') {
      action('mInfo', '.title-info-btn')
      footer('mBack', 'mGen')
      const rows = all('.maturity-table tbody tr')
      if (rows.length !== 5) throw new Error('Expected five maturity slots')
      rows.forEach((row, i) => {
        const cells = [...row.cells]
        for (const [j, name] of ['tDay', 'tTim', 'tFc', 'tT'].entries()) {
          const input = cells[j].querySelector('input')
          mark(name + i, input, { target: cells[j], hide: true, align: 1 })
        }
        mark('mDelete' + i, cells[4], { kind: 'paint' })
        hideInBase(row)
      })
      action('mAddDay', '.add-day-btn')
      action('mSensor', '.sensor-btn')
      map.boxes.mAddDay.kind = map.boxes.mSensor.kind = 'paint'
      const strip = one('.maturity-actions')
      hideInBase(strip)
      map.regions.maturityActions = box(strip)
      map.regions.rows = rows.map(box)
      value('tPourTime', '.pour-clock-input', 0, { align: 1 })
      value('tDatumLab', '.info-box > div', 1)
      const [x, y, w] = map.boxes.tNotice.rect
      dims('tPageRows', [x + 193, y - 12, w - 386, 12], { align: 1, font: 12 })
    }
    if (id === 'pBaseR') {
      fields(['tName', 'tTarget', 'tDatum', 'tDate', 'tOp', 'tProj'], '.br-card:first-child .br-kv strong')
      fields(['tA', 'tB', 'tR2', 'tFactor'], '.br-inner-eq .br-kv strong')
      value('tEq', '.br-equation')
      action('mCurve', '.br-inner-chart')
      map.regions.plot = box(one('.chart-frame'))
      map.regions.plotSurface = box(one('.chart'))
      for (const el of all('.chart-line-log, .chart-dot, .chart-tick, .chart-grid-major, .chart-grid-minor, .chart-frame')) {
        el.classList.add('k050-value')
      }
      footer('mBack', 'mSave')
    }
    if (id === 'pSaveB' || id === 'pSelB') {
      resetLength('.baseline-card', 4)
      if (id === 'pSelB') {
        const body = one('.panel-body > .stack')
        const resume = add(body, 'button', 'btn btn-dark k050-resume', 'RESUME')
        body.prepend(resume)
        const hint = add(body, 'div', 'k050-start-hint', ' ')
        dynamicBox('mResume', resume)
        hideInBase(resume)
        mark('tStartHint', hint, { align: 1 })
      }
      map.regions.cards = []
      all('.baseline-card').forEach((card, i) => {
        card.classList.remove('selected')
        card.querySelector('.mini-btn.orange').classList.remove('active')
        const [x, y, w, h] = box(card)
        map.regions.cards.push([x, y, w, h])
        const body = card.querySelector('.baseline-card-body')
        mark('tName' + i, body.querySelector('strong'), { hide: true })
        const values = body.querySelectorAll('.triple b')
        const dateLabel = values[2].parentElement.firstChild
        if (dateLabel.nodeType === Node.TEXT_NODE) dateLabel.textContent = 'Pour Date '
        const labels = ['tVal', 'tDatum', 'tSavedDate']
        for (let j = 0; j < labels.length; j++) {
          const [cx] = box(values[j].parentElement)
          const [, vy, , vh] = box(values[j])
          const cw = box(values[j].parentElement)[2]
          dims(labels[j] + i, [cx, vy, cw, vh], { font: 13, kind: 'draw' })
          values[j].classList.add('k050-value')
        }
        map.boxes['tName' + i].kind = 'draw'
        const deleteButton = card.querySelector('.mini-btn.dark')
        if (deleteButton) {
          const [dx, dy, , dh] = box(deleteButton)
          dims('mPick' + i, [x, y, dx - x, h], { kind: 'touch' })
          dims('mPickTag' + i, [dx, y, x + w - dx, dy - y], { kind: 'touch' })
          dims('mDelete' + i, [dx, dy, x + w - dx, Math.max(dh, y + h - dy)], { kind: 'touch' })
        } else {
          dims('mPick' + i, [x, y, w, h], { kind: 'touch' })
        }
        hideInBase(card)
      })
      footer('mBack', id === 'pSaveB' ? 'mSelect' : 'mStart')
      const [x, y, w] = box(one('.panel-body'))
      if (id === 'pSaveB') dims('tEmptyList', [x + 16, y + 8, w - 32, 48], { align: 1, kind: 'draw' })
      const [, ny] = map.boxes.tNotice.rect
      dims('tPageRows', [206, ny - 13, 68, 13], { font: 12, align: 1 })
    }
    if (id === 'pRT') {
      const header = one('.monitor-head')
      maskText(header)
      const log = add(header, 'button', 'mini-btn dark k050-log', '+ ADD DAY')
      for (const demo of all('.rt-day-btn')) demo.remove()
      const [hx] = box(header)
      const [lx, ly, , lh] = box(log)
      dims('mPoints', [hx, ly, lx - hx - 4, lh], { kind: 'touch' })
      mark('mAddCheck', log, { kind: 'touch' })
      value('tBase', '.rt-baseline-name')
      fields(['tTarget', 'tDatum'], '.rt-baseline-split b')
      value('tM', '.rt-live-cell strong')
      const fc = one('.rt-live-fc strong')
      const [fx, fy, fw, fh] = box(fc)
      fc.classList.add('k050-value')
      dims('tFc', [fx, fy, fw - 59, fh], { font: 18 })
      dims('tPct', [fx + fw - 55, fy, 55, fh], { font: 16, align: 2 })
      fields(['tS1', 'tS2', 'tS3'], '.sensor-box strong', { align: 1 })
      all('.sensor-box').forEach((item, i) => {
        const b = map.boxes['tS' + (i + 1)]
        const [cx, , cw] = box(item)
        b.rect = [cx + 3, b.rect[1], cw - 6, b.rect[3]]
      })
      value('tAvg', '.avg-bar strong', 0, { align: 1 })
      fields(['tPDate', 'tNowD', 'tPour', 'tNowT', 'tInitTemp', 'tNowTemp'], '.rt-cell-value')
      for (const name of ['tPDate', 'tPour', 'tInitTemp']) {
        map.boxes[name].rect[2] = 107
      }
      for (const name of ['tNowD', 'tNowT', 'tNowTemp']) {
        const d = map.boxes[name]
        d.rect[0] += d.rect[2] - 107
        d.rect[2] = 107
        d.align = 2
      }
      footer('mBack', 'mNext')
    }
    if (id === 'pStr') {
      value('tBase', '.sr-baseline-name')
      fields(['tTarget', 'tDatum'], '.sr-baseline-split b')
      const strength = one('.predict-box-main strong')
      const [x, y, w, h] = box(strength)
      strength.classList.add('k050-value')
      dims('tFc', [x, y, w - 85, h], { font: 28, align: 1 })
      dims('tPct', [x + w - 80, y, 80, h], { font: 22, align: 1, color: 'rgb(255, 148, 49)' })
      fields(['tAvg', 'tM'], '.sr-metric strong', { width: 146, align: 1 })
      footer('mBack', 'mSave')
    }
    if (id === 'pHist') {
      const template = one('.history-card')
      const cards = Array.from({ length: 3 }, () => template.cloneNode(true))
      one('.history-list').replaceChildren(...cards)
      map.regions.cards = cards.map((card, i) => {
        card.classList.remove('selected')
        const values = card.querySelectorAll('strong')
        for (const [j, field] of ['tId', 'tName', 'tVal', 'tDate', 'tCount'].entries()) {
          mark(field + i, values[j], { hide: true, kind: 'draw' })
        }
        const rect = box(card)
        dims('mHistory' + i, rect, { kind: 'touch' })
        hideInBase(card)
        return rect
      })
      footer('mBack', 'mDetail')
      map.boxes.mDetail.kind = 'paint'
      hideInBase(one('.panel-footer .btn-orange'))
      const [x, y, w, h] = map.regions.cards[0]
      dims('tHistEmpty', [x + 10, y + 12, w - 20, Math.min(50, h - 12)], { align: 1, kind: 'draw' })
    }
    if (id === 'pHistD') {
      resetLength('.rdh-log-item', 5)
      resetLength('.rdh-section', 2)
      fields(['tId', 'tSavedAt', 'tDate', 'tOp', 'tProj'], '.rdh-meta strong')
      value('tBase', '.rdh-baseline strong')
      fields(['tTarget', 'tDatum'], '.rdh-baseline-split b')
      map.regions.rows = all('.rdh-log-toggle').map((row, i) => {
        const [x, y, w, h] = box(row)
        for (const el of row.children) {
          if (!el.classList.contains('rdh-log-chevron')) el.classList.add('k050-value')
        }
        dims('tLog' + i, [x + 9, y + 2, w - 27, h - 4], { font: 15, patch: true })
        hideInBase(row.closest('.rdh-log-item'))
        return [x, y, w, h]
      })
      footer('mBack')
    }
    if (id === 'pSet') {
      fields(['tHour', 'tMin', 'tSec', 'tBright'], '.stepper > strong')
      for (let i = 0; i < 8; i++) action('mTap' + i, '.stepper-arrows button', i)
      for (let i = 0; i < 2; i++) action('mTap' + (i + 8), '.toggle', i)
      footer('mBack', 'mSave')
    }
    if (id === 'pDev') {
      const defs = all('.info-row:not(.info-row-status) strong')
      defs[3].textContent = 'NX8048K050'
      defs[5].textContent = 'Serial / CM1'
      for (const [i, name] of [[2, 'tDevVersion'], [3, 'tDevHardware'], [4, 'tDevSensor'], [5, 'tDevSerial']]) {
        const el = defs[i]
        const baked = i === 3 || i === 5
        mark(name, el, { hide: !baked, target: el.parentElement })
        if (baked) Object.assign(map.boxes[name], { baked: true, value: el.textContent })
        const [x, , w] = map.boxes[name].rect
        const [, y, , h] = box(el)
        map.boxes[name].rect = [x, y, w, h]
      }
      const pill = one('.info-row-status .status-pill')
      mark('tDevStatus', pill, { align: 1 })
      maskText(pill).classList.add('k050-value')
      const subtitle = one('.panel-sub')
      const [sx, sy, sw, sh] = box(subtitle)
      dims('tDevHealth', [sx, sy + sh + 1, sw, 16], { font: 13 })
      footer('mBack')
    }
    return map
  }, id)
}

async function screenshot(page, name) {
  await page.locator('.phone').screenshot({ path: join(output, name + '.png'), animations: 'disabled' })
  layout.pictures.push(name)
}

async function renderDomain(page, id, screen, picture) {
  await page.goto(url + '?screen=' + screen, { waitUntil: 'domcontentloaded' })
  const phone = page.locator('.phone')
  await phone.waitFor()
  await page.evaluate(() => document.fonts.ready)
  await page.addStyleTag({ content: style })
  const entry = await configure(page, id)
  entry.picture = picture
  if (entry.hide.length) {
    entry.patch = picture + '_controls'
    await screenshot(page, entry.patch)
  }
  if (id === 'pSet') {
    entry.alternate = picture + '_off'
    await page.locator('.toggle').evaluateAll(toggles => {
      for (const el of toggles) { el.classList.remove('on'); el.textContent = 'OFF' }
    })
    await screenshot(page, entry.alternate)
    await page.locator('.toggle').evaluateAll(toggles => {
      for (const el of toggles) { el.classList.add('on'); el.textContent = 'ON' }
    })
  }
  if (id === 'pSaveB' || id === 'pSelB') {
    entry.alternate = picture + '_selected'
    await page.locator('.baseline-card').evaluateAll(cards => {
      for (const card of cards) {
        card.classList.add('selected')
        card.querySelector('.mini-btn.orange').classList.add('active')
      }
    })
    await screenshot(page, entry.alternate)
  }
  if (id === 'pMatu') {
    entry.alternate = picture + '_selected'
    await page.locator('.maturity-table tbody tr').evaluateAll(rows => {
      for (const row of rows) row.classList.add('maturity-row-active')
    })
    await screenshot(page, entry.alternate)
  }
  await page.addStyleTag({ content: '[data-k050-patch] {opacity:0 !important}' })
  await screenshot(page, picture)
  delete entry.hide
  layout.pages[id] = entry
  console.log(id, picture)
}

async function renderLocals(page) {
  const pages = JSON.parse(execFileSync(python, [generator, '--local-layout'], { encoding: 'utf8' }))
  for (const [name, components] of Object.entries(pages)) {
    const trigger = dialogs[name]
    await page.goto(url + '?screen=' + (trigger ? 'maturityData' : 'userInfo'), { waitUntil: 'domcontentloaded' })
    await page.addStyleTag({ content: style })
    await page.evaluate(() => document.fonts.ready)
    const status = await configure(page, trigger ? 'pMatu' : name)
    let entry
    if (trigger) {
      await page.locator(trigger).first().click()
      await page.locator('.confirm-dialog').waitFor()
      await page.mouse.move(0, 0)
      entry = await renderDialog(page, name, status)
    } else {
      entry = await renderPanel(page, name, components, status)
    }
    entry.picture = 'web_' + name
    if (Object.values(entry.boxes).some(box => box.patch)) {
      entry.patch = entry.picture + '_controls'
      await screenshot(page, entry.patch)
      await page.addStyleTag({ content: '[data-k050-local-patch] {opacity:0 !important}' })
    }
    await screenshot(page, entry.picture)
    layout.pages[name] = entry
    console.log(name, entry.picture, entry.regions.container.join(', '))
  }
}

async function renderDialog(page, name, status) {
  return page.locator('.phone').evaluate((phone, { name, status }) => {
    const dialog = phone.querySelector('.confirm-dialog')
    dialog.classList.add('k050-dialog')
    if (name === 'pConfirm') {
      phone.querySelector('.stage').style.opacity = '0'
      phone.querySelector('.status-corners').remove()
    }
    for (const el of phone.querySelectorAll('[data-k050-patch]')) el.style.opacity = '0'

    const root = phone.getBoundingClientRect()
    const boxes = name === 'pSchedule' ? { tClock: status.boxes.tClock, tBatt: status.boxes.tBatt } : {}
    const regions = name === 'pSchedule' ? { battery: status.regions.battery } : {}
    const box = (el) => {
      const r = el.getBoundingClientRect()
      const x = Math.round(r.left - root.left)
      const y = Math.round(r.top - root.top)
      return [x, y, Math.round(r.right - root.left) - x, Math.round(r.bottom - root.top) - y]
    }
    const record = (name, el, options = {}) => {
      const css = getComputedStyle(el)
      boxes[name] = {
        rect: box(options.target ?? el), kind: options.kind ?? 'text', align: options.align ?? 0,
        font: parseFloat(css.fontSize), color: css.color,
      }
      if (options.baked) Object.assign(boxes[name], { baked: true, value: el.textContent.trim() })
      if (options.live) el.classList.add('k050-value')
      if (options.patch) boxes[name].patch = true
    }
    const makeMessage = (before) => {
      const message = document.createElement('div')
      message.className = 'confirm-body k050-dialog-message'
      message.textContent = ' '
      before.before(message)
      return message
    }
    const actions = dialog.querySelector('.confirm-actions')
    const title = dialog.querySelector('.confirm-title')

    if (name === 'pAddRow') {
      const choices = [...dialog.querySelectorAll('.add-sheet-option')]
      const labels = ['Day 0 — early temp', 'Lab day', 'Fill 0–6 h (0.5 step)']
      const hints = ['Next early-age temperature slot', 'Fc Lab + temperature', 'From the pour start time']
      choices.forEach((button, i) => {
        button.querySelector('strong').textContent = labels[i]
        button.querySelector('span').textContent = hints[i]
      })
      const error = makeMessage(actions)
      choices.forEach((button, i) => record(['mEarly', 'mLab', 'mFill'][i], button, { kind: 'touch' }))
      record('mClose', actions.querySelector('button'), { kind: 'touch' })
      record('tError', error)
    } else if (name === 'pSchedule') {
      const list = dialog.querySelector('.schedule-list')
      const hint = dialog.querySelector('.add-sheet-hint')
      hint.textContent = 'Locked from start 00-00-0000 00:00:00'
      const rows = [...list.querySelectorAll('.schedule-row:not(.schedule-row-head)')]
      if (rows.length !== 5) throw new Error('Sample schedule requires five export rows')
      const notice = makeMessage(actions)
      regions.rows = rows.map(box)
      rows.forEach((row, i) => {
        row.dataset.k050LocalPatch = '1'
        for (const [col, prefix] of ['Day', 'Hari', 'Date', 'Tim'].entries()) {
          record('t' + prefix + i, row.children[col], { live: true, patch: true })
        }
      })
      record('tPour', hint, { live: true })
      record('tNotice', notice)
      record('mClose', actions.querySelector('button'), { kind: 'touch' })
    } else {
      title.textContent = 'Confirm change'
      const body = dialog.querySelector('.confirm-body')
      body.textContent = 'Replace the active measurement?'
      const error = makeMessage(actions)
      const [no, yes] = actions.querySelectorAll('button')
      yes.querySelector('.btn-label').textContent = 'CONFIRM'
      record('tBody', body, { live: true })
      record('tError', error)
      record('mNo', no, { kind: 'touch' })
      record('mYes', yes, { kind: 'touch' })
    }
    record('tTitle', title, { baked: true })
    regions.container = box(dialog)
    return { boxes, regions }
  }, { name, status }).then(entry => verifyLocalLayout(name, entry))
}

async function renderPanel(page, name, components, status) {
  return page.locator('.phone').evaluate((phone, { components, name, status }) => {
    const screen = phone.querySelector('.screen')
    const showStatus = components.some(c => c.name === 'tClock')
    screen.className = showStatus ? 'screen has-status' : 'screen'
    screen.querySelector('.stage').remove()
    if (!showStatus) screen.querySelector('.status-corners').remove()
    screen.querySelector('.k050-notice')?.remove()
    const panel = document.createElement('div')
    panel.className = 'panel k050-local'
    screen.append(panel)
    const boxes = showStatus ? { tClock: status.boxes.tClock, tBatt: status.boxes.tBatt } : {}
    const regions = showStatus ? { battery: status.regions.battery } : {}
    const primary = new Set(['kSave', 'mSave'])
    const keys = /^(k\d\d|kN\d|kDot|kMinus)$/
    const top = {
      pEdit: { tTitle: [124, 40], tInput: [179, 50], tError: [231, 33] },
      pNumber: { tTitle: [120, 38], tInput: [172, 50], tError: [223, 34] },
      pClock: {},
      pPoints: {},
      pChart: {},
    }
    const root = phone.getBoundingClientRect()
    const box = (el) => {
      const r = el.getBoundingClientRect()
      const x = Math.round(r.left - root.left)
      const y = Math.round(r.top - root.top)
      return [x, y, Math.round(r.right - root.left) - x, Math.round(r.bottom - root.top) - y]
    }
    if (name === 'pChart') {
      const chart = document.createElement('div')
      chart.className = 'br-inner br-inner-chart k050-chart-frame'
      screen.append(chart)
      const [x, y, w, h] = box(chart)
      regions.plotSurface = [x, y, w, h]
      regions.plot = [x + 36, y + 14, w - 62, h - 52]
    }
    for (const c of components) {
      if (!Number.isInteger(c.x) || !['button', 'text'].includes(c.type)) continue
      if (c.name === 'tClock' || c.name === 'tBatt') continue
      const visual = document.createElement(c.type === 'button' ? 'button' : 'div')
      const isKey = keys.test(c.name)
      visual.className = 'k050-local-slot'
      if (c.type === 'button') {
        visual.type = 'button'
        visual.classList.add('btn', primary.has(c.name) ? 'btn-orange' : 'btn-dark')
      } else if (c.name === 'tInput' || c.events?.includes('up')) {
        visual.classList.add('text-input')
      } else if (c.name === 'tTitle') {
        visual.classList.add('panel-title')
      } else {
        visual.classList.add('panel-sub')
        if (name === 'pPoints' && /^t[A-Z]\w*\d$/.test(c.name)) visual.classList.add('k050-reading')
      }
      const [y, h] = top[name][c.name] ?? [c.y, c.h]
      const font = c.name === 'tTitle' ? 22 : c.font === 'NotoSans28' ? 24 : c.font === 'NotoSans20' ? 19 : 16
      Object.assign(visual.style, {
        left: c.x + 'px', top: y + 'px', width: c.w + 'px', height: h + 'px',
        minHeight: '0', padding: 0, fontSize: font + 'px',
      })
      const caption = document.createElement('span')
      caption.textContent = c.txt ?? ''
      const dynamic = isKey || !c.txt
      if (dynamic) caption.className = 'k050-value'
      visual.append(caption)
      screen.append(visual)
      const css = getComputedStyle(visual)
      boxes[c.name] = {
        rect: box(visual), kind: c.type === 'button' && !isKey ? 'paint' : 'text',
        font: parseFloat(css.fontSize), align: 1, color: css.color,
        baked: Boolean(c.txt && !dynamic), touch: c.events?.includes('up') ?? false,
      }
      if ((name === 'pNumber' && isKey) || c.name === 'kProbe' ||
          name === 'pPoints' && /^t(Day|Date|Time|Temp|M|Fc)\d$|^mGap\d$/.test(c.name)) {
        visual.dataset.k050LocalPatch = '1'
        boxes[c.name].patch = true
      }
      if (c.name === 'tTitle') {
        const rule = document.createElement('div')
        rule.className = 'panel-rule k050-local-rule'
        rule.style.top = (y + h + 3) + 'px'
        rule.style.left = Math.max(20, c.x) + 'px'
        screen.append(rule)
      }
    }
    if (name === 'pPoints') {
      regions.rows = Array.from({ length: 6 }, (_, i) => {
        const [x, y, , h] = boxes['tDay' + i].rect
        const [lastX, , w] = boxes['mGap' + i].rect
        return [x, y, lastX + w - x, h]
      })
    }
    regions.container = box(panel)
    return { boxes, regions }
  }, { components, name, status }).then(entry => verifyLocalLayout(name, entry))
}

function verifyLocalLayout(name, entry) {
  function contains([x, y, w, h], [cx, cy, cw, ch]) {
    return cx >= x && cy >= y && cx + cw <= x + w && cy + ch <= y + h
  }
  const frame = entry.regions.container
  if (!contains([0, 0, 480, 800], frame) || Math.abs(frame[0] * 2 + frame[2] - 480) > 2) {
    throw new Error(name + ' panel is outside the centered canvas: ' + frame)
  }
  for (const [part, spec] of Object.entries(entry.boxes)) {
    if (['tClock', 'tBatt'].includes(part) || (name === 'pPoints' && part === 'tNotice')) continue
    if (!contains(frame, spec.rect)) throw new Error(name + '.' + part + ' falls outside its panel: ' + spec.rect)
    if ((spec.touch || ['touch', 'paint'].includes(spec.kind)) && (spec.rect[2] < 44 || spec.rect[3] < 48)) {
      throw new Error(name + '.' + part + ' has a touch target smaller than 44 × 48 px')
    }
  }
  if (name === 'pChart') {
    const [title, axes, plot] = [entry.boxes.tTitle.rect, entry.boxes.tAxes.rect, entry.regions.plotSurface]
    if (title[1] + title[3] > axes[1] || axes[1] + axes[3] > plot[1]) {
      throw new Error('Chart title, axis label and plot overlap')
    }
  }
  return entry
}
