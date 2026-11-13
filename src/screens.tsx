import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  BtnGhost,
  BtnPrimary,
  ConfirmDialog,
  FieldBlock,
  MaturityChart,
  MenuRow,
  NavFooter,
  Screen,
  SectionTitle,
  StatusCorners,
  StatusPill,
  TempStrip,
  TextInput,
  UnitBox,
} from './components'
import type { MaturityRow } from './types'
import {
  IconBuilding,
  IconCalendar,
  IconChart,
  IconCheck,
  IconChip,
  IconClock,
  IconDatabase,
  IconDevice,
  IconDoc,
  IconGear,
  IconInfo,
  IconSave,
  IconSound,
  IconSun,
  IconThermo,
  IconUser,
  IconBaselineNew,
  IconBaselineSaved,
  UiIcon,
} from './icons'
import { DATUM_TEMPS } from './mockData'
import {
  accumulateNurseSaulM,
  fitLogMaturity,
  formatCoeff,
  formatFcEquation,
  nurseSaulIntervalDm,
  nurseSaulMaturityLocked,
} from './maturityFit'
import type { AppState, ScreenId } from './types'

type Props = {
  state: AppState
  setState: (updater: (s: AppState) => AppState) => void
  go: (id: ScreenId) => void
}

function fmtDate(iso: string) {
  const [y, m, d] = iso.split('-')
  if (!d) return iso
  return `${d}-${m}-${y}`
}

function selectedBaseline(state: AppState) {
  return state.baselines.find((b) => b.id === state.selectedBaselineId) ?? state.baselines[0]
}

export function SplashScreen({ go }: Props) {
  const steps = [
    'Starting Application',
    'Loading Database',
    'Checking Sensors',
    'Checking Hardware',
  ]
  const [doneCount, setDoneCount] = useState(0)
  const progress = Math.min(100, Math.round((doneCount / steps.length) * 100))

  useEffect(() => {
    if (doneCount >= steps.length) {
      const t = window.setTimeout(() => go('userInfo'), 700)
      return () => window.clearTimeout(t)
    }
    const t = window.setTimeout(() => setDoneCount((n) => n + 1), 650)
    return () => window.clearTimeout(t)
  }, [doneCount, go, steps.length])

  return (
    <Screen bare>
      <div className="init-body">
        <img className="init-logo" src="/conmt-logo.png" alt="ConMT" />

        <h1 className="init-title">
          <span>CONCRETE MATURITY</span>
          <span className="init-title-accent">MONITORING SYSTEM</span>
        </h1>
        <div className="panel-rule init-rule" />

        <div className="init-progress-head">
          <span>SYSTEM INITIALIZING...</span>
          <strong>{progress || 5}%</strong>
        </div>
        <div className="init-progress-track" aria-hidden>
          <div className="init-progress-fill" style={{ width: `${Math.max(progress, 8)}%` }} />
        </div>

        <ul className="init-steps">
          {steps.map((label, i) => {
            const state = i < doneCount ? 'done' : i === doneCount ? 'active' : 'todo'
            return (
              <li key={label} className={state}>
                <span className="init-step-icon" aria-hidden>
                  {state === 'done' ? '✓' : ''}
                </span>
                {label}
              </li>
            )
          })}
        </ul>
      </div>
    </Screen>
  )
}

export function UserInfoScreen({ state, setState, go }: Props) {
  return (
    <Screen
      title="USER INFORMATION"
      footer={
        <BtnPrimary block iconLeft={<IconSave className="ico ico-xl ico-white" />} onClick={() => go('main')}>
          SAVE
        </BtnPrimary>
      }
    >
      <div className="stack">
        <FieldBlock label="Operator ID" icon={<IconUser className="ico ico-xl ico-white" />}>
          <TextInput
            value={state.operatorId}
            placeholder="Enter Operator ID"
            onChange={(e) => setState((s) => ({ ...s, operatorId: e.target.value }))}
          />
        </FieldBlock>
        <FieldBlock label="Project Name" icon={<IconDoc className="ico ico-xl ico-white" />}>
          <TextInput
            value={state.projectName}
            placeholder="Enter Project Name"
            onChange={(e) => setState((s) => ({ ...s, projectName: e.target.value }))}
          />
        </FieldBlock>
        <FieldBlock label="Date" icon={<IconCalendar className="ico ico-xl ico-white" />}>
          <div className="input-with-icon">
            <TextInput
              type="date"
              value={state.date}
              onChange={(e) => setState((s) => ({ ...s, date: e.target.value }))}
            />
            <IconCalendar className="ico ico-sm ico-white trailing" />
          </div>
        </FieldBlock>
      </div>
    </Screen>
  )
}

export function MainMenuScreen({ go }: Props) {
  return (
    <Screen title="MAIN MENU" className="screen-main-menu">
      <div className="stack menu-stack">
        <MenuRow
          icon={<UiIcon name="menu-baseline" size="lg" className="ico-white" />}
          label="BASELINE"
          onClick={() => go('baselineMenu')}
        />
        <MenuRow
          icon={<UiIcon name="menu-kuat-tekan" size="lg" className="ico-white" />}
          label="KUAT TEKAN"
          onClick={() => go('kuatTekanMenu')}
        />
        <MenuRow
          icon={<UiIcon name="menu-settings" size="lg" className="ico-white" />}
          label="SETTINGS"
          onClick={() => go('settings')}
        />
        <MenuRow
          icon={<UiIcon name="menu-device-info" size="lg" className="ico-white" />}
          label="DEVICE INFO"
          onClick={() => go('deviceInfo')}
        />
      </div>
    </Screen>
  )
}

export function BaselineMenuScreen({ state, setState, go }: Props) {
  return (
    <Screen
      title="BASELINE"
      className="screen-baseline-menu"
      topLeft={
        <button type="button" className="back-chip" onClick={() => go('main')}>
          <UiIcon name="back-chevron" size="back" className="ico-accent" /> BACK
        </button>
      }
    >
      <div className="stack baseline-menu-stack">
        <TempStrip temps={state.measurement.sensorTemps} />
        <MenuRow
          icon={<IconBaselineNew className="ico ico-baseline-new ico-white" />}
          label="NEW BASELINE"
          desc="Create a new concrete model based on laboratory data, material composition, and maturity calculation."
          onClick={() => {
            setState((s) => ({
              ...s,
              baselineDraft: { ...s.baselineDraft, pourClock: nowPourClock() },
            }))
            go('newBaseline')
          }}
        />
        <MenuRow
          icon={<IconBaselineSaved className="ico ico-baseline-saved ico-white" />}
          label="SAVED BASELINE"
          desc="View, manage, and use existing concrete models for strength prediction."
          onClick={() => go('savedBaseline')}
        />
      </div>
    </Screen>
  )
}

export function NewBaselineScreen({ state, setState, go }: Props) {
  const d = state.baselineDraft

  return (
    <Screen
      title="NEW BASELINE"
      rule="short"
      footer={<NavFooter onBack={() => go('baselineMenu')} onNext={() => go('materialData')} />}
    >
      <div className="stack">
        <FieldBlock label="Baseline Name">
          <TextInput
            value={d.name}
            onChange={(e) =>
              setState((s) => ({ ...s, baselineDraft: { ...s.baselineDraft, name: e.target.value } }))
            }
          />
        </FieldBlock>
        <FieldBlock label="Target Fc'">
          <div className="row-unit">
            <TextInput
              value={d.targetFc}
              onChange={(e) =>
                setState((s) => ({
                  ...s,
                  baselineDraft: { ...s.baselineDraft, targetFc: e.target.value },
                }))
              }
            />
            <UnitBox>MPa</UnitBox>
          </div>
        </FieldBlock>
        <FieldBlock label="Datum Temperature">
          <div className="row-unit">
            <select
              className="select-input"
              value={d.datumTemp}
              onChange={(e) =>
                setState((s) => ({
                  ...s,
                  baselineDraft: { ...s.baselineDraft, datumTemp: e.target.value },
                }))
              }
            >
              <option value="" disabled>
                Select Temperature
              </option>
              {DATUM_TEMPS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <UnitBox>°C</UnitBox>
          </div>
        </FieldBlock>
      </div>
    </Screen>
  )
}

export function MaterialDataScreen({ state, setState, go }: Props) {
  const d = state.baselineDraft
  const wc = useMemo(() => {
    const c = Number(d.cement)
    const w = Number(d.water)
    if (!c || !w) return '—'
    return (w / c).toFixed(2)
  }, [d.cement, d.water])

  const set = (key: keyof typeof d, value: string) =>
    setState((s) => ({ ...s, baselineDraft: { ...s.baselineDraft, [key]: value } }))

  return (
    <Screen
      title="MATERIAL DATA"
      rule="short"
      footer={
        <NavFooter
          onBack={() => go('newBaseline')}
          onNext={() => {
            setState((s) => ({ ...s, baselineEntry: 'create' }))
            go('maturityData')
          }}
        />
      }
    >
      <div className="stack">
        <SectionTitle>Concrete Material</SectionTitle>
        <MaterialRow label="Cement" value={d.cement} unit="kg" onChange={(v) => set('cement', v)} />
        <MaterialRow label="Water" value={d.water} unit="liter" onChange={(v) => set('water', v)} />
        <div className="material-row readonly">
          <span>W/C Ratio</span>
          <input className="text-input compact" value={wc} readOnly />
          <UnitBox>Auto Calculated</UnitBox>
        </div>
        <MaterialRow
          label="Coarse Aggregate"
          value={d.coarseAgg}
          unit="kg"
          onChange={(v) => set('coarseAgg', v)}
        />
        <MaterialRow
          label="Fine Aggregate"
          value={d.fineAgg}
          unit="kg"
          onChange={(v) => set('fineAgg', v)}
        />

        <hr className="sep" />
        <SectionTitle>Admixture</SectionTitle>
        <AdmixRow
          label="Retarder"
          pct={d.retarderPct}
          brand={d.retarderBrand}
          onPct={(v) => set('retarderPct', v)}
          onBrand={(v) => set('retarderBrand', v)}
        />
        <AdmixRow
          label="Accelerator"
          pct={d.acceleratorPct}
          brand={d.acceleratorBrand}
          onPct={(v) => set('acceleratorPct', v)}
          onBrand={(v) => set('acceleratorBrand', v)}
        />
        <AdmixRow
          label="Fly Ash"
          pct={d.flyAshPct}
          brand={d.flyAshBrand}
          onPct={(v) => set('flyAshPct', v)}
          onBrand={(v) => set('flyAshBrand', v)}
        />
      </div>
    </Screen>
  )
}

function MaterialRow({
  label,
  value,
  unit,
  onChange,
}: {
  label: string
  value: string
  unit: string
  onChange: (v: string) => void
}) {
  return (
    <div className="material-row">
      <span>{label}</span>
      <input className="text-input compact" value={value} onChange={(e) => onChange(e.target.value)} />
      <UnitBox>{unit}</UnitBox>
    </div>
  )
}

function AdmixRow({
  label,
  pct,
  brand,
  onPct,
  onBrand,
}: {
  label: string
  pct: string
  brand: string
  onPct: (v: string) => void
  onBrand: (v: string) => void
}) {
  return (
    <div className="admix-row">
      <span>{label}</span>
      <div className="row-unit tight">
        <input className="text-input compact" value={pct} onChange={(e) => onPct(e.target.value)} />
        <UnitBox>%</UnitBox>
      </div>
      <span className="brand-label">Brand</span>
      <input className="text-input compact" value={brand} onChange={(e) => onBrand(e.target.value)} />
    </div>
  )
}

const MIN_MATURITY_ROWS = 3
const DEFAULT_DAY0_TIME_H = 0.5
/** Day 0 early-age times: every half hour from 0 up to (but not including) Day 1. */
const DAY0_TIME_OPTIONS: number[] = Array.from({ length: 48 }, (_, i) =>
  Number((i * 0.5).toFixed(1)),
)
/** First 6 hours at 0.5 h steps — temp-only rows like the lab Excel sheet. */
const EARLY_0_TO_6H: number[] = DAY0_TIME_OPTIONS.filter((h) => h <= 6)

/**
 * Average only readable sensor channels (skip NaN / missing).
 * 3 live → avg of 3; 2 live → avg of those 2; 0 live → null.
 */
function averageReadableTemps(temps: readonly number[]): { avg: number; count: number } | null {
  const live = temps.filter((t) => Number.isFinite(t))
  if (live.length === 0) return null
  const sum = live.reduce((a, b) => a + b, 0)
  return { avg: +(sum / live.length).toFixed(1), count: live.length }
}

function timeFromDay(day: number): number {
  if (day === 0) return DEFAULT_DAY0_TIME_H
  return Number((day * 24).toFixed(2))
}

function snapDay0Time(h: number): number {
  if (DAY0_TIME_OPTIONS.includes(h)) return h
  return DAY0_TIME_OPTIONS.reduce((best, opt) =>
    Math.abs(opt - h) < Math.abs(best - h) ? opt : best,
  )
}

function parseHHMM(raw: string): { h: number; m: number } | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(raw).trim())
  if (!m) return null
  const h = Number(m[1])
  const min = Number(m[2])
  if (!Number.isFinite(h) || !Number.isFinite(min) || h > 23 || min > 59) return null
  return { h, m: min }
}

function formatHHMM(totalMinutes: number): string {
  const dayMins = 24 * 60
  const mins = ((Math.round(totalMinutes) % dayMins) + dayMins) % dayMins
  const h = Math.floor(mins / 60)
  const min = mins % 60
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`
}

/** Device clock → HH:MM (default Start time = jam sekarang). */
function nowPourClock(date = new Date()): string {
  return formatHHMM(date.getHours() * 60 + date.getMinutes())
}

function normalizePourClock(raw: string): string {
  const p = parseHHMM(raw)
  if (!p) return nowPourClock()
  return formatHHMM(p.h * 60 + p.m)
}

/** Elapsed age hours → wall clock from pour start (e.g. 13:00 + 0.5 h → 13:30). */
function elapsedToClock(pourClock: string, timeH: number): string {
  const normalized = normalizePourClock(pourClock)
  const p = parseHHMM(normalized) ?? parseHHMM(nowPourClock()) ?? { h: 0, m: 0 }
  return formatHHMM(p.h * 60 + p.m + Math.round(timeH * 60))
}

/** Next half-hour slot not already used by an existing Day 0 row. */
function nextDay0Time(rows: MaturityRow[]): number {
  const used = new Set(
    rows.filter((r) => r.day === 0).map((r) => snapDay0Time(r.timeH)),
  )
  return DAY0_TIME_OPTIONS.find((h) => !used.has(h)) ?? DEFAULT_DAY0_TIME_H
}

/** Next unique lab day (≥ 1). Day 0 may repeat separately. */
function nextLabDay(rows: MaturityRow[]): number {
  const used = new Set(rows.filter((r) => r.day !== 0).map((r) => r.day))
  let d = 1
  while (used.has(d)) d += 1
  return d
}

function sortMaturityRows(rows: MaturityRow[]): MaturityRow[] {
  return [...rows].sort((a, b) => a.day - b.day || a.timeH - b.timeH)
}

export function MaturityDataScreen({ state, setState, go }: Props) {
  const rows = state.baselineDraft.rows
  const pourClock = normalizePourClock(state.baselineDraft.pourClock || nowPourClock())
  const canDelete = rows.length > MIN_MATURITY_ROWS
  const [pendingDelete, setPendingDelete] = useState<number | null>(null)
  const [addSheetOpen, setAddSheetOpen] = useState(false)
  const [timePickerRow, setTimePickerRow] = useState<number | null>(null)
  const [focusDayIndex, setFocusDayIndex] = useState<number | null>(null)
  const [dayDraft, setDayDraft] = useState<{ i: number; value: string } | null>(null)
  const [clockDraft, setClockDraft] = useState<string | null>(null)
  const [activeRow, setActiveRow] = useState<number | null>(null)
  const [sensorHint, setSensorHint] = useState<string | null>(null)
  const [sensorBusy, setSensorBusy] = useState(false)
  const dayInputRefs = useRef<(HTMLInputElement | null)[]>([])
  const nextLab = nextLabDay(rows)
  const clockLabel = (timeH: number) => elapsedToClock(pourClock, timeH)
  const timePickerValue =
    timePickerRow != null && rows[timePickerRow]?.day === 0
      ? snapDay0Time(rows[timePickerRow].timeH)
      : null

  useEffect(() => {
    if (focusDayIndex == null) return
    dayInputRefs.current[focusDayIndex]?.focus()
    dayInputRefs.current[focusDayIndex]?.select()
    setFocusDayIndex(null)
  }, [focusDayIndex, rows.length])

  useEffect(() => {
    if (activeRow != null && activeRow >= rows.length) setActiveRow(null)
  }, [activeRow, rows.length])

  useEffect(() => {
    if (!sensorHint) return
    const t = window.setTimeout(() => setSensorHint(null), 2200)
    return () => window.clearTimeout(t)
  }, [sensorHint])

  const setRows = (next: MaturityRow[]) =>
    setState((s) => ({ ...s, baselineDraft: { ...s.baselineDraft, rows: next } }))

  const updateField = (i: number, key: 'fcLab' | 'temperature', value: string) => {
    setRows(rows.map((r, idx) => (idx === i ? { ...r, [key]: value } : r)))
  }

  const updateDay0Time = (i: number, timeH: number) => {
    setRows(
      sortMaturityRows(
        rows.map((r, idx) => (idx === i && r.day === 0 ? { ...r, timeH } : r)),
      ),
    )
  }

  const commitDay = (i: number, raw: string) => {
    const day = Number(raw)
    let next = rows
    // Day 0 may repeat (early-age samples at different hours). Other days stay unique.
    const dayTaken =
      day !== 0 && rows.some((r, idx) => idx !== i && r.day === day)
    if (Number.isFinite(day) && day >= 0 && !dayTaken) {
      next = rows.map((r, idx) => {
        if (idx !== i) return r
        const timeH =
          day === 0
            ? r.day === 0
              ? snapDay0Time(r.timeH)
              : nextDay0Time(rows.filter((_, j) => j !== i))
            : timeFromDay(day)
        return { ...r, day, timeH }
      })
    }
    setRows(sortMaturityRows(next))
    setDayDraft(null)
  }

  const focusNewRow = (next: MaturityRow[], pred: (r: MaturityRow) => boolean) => {
    const focusAt = next.findIndex(pred)
    setRows(next)
    setFocusDayIndex(focusAt >= 0 ? focusAt : next.length - 1)
    setActiveRow(focusAt >= 0 ? focusAt : next.length - 1)
    setAddSheetOpen(false)
  }

  const addDay0 = () => {
    const timeH = nextDay0Time(rows)
    const next = sortMaturityRows([
      ...rows,
      { day: 0, timeH, fcLab: '', temperature: '' },
    ])
    focusNewRow(
      next,
      (r) => r.day === 0 && r.timeH === timeH && r.fcLab === '' && r.temperature === '',
    )
    setSensorHint(`Day 0 @ ${clockLabel(timeH)} — fill Temperature`)
  }

  const addLabDay = () => {
    const day = nextLabDay(rows)
    const next = sortMaturityRows([
      ...rows,
      { day, timeH: timeFromDay(day), fcLab: '', temperature: '' },
    ])
    focusNewRow(next, (r) => r.day === day && r.fcLab === '' && r.temperature === '')
    setSensorHint(`Day ${day} @ ${clockLabel(timeFromDay(day))} — fill Fc Lab + Temperature`)
  }

  const commitPourClock = (raw: string) => {
    const next = normalizePourClock(raw)
    setState((s) => ({
      ...s,
      baselineDraft: { ...s.baselineDraft, pourClock: next },
    }))
    setClockDraft(null)
  }

  const fillEarly0to6h = () => {
    const used = new Set(
      rows.filter((r) => r.day === 0).map((r) => snapDay0Time(r.timeH)),
    )
    const toAdd = EARLY_0_TO_6H.filter((h) => !used.has(h)).map((timeH) => ({
      day: 0,
      timeH,
      fcLab: '',
      temperature: '',
    }))
    if (toAdd.length === 0) {
      setSensorHint('0–6 h Day 0 slots already present')
      setAddSheetOpen(false)
      return
    }
    const next = sortMaturityRows([...rows, ...toAdd])
    const firstNew = toAdd[0].timeH
    focusNewRow(
      next,
      (r) => r.day === 0 && r.timeH === firstNew && r.fcLab === '' && r.temperature === '',
    )
    setSensorHint(`Added ${toAdd.length} Day 0 rows (0–6 h) — fill Temperature`)
  }

  const readSensorIntoActiveRow = () => {
    if (activeRow == null || !rows[activeRow]) {
      setSensorHint('Select a temperature row first')
      return
    }
    const target = activeRow
    const day = rows[target].day
    setSensorBusy(true)
    // Preview: avg of readable channels only (2 of 3 live → avg of 2). MCU pushes via serial.
    window.setTimeout(() => {
      const result = averageReadableTemps(state.measurement.sensorTemps)
      if (!result) {
        setSensorHint('No sensor reading available')
        setSensorBusy(false)
        return
      }
      const reading = result.avg.toFixed(1)
      setState((s) => ({
        ...s,
        baselineDraft: {
          ...s.baselineDraft,
          rows: s.baselineDraft.rows.map((r, idx) =>
            idx === target ? { ...r, temperature: reading } : r,
          ),
        },
      }))
      setSensorHint(`Day ${day}: ${reading} °C (avg ${result.count} sensor${result.count > 1 ? 's' : ''})`)
      setSensorBusy(false)
    }, 450)
  }

  const confirmDelete = () => {
    if (pendingDelete == null || rows.length <= MIN_MATURITY_ROWS) {
      setPendingDelete(null)
      return
    }
    setRows(rows.filter((_, idx) => idx !== pendingDelete))
    if (activeRow === pendingDelete) setActiveRow(null)
    else if (activeRow != null && pendingDelete < activeRow) setActiveRow(activeRow - 1)
    setPendingDelete(null)
  }

  const pendingRow = pendingDelete != null ? rows[pendingDelete] : null

  return (
    <Screen
      title="MATURITY DATA INPUT"
      footer={
        <NavFooter
          onBack={() =>
            go(state.baselineEntry === 'saved' ? 'savedBaseline' : 'materialData')
          }
          onNext={() => go('baselineResult')}
          nextLabel="GENERATE BASELINE"
          nextClassName="btn-fs-10"
          backClassName="btn-fs-10"
          backWithChevron={false}
        />
      }
      overlay={
        pendingRow ? (
          <ConfirmDialog
            title={`Delete day ${pendingRow.day}?`}
            body={
              <>
                <div>Fc Lab: {pendingRow.fcLab || '—'} MPa</div>
                <div>Temperature: {pendingRow.temperature || '—'} °C</div>
                <p>This row will be removed from the maturity table.</p>
              </>
            }
            onCancel={() => setPendingDelete(null)}
            onConfirm={confirmDelete}
          />
        ) : addSheetOpen ? (
          <div
            className="confirm-overlay"
            role="presentation"
            onClick={() => setAddSheetOpen(false)}
          >
            <div
              className="confirm-dialog add-sheet"
              role="dialog"
              aria-modal="true"
              aria-labelledby="add-sheet-title"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 id="add-sheet-title" className="confirm-title">
                Add row
              </h2>
              <p className="add-sheet-hint">Choose early-age temperature or a lab day.</p>
              <div className="add-sheet-options">
                <button type="button" className="add-sheet-option" onClick={addDay0}>
                  <strong>Day 0 — early temp</strong>
                  <span>Next slot {clockLabel(nextDay0Time(rows))}</span>
                </button>
                <button type="button" className="add-sheet-option" onClick={addLabDay}>
                  <strong>Lab day {nextLab}</strong>
                  <span>Fc Lab + temperature · {clockLabel(timeFromDay(nextLab))}</span>
                </button>
                <button type="button" className="add-sheet-option" onClick={fillEarly0to6h}>
                  <strong>Fill 0–6 h (0.5 step)</strong>
                  <span>
                    {clockLabel(0)} → {clockLabel(6)} from start
                  </span>
                </button>
              </div>
              <div className="confirm-actions">
                <BtnGhost onClick={() => setAddSheetOpen(false)}>CANCEL</BtnGhost>
              </div>
            </div>
          </div>
        ) : timePickerRow != null && timePickerValue != null ? (
          <div
            className="confirm-overlay"
            role="presentation"
            onClick={() => setTimePickerRow(null)}
          >
            <div
              className="confirm-dialog time-picker-sheet"
              role="dialog"
              aria-modal="true"
              aria-labelledby="time-picker-title"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 id="time-picker-title" className="confirm-title">
                Select time
              </h2>
              <p className="add-sheet-hint">From start {pourClock} (jam 0)</p>
              <div className="time-picker-list" role="listbox" aria-label="Clock times">
                {DAY0_TIME_OPTIONS.map((h) => {
                  const selected = h === timePickerValue
                  return (
                    <button
                      key={h}
                      type="button"
                      role="option"
                      aria-selected={selected}
                      className={`time-picker-option${selected ? ' is-selected' : ''}`}
                      onClick={() => {
                        updateDay0Time(timePickerRow, h)
                        setActiveRow(timePickerRow)
                        setTimePickerRow(null)
                      }}
                    >
                      {clockLabel(h)}
                    </button>
                  )
                })}
              </div>
              <div className="confirm-actions">
                <BtnGhost onClick={() => setTimePickerRow(null)}>CANCEL</BtnGhost>
              </div>
            </div>
          </div>
        ) : null
      }
    >
      <div className="stack">
        <div className="table-scroll">
          <table className="maturity-table maturity-table-edit">
            <thead>
              <tr>
                <th>Day</th>
                <th>Time</th>
                <th>Fc Lab (MPa)</th>
                <th>Temperature (°C)</th>
                <th aria-label="Delete" />
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr
                  key={`${r.day}-${i}`}
                  className={activeRow === i ? 'maturity-row-active' : undefined}
                  onClick={() => setActiveRow(i)}
                >
                  <td>
                    <input
                      ref={(el) => {
                        dayInputRefs.current[i] = el
                      }}
                      className="day-input"
                      inputMode="decimal"
                      value={dayDraft?.i === i ? dayDraft.value : String(r.day)}
                      onFocus={() => {
                        setActiveRow(i)
                        setDayDraft({ i, value: String(r.day) })
                      }}
                      onChange={(e) => setDayDraft({ i, value: e.target.value })}
                      onBlur={() => commitDay(i, dayDraft?.i === i ? dayDraft.value : String(r.day))}
                    />
                  </td>
                  <td className="time-cell">
                    {r.day === 0 &&
                    !(
                      dayDraft?.i === i &&
                      dayDraft.value.trim() !== '' &&
                      Number.isFinite(Number(dayDraft.value)) &&
                      Number(dayDraft.value) > 0
                    ) ? (
                      <button
                        type="button"
                        className="time-select"
                        aria-label="Day 0 clock time"
                        onClick={(e) => {
                          e.stopPropagation()
                          setActiveRow(i)
                          setTimePickerRow(i)
                        }}
                      >
                        {clockLabel(snapDay0Time(r.timeH))}
                      </button>
                    ) : dayDraft?.i === i &&
                      dayDraft.value.trim() !== '' &&
                      Number.isFinite(Number(dayDraft.value)) &&
                      Number(dayDraft.value) >= 0 ? (
                      clockLabel(timeFromDay(Number(dayDraft.value)))
                    ) : (
                      clockLabel(r.timeH)
                    )}
                  </td>
                  <td>
                    <input
                      value={r.fcLab}
                      onFocus={() => setActiveRow(i)}
                      onChange={(e) => updateField(i, 'fcLab', e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      value={r.temperature}
                      onFocus={() => setActiveRow(i)}
                      onChange={(e) => updateField(i, 'temperature', e.target.value)}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="row-del"
                      aria-label={`Delete day ${r.day}`}
                      disabled={!canDelete}
                      onClick={(e) => {
                        e.stopPropagation()
                        setPendingDelete(i)
                      }}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="maturity-actions">
          <button type="button" className="add-day-btn" onClick={() => setAddSheetOpen(true)}>
            + ADD DAY
          </button>
          <button
            type="button"
            className="sensor-btn"
            onClick={readSensorIntoActiveRow}
            disabled={sensorBusy}
            aria-label="Read temperature sensor into selected row"
          >
            <IconThermo className="ico ico-accent ico-md" />
            {sensorBusy ? 'READING…' : 'SENSOR'}
          </button>
        </div>
        <div className="info-box">
          <div className="pour-clock-row">
            <span>Start time</span>
            <input
              className="pour-clock-input"
              inputMode="numeric"
              placeholder={nowPourClock()}
              aria-label="Pour start clock time"
              value={clockDraft ?? pourClock}
              onFocus={() => setClockDraft(pourClock)}
              onChange={(e) => setClockDraft(e.target.value)}
              onBlur={() => commitPourClock(clockDraft ?? pourClock)}
            />
            <span className="pour-clock-eq">= jam 0</span>
          </div>
          <div>Datum Temperature: {state.baselineDraft.datumTemp} °C</div>
          <div>Formula: M = Σ(T − T₀)Δt</div>
          <p>
            {sensorHint ??
              (activeRow == null
                ? 'Tap a row, then SENSOR to fill Temperature (°C).'
                : `Active: Day ${rows[activeRow]?.day} @ ${clockLabel(rows[activeRow].timeH)} — SENSOR fills this row.`)}
          </p>
        </div>
      </div>
    </Screen>
  )
}

export function BaselineResultScreen({ state, setState, go }: Props) {
  const d = state.baselineDraft
  const datumTemp = Number(d.datumTemp)
  const t0 = Number.isFinite(datumTemp) ? datumTemp : -20
  // Excel: M = Σ((T_i+T_{i-1})/2 − T₀)·Δt over all temp rows; plot only ages with Fc Lab.
  const samples = d.rows
    .map((r) => {
      const timeH = Number(r.timeH)
      const temp = Number(r.temperature)
      const fc = Number(r.fcLab)
      if (!Number.isFinite(timeH) || !Number.isFinite(temp)) return null
      return { timeH, temp, fc }
    })
    .filter((s): s is { timeH: number; temp: number; fc: number } => s != null)
  const withM = accumulateNurseSaulM(samples, t0)
  const points = withM
    .filter((s) => Number.isFinite(s.fc) && s.fc > 0 && s.m > 0)
    .map((s) => ({ x: s.m, y: s.fc }))
    .sort((a, b) => a.x - b.x)

  const fit = fitLogMaturity(points)

  const save = () => {
    setState((s) => {
      const id = `b${Date.now()}`
      return {
        ...s,
        baselines: [
          {
            id,
            name: d.name,
            targetFc: Number(d.targetFc) || 0,
            datumTemp: Number(d.datumTemp) || 0,
            createdAt: fmtDate(s.date),
            cement: Number(d.cement) || 0,
            water: Number(d.water) || 0,
            coarseAgg: Number(d.coarseAgg) || 0,
            fineAgg: Number(d.fineAgg) || 0,
            retarder: { pct: Number(d.retarderPct) || 0, brand: d.retarderBrand },
            accelerator: { pct: Number(d.acceleratorPct) || 0, brand: d.acceleratorBrand },
            flyAsh: { pct: Number(d.flyAshPct) || 0, brand: d.flyAshBrand },
            rows: d.rows.map((r) => ({ ...r })),
            coeffA: fit?.a,
            coeffB: fit?.b,
            r2: fit?.r2,
          },
          ...s.baselines,
        ],
        selectedBaselineId: id,
      }
    })
    go('savedBaseline')
  }

  const modelRows: [string, string][] = [
    ['Baseline Name', d.name],
    ["Target Fc'", `${d.targetFc} MPa`],
    ['Datum Temperature', `${d.datumTemp} °C`],
    ['Created Date', fmtDate(state.date)],
    ['Operator ID', state.operatorId],
    ['Project Name', state.projectName],
  ]

  return (
    <div className="screen has-status">
      <div className="screen-bg" aria-hidden />
      <div className="brand-bar" aria-hidden />
      <StatusCorners />
      <button type="button" className="back-chip br-back" onClick={() => go('maturityData')}>
        <UiIcon name="back-chevron" size="back" className="ico-accent" /> BACK
      </button>
      <div className="br-stage">
        <header className="br-title-block">
          <h1 className="br-title">BASELINE CALCULATION RESULT</h1>
          <div className="panel-rule panel-rule-short br-title-rule" />
        </header>

        <div className="br-cards">
          <section className="br-card">
            <div className="br-card-head">
              <span className="num">1</span>
              <h3>Model Information</h3>
            </div>
            <div className="br-inner">
              {modelRows.map(([label, value]) => (
                <div className="br-kv" key={label}>
                  <span>{label}</span>
                  <span className="br-colon">:</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          </section>

          <section className="br-card">
            <div className="br-card-head">
              <span className="num">2</span>
              <h3>Maturity vs Compressive Strength</h3>
            </div>
            <div className="br-inner br-inner-chart">
              <MaturityChart points={points} fit={fit} compact />
            </div>
          </section>

          <section className="br-card">
            <div className="br-card-head">
              <span className="num">3</span>
              <h3>Equation and Coefficient</h3>
            </div>
            <div className="br-inner br-inner-eq">
              <div className="br-equation">
                {fit ? formatFcEquation(fit.a, fit.b) : 'fc = a + b ln(M)'}
              </div>
              <div className="br-kv">
                <span>Coefficient a</span>
                <span className="br-colon">:</span>
                <strong>{fit ? formatCoeff(fit.a, 3) : '—'}</strong>
              </div>
              <div className="br-kv">
                <span>Coefficient b</span>
                <span className="br-colon">:</span>
                <strong>{fit ? formatCoeff(fit.b, 4) : '—'}</strong>
              </div>
              <div className="br-kv">
                <span>R²</span>
                <span className="br-colon">:</span>
                <strong>{fit ? formatCoeff(fit.r2, 4) : '—'}</strong>
              </div>
            </div>
          </section>
        </div>

        <div className="br-save">
          <BtnPrimary
            className="br-save-btn"
            iconLeft={<IconSave className="ico ico-xl ico-white" />}
            onClick={save}
          >
            SAVE
          </BtnPrimary>
        </div>
      </div>
    </div>
  )
}

export function SavedBaselineScreen({ state, setState, go }: Props) {
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const select = (id: string) => setState((s) => ({ ...s, selectedBaselineId: id }))
  const pending = state.baselines.find((b) => b.id === pendingDeleteId) ?? null

  const confirmDelete = () => {
    if (!pendingDeleteId) return
    const id = pendingDeleteId
    setPendingDeleteId(null)
    setState((s) => {
      const next = s.baselines.filter((x) => x.id !== id)
      return {
        ...s,
        baselines: next,
        selectedBaselineId: s.selectedBaselineId === id ? next[0]?.id ?? null : s.selectedBaselineId,
      }
    })
  }

  return (
    <Screen
      title="SAVED BASELINE"
      rule="short"
      footer={
        <NavFooter
          onBack={() => go('baselineMenu')}
          onNext={() => {
            if (!state.selectedBaselineId) return
            setState((s) => ({ ...s, baselineEntry: 'saved' }))
            go('maturityData')
          }}
          nextLabel="SELECT"
        />
      }
      overlay={
        pending ? (
          <ConfirmDialog
            title="Delete baseline?"
            body={
              <>
                <div>
                  <strong>{pending.name}</strong>
                </div>
                <div>
                  Target Fc&apos;: {pending.targetFc} MPa · Datum: {pending.datumTemp} °C
                </div>
                <p>This baseline will be removed from the saved list.</p>
              </>
            }
            onCancel={() => setPendingDeleteId(null)}
            onConfirm={confirmDelete}
          />
        ) : null
      }
    >
      <div className="stack gap-sm">
        {state.baselines.map((b) => {
          const selected = state.selectedBaselineId === b.id
          return (
            <div
              key={b.id}
              role="button"
              tabIndex={0}
              className={`baseline-card selectable${selected ? ' selected' : ''}`}
              onClick={() => select(b.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  select(b.id)
                }
              }}
            >
              <IconDatabase className="ico ico-accent card-ico" />
              <div className="baseline-card-body">
                <strong>{b.name}</strong>
                <div className="triple">
                  <span>
                    Target Fc' <b>{b.targetFc} MPa</b>
                  </span>
                  <span>
                    Datum Temp. <b>{b.datumTemp} °C</b>
                  </span>
                  <span>
                    Created <b>{b.createdAt}</b>
                  </span>
                </div>
              </div>
              <div className="card-actions">
                <button
                  type="button"
                  className={`mini-btn orange${selected ? ' active' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation()
                    select(b.id)
                  }}
                >
                  SELECT
                </button>
                <button
                  type="button"
                  className="mini-btn dark"
                  onClick={(e) => {
                    e.stopPropagation()
                    setPendingDeleteId(b.id)
                  }}
                >
                  DELETE
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </Screen>
  )
}

export function KuatTekanMenuScreen({ state, go }: Props) {
  return (
    <Screen
      title="KUAT TEKAN"
      className="screen-kuat-tekan-menu"
      subtitle="Select menu to begin compressive strength prediction."
    >
      <div className="stack kuat-tekan-menu-stack">
        <TempStrip temps={state.measurement.sensorTemps} />
        <button type="button" className="dark-menu-row" onClick={() => go('selectBaseline')}>
          <UiIcon name="kuat-start" size="lg" className="ico-accent" />
          <strong>START TEST</strong>
          <span className="chev">›</span>
        </button>
        <button type="button" className="dark-menu-row" onClick={() => go('history')}>
          <UiIcon name="kuat-history" size="lg" className="ico-accent" />
          <strong>HISTORY</strong>
          <span className="chev">›</span>
        </button>
        <button type="button" className="dark-menu-row" onClick={() => go('main')}>
          <UiIcon name="back-chevron" size="back" className="ico-accent" />
          <strong>BACK</strong>
          <span />
        </button>
      </div>
    </Screen>
  )
}

function sampleSensorTemps(base: [number, number, number]): [number, number, number] {
  return base.map((v) => +(v + (Math.random() - 0.5) * 0.35).toFixed(1)) as [
    number,
    number,
    number,
  ]
}

export function SelectBaselineScreen({ state, setState, go }: Props) {
  const select = (id: string) => setState((s) => ({ ...s, selectedBaselineId: id }))

  const startMeasurement = () => {
    if (!state.selectedBaselineId) return
    const sensorTemps = sampleSensorTemps(state.measurement.sensorTemps)
    const initialPourTemp = averageReadableTemps(sensorTemps)?.avg ?? 0
    const pourStartMs = Date.now()
    setState((s) => ({
      ...s,
      measurement: {
        pourStartMs,
        endMs: null,
        initialPourTemp,
        avgTemp: initialPourTemp,
        maturityIndex: 0,
        sensorTemps,
      },
    }))
    go('realtime')
  }

  return (
    <Screen
      title="SELECT BASELINE"
      rule="short"
      footer={
        <NavFooter
          onBack={() => go('kuatTekanMenu')}
          onNext={startMeasurement}
          nextLabel="START"
        />
      }
    >
      <div className="stack gap-sm">
        {state.baselines.map((b) => {
          const selected = state.selectedBaselineId === b.id
          return (
            <div
              key={b.id}
              role="button"
              tabIndex={0}
              aria-pressed={selected}
              className={`baseline-card selectable${selected ? ' selected' : ''}`}
              onClick={() => select(b.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  select(b.id)
                }
              }}
            >
              <IconDatabase className="ico ico-accent card-ico" />
              <div className="baseline-card-body">
                <strong>{b.name}</strong>
                <div className="triple">
                  <span>
                    Target Fc' <b>{b.targetFc} MPa</b>
                  </span>
                  <span>
                    Datum Temp. <b>{b.datumTemp} °C</b>
                  </span>
                  <span>
                    Created <b>{b.createdAt}</b>
                  </span>
                </div>
              </div>
              <div className="card-actions">
                <button
                  type="button"
                  className={`mini-btn orange${selected ? ' active' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation()
                    select(b.id)
                  }}
                >
                  SELECT
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </Screen>
  )
}

function formatClock(d: Date) {
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

function formatElapsed(totalSec: number) {
  const sec = Math.max(0, Math.floor(totalSec))
  const hh = String(Math.floor(sec / 3600)).padStart(2, '0')
  const mm = String(Math.floor((sec % 3600) / 60)).padStart(2, '0')
  const ss = String(sec % 60).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

export function RealtimeScreen({ state, setState, go }: Props) {
  const baseline = selectedBaseline(state)
  const [temps, setTemps] = useState<[number, number, number]>(
    () => state.measurement.sensorTemps,
  )
  const pourStartRef = useRef(
    state.measurement.pourStartMs ? new Date(state.measurement.pourStartMs) : new Date(),
  )
  const initialPourTemp = state.measurement.initialPourTemp
  const datumTemp = baseline?.datumTemp ?? -20
  const [now, setNow] = useState(() => new Date())
  const [elapsed, setElapsed] = useState(() =>
    state.measurement.pourStartMs
      ? Math.max(0, Math.floor((Date.now() - state.measurement.pourStartMs) / 1000))
      : 0,
  )
  // Excel Σ: accumulate dM each second with trapezoid ((T_prev+T_now)/2 − T₀)·Δt
  const maturityRef = useRef(0)
  const prevTempRef = useRef(initialPourTemp ?? averageReadableTemps(temps)?.avg ?? 0)
  const caughtUpRef = useRef(false)

  useEffect(() => {
    const startMs = pourStartRef.current.getTime()
    setState((s) =>
      s.measurement.pourStartMs === startMs
        ? s
        : {
            ...s,
            measurement: { ...s.measurement, pourStartMs: startMs, endMs: null },
          },
    )
  }, [setState])

  // If realtime resumed mid-session, catch up M for elapsed so far (one Excel interval).
  useEffect(() => {
    if (caughtUpRef.current) return
    caughtUpRef.current = true
    const tStart = initialPourTemp ?? averageReadableTemps(temps)?.avg ?? 0
    const tNow = averageReadableTemps(temps)?.avg ?? tStart
    if (elapsed > 0) {
      maturityRef.current = nurseSaulMaturityLocked(tStart, tNow, datumTemp, elapsed)
      prevTempRef.current = tNow
    }
  }, [])

  useEffect(() => {
    const t = window.setInterval(() => {
      setElapsed((e) => e + 1)
      setNow(new Date())
      setTemps((prev) => {
        const next = prev.map((v) => +(v + (Math.random() - 0.5) * 0.15).toFixed(1)) as [
          number,
          number,
          number,
        ]
        const tNow = averageReadableTemps(next)?.avg ?? prevTempRef.current
        const tPrev = prevTempRef.current
        maturityRef.current += nurseSaulIntervalDm(tPrev, tNow, datumTemp, 1 / 3600)
        maturityRef.current = Math.max(0, maturityRef.current)
        prevTempRef.current = tNow
        return next
      })
    }, 1000)
    return () => window.clearInterval(t)
  }, [datumTemp])

  const avg = averageReadableTemps(temps)?.avg ?? 0
  const pourStart = formatClock(pourStartRef.current)
  const currentTime = formatClock(now)

  const goToResult = () => {
    const endMs = Date.now()
    // Average Temperature di result = suhu awal penuangan (freeze saat START), bukan avg live saat NEXT.
    const pourAvg = initialPourTemp ?? avg
    // Prefer live Σ; fallback one Excel interval start→lock if accum still ~0 but elapsed > 0.
    let m = maturityRef.current
    if (m < 1e-9 && elapsed > 0) {
      m = nurseSaulMaturityLocked(pourAvg, avg, datumTemp, elapsed)
    }
    const maturityIndex = Math.round(m)
    setState((s) => ({
      ...s,
      measurement: {
        ...s.measurement,
        pourStartMs: pourStartRef.current.getTime(),
        endMs,
        avgTemp: pourAvg,
        maturityIndex,
        sensorTemps: temps,
      },
    }))
    go('strengthResult')
  }

  return (
    <Screen
      title="REAL TIME MEASUREMENT"
      className="screen-realtime"
      footer={<NavFooter onBack={() => go('selectBaseline')} onNext={goToResult} />}
    >
      <div className="stack rt-stack">
        <div className="info-card rt-baseline">
          <IconDoc className="ico ico-accent rt-baseline-ico" />
          <div className="rt-baseline-body">
            <span className="rt-label">Baseline Name</span>
            <strong className="rt-baseline-name">{baseline?.name}</strong>
            <div className="rt-baseline-split">
              <div>
                <span className="rt-label">Target Fc'</span>
                <b>{baseline?.targetFc} MPa</b>
              </div>
              <div>
                <span className="rt-label">Datum Temp.</span>
                <b>{baseline?.datumTemp} °C</b>
              </div>
            </div>
          </div>
        </div>

        <div className="sensor-row">
          {temps.map((t, i) => (
            <div key={i} className="sensor-box">
              <IconThermo className="ico ico-accent ico-md" />
              <span>Sensor {i + 1}</span>
              <strong>{t.toFixed(1)} °C</strong>
            </div>
          ))}
        </div>

        <div className="avg-bar">
          <div className="avg-bar-left">
            <IconChart className="ico ico-accent" />
            <span>Average</span>
          </div>
          <strong>{avg.toFixed(1)} °C</strong>
          <span className="avg-bar-spacer" aria-hidden />
        </div>

        <div className="monitor-card">
          <div className="monitor-head">
            <IconClock className="ico ico-accent" />
            REAL TIME MONITORING
          </div>
          <div className="rt-monitor-grid" role="group" aria-label="Pour monitoring">
            <div className="rt-cell">
              <span className="rt-cell-label">Initial Pour Time</span>
              <strong className="rt-cell-value">{pourStart}</strong>
            </div>
            <div className="rt-cell rt-cell-end">
              <span className="rt-cell-label">Current Time</span>
              <strong className="rt-cell-value rt-clock">{currentTime}</strong>
            </div>
            <div className="rt-cell">
              <span className="rt-cell-label">Initial Temp.</span>
              <strong className="rt-cell-value rt-pour-temp">
                {initialPourTemp != null ? `${initialPourTemp.toFixed(1)} °C` : '—'}
              </strong>
            </div>
            <div className="rt-cell rt-cell-end">
              <span className="rt-cell-label">Status</span>
              <StatusPill>
                <span className="status-spin" aria-hidden />
                RUNNING
              </StatusPill>
            </div>
          </div>
        </div>
      </div>
    </Screen>
  )
}

export function StrengthResultScreen({ state, setState, go }: Props) {
  const baseline = selectedBaseline(state)
  const strength = 35.4
  const m = state.measurement
  const pourStartMs = m.pourStartMs ?? Date.now()
  const endMs = m.endMs ?? Date.now()
  const elapsedLabel = formatElapsed((endMs - pourStartMs) / 1000)
  // Suhu awal penuangan (saat START) — sama dengan Initial Temp. di realtime.
  const avgTemp = m.initialPourTemp ?? m.avgTemp
  const maturityIndex = m.maturityIndex

  const save = () => {
    setState((s) => ({
      ...s,
      history: [
        {
          id: `h${Date.now()}`,
          testId: `TEST-${String(s.history.length + 1).padStart(3, '0')}`,
          baselineName: baseline?.name ?? '—',
          date: fmtDate(s.date),
          time: formatClock(new Date(endMs)),
          strengthMpa: strength,
          avgTemp,
          maturityIndex,
          elapsed: elapsedLabel,
          sensorTemps: s.measurement.sensorTemps,
          operatorId: s.operatorId,
          project: s.projectName,
          targetFc: baseline?.targetFc ?? 0,
          datumTemp: baseline?.datumTemp ?? 0,
          status: 'COMPLETED',
        },
        ...s.history,
      ],
    }))
    go('history')
  }

  return (
    <Screen
      title="STRENGTH PREDICTION RESULT"
      className="screen-strength-result"
      rule="short"
      footer={
        <NavFooter onBack={() => go('realtime')} onNext={save} nextLabel="SAVE RESULT" />
      }
    >
      <div className="stack sr-stack">
        <div className="info-card sr-baseline">
          <IconDoc className="ico ico-accent sr-baseline-ico" />
          <div className="sr-baseline-body">
            <span className="mini-label">Baseline Name</span>
            <strong className="sr-baseline-name">{baseline?.name}</strong>
            <div className="split-line sr-baseline-split">
              <span>
                <span className="mini-label">Target Fc'</span>
                <b>{baseline?.targetFc} MPa</b>
              </span>
              <span>
                <span className="mini-label">Datum Temp.</span>
                <b>{baseline?.datumTemp} °C</b>
              </span>
            </div>
          </div>
        </div>

        <div className="predict-box">
          <div className="predict-box-left">
            <IconChart className="ico ico-accent" />
          </div>
          <div className="predict-box-main">
            <span className="mini-label">Predicted Fc'</span>
            <strong className="huge">{strength.toFixed(1)} MPa</strong>
          </div>
          <span className="predict-box-spacer" aria-hidden />
        </div>

        <div className="sr-metrics">
          <div className="sr-metric">
            <IconThermo className="ico ico-accent" />
            <span>Average Temperature</span>
            <strong>{avgTemp.toFixed(1)} °C</strong>
          </div>
          <div className="sr-metric">
            <IconChart className="ico ico-accent" />
            <span>Maturity Index</span>
            <strong>
              {maturityIndex.toLocaleString()}
              <small>°C·hour</small>
            </strong>
          </div>
          <div className="sr-metric">
            <IconClock className="ico ico-accent" />
            <span>Elapsed Time</span>
            <strong>{elapsedLabel}</strong>
          </div>
        </div>

        <div className="status-card">
          <div className="row-between">
            <span className="with-ico">
              <IconCheck className="ico ico-accent" /> Prediction Status
            </span>
            <StatusPill>
              <span className="status-spin" aria-hidden />
              READY
            </StatusPill>
          </div>
          <p className="footnote">
            <IconInfo className="ico ico-muted" /> Prediction generated from selected baseline and
            real-time temperature measurement.
          </p>
        </div>
      </div>
    </Screen>
  )
}

export function HistoryScreen({ state, setState, go }: Props) {
  const selected = state.selectedHistoryId ?? state.history[0]?.id

  return (
    <Screen
      title="TEST HISTORY"
      className="screen-history"
      rule="short"
      footer={
        <NavFooter
          onBack={() => go('kuatTekanMenu')}
          onNext={() => {
            setState((s) => ({ ...s, selectedHistoryId: selected }))
            go('historyDetail')
          }}
          nextLabel="VIEW DETAIL"
        />
      }
    >
      <div className="stack gap-sm history-list">
        {state.history.map((h) => (
          <button
            key={h.id}
            type="button"
            className={`history-card${selected === h.id ? ' selected' : ''}`}
            onClick={() => setState((s) => ({ ...s, selectedHistoryId: h.id }))}
          >
            <div className="history-top">
              <div className="history-field">
                <span className="mini-label">Test ID</span>
                <strong>{h.testId}</strong>
              </div>
              <div className="history-field grow">
                <span className="mini-label">Baseline Name</span>
                <strong>{h.baselineName}</strong>
              </div>
              <span className="detail-link">
                DETAIL <span aria-hidden>›</span>
              </span>
            </div>
            <div className="history-bottom">
              <div className="history-field">
                <span className="mini-label">Predicted Strength</span>
                <strong className="orange-text">
                  {h.strengthMpa.toFixed(1)}
                  <span> MPa</span>
                </strong>
              </div>
              <div className="history-field">
                <span className="mini-label">Date</span>
                <strong>{h.date}</strong>
              </div>
              <div className="history-field history-status">
                <span className="mini-label">Status</span>
                <StatusPill tone="green">
                  <IconCheck className="ico" /> COMPLETED
                </StatusPill>
              </div>
            </div>
          </button>
        ))}
      </div>
    </Screen>
  )
}

export function HistoryDetailScreen({ state, go }: Props) {
  const h = state.history.find((x) => x.id === state.selectedHistoryId) ?? state.history[0]
  if (!h) {
    return (
      <Screen title="RESULT DETAIL HISTORY" footer={<NavFooter onBack={() => go('history')} />}>
        <p className="panel-sub">No history selected.</p>
      </Screen>
    )
  }

  return (
    <Screen
      title="RESULT DETAIL HISTORY"
      scroll={false}
      bodyClassName="rdh-body"
      footer={
        <div className="rdh-footer">
          <BtnGhost onClick={() => go('history')}>BACK</BtnGhost>
        </div>
      }
    >
      <div className="rdh">
        <div className="rdh-meta">
          <div className="rdh-meta-row three">
            <div className="rdh-cell">
              <IconDoc className="ico ico-accent" />
              <span>Test ID</span>
              <strong>{h.testId}</strong>
            </div>
            <div className="rdh-cell">
              <IconCalendar className="ico ico-accent" />
              <span>Test Date</span>
              <strong>{h.date}</strong>
            </div>
            <div className="rdh-cell">
              <IconClock className="ico ico-accent" />
              <span>Time</span>
              <strong>{h.time}</strong>
            </div>
          </div>
          <div className="rdh-meta-row two">
            <div className="rdh-cell">
              <IconUser className="ico ico-accent" />
              <span>Operator ID</span>
              <strong>{h.operatorId}</strong>
            </div>
            <div className="rdh-cell">
              <IconBuilding className="ico ico-accent" />
              <span>Project</span>
              <strong>{h.project}</strong>
            </div>
          </div>
        </div>

        <div className="rdh-section">
          <div className="rdh-label">BASELINE</div>
          <div className="rdh-card rdh-baseline">
            <IconDoc className="ico ico-accent" />
            <div>
              <span className="rdh-field-label">Baseline Name</span>
              <strong>{h.baselineName}</strong>
              <div className="rdh-baseline-split">
                <div>
                  <span>Target Fc</span>
                  <b>{h.targetFc} MPa</b>
                </div>
                <div>
                  <span>Datum Temp.</span>
                  <b>{h.datumTemp} °C</b>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="rdh-section">
          <div className="rdh-label">SENSOR DATA</div>
          <div className="rdh-sensor-strip">
            {h.sensorTemps.map((t, i) => (
              <div key={i} className="rdh-cell">
                <IconThermo className="ico ico-accent" />
                <span>Sensor {i + 1}</span>
                <strong>{t.toFixed(1)} °C</strong>
              </div>
            ))}
            <div className="rdh-cell">
              <IconChart className="ico ico-accent" />
              <span>Average Temperature</span>
              <strong>{h.avgTemp.toFixed(1)} °C</strong>
            </div>
          </div>
        </div>

        <div className="rdh-section">
          <div className="rdh-label">CALCULATION</div>
          <div className="rdh-calc">
            <div className="rdh-cell">
              <IconClock className="ico ico-accent" />
              <span>Elapsed Time</span>
              <strong>{h.elapsed}</strong>
            </div>
            <div className="rdh-cell">
              <IconChart className="ico ico-accent" />
              <span>Maturity Index</span>
              <strong>{h.maturityIndex.toLocaleString()}</strong>
              <em>°C·hours</em>
            </div>
            <div className="rdh-cell rdh-predict">
              <IconChart className="ico ico-accent" />
              <span>Predicted Strength</span>
              <strong>{h.strengthMpa.toFixed(1)} MPa</strong>
            </div>
          </div>
        </div>

        <div className="rdh-status">
          <span className="with-ico">
            <IconCheck className="ico ico-accent" /> Status
          </span>
          <StatusPill>{h.status}</StatusPill>
        </div>

        <div className="rdh-note">
          <IconInfo className="ico ico-muted" />
          <p>
            This is a saved historical result from a previous test. Data is retrieved from the
            history menu.
          </p>
        </div>
      </div>
    </Screen>
  )
}

export function SettingsScreen({ state, setState, go }: Props) {
  const s = state.settings
  const bump = (key: 'hour' | 'minute' | 'second' | 'brightness', delta: number, max: number) =>
    setState((st) => ({
      ...st,
      settings: {
        ...st.settings,
        [key]: Math.max(0, Math.min(max, st.settings[key] + delta)),
      },
    }))

  return (
    <Screen
      title="SETTINGS"
      subtitle="Configure timer and device operation parameters."
      rule="short"
      footer={
        <NavFooter
          onBack={() => go('main')}
          onNext={() => go('main')}
          nextLabel="SAVE"
          nextIcon={<span className="chev-white">›</span>}
        />
      }
    >
      <div className="stack">
        <div className="boxed">
          <div className="boxed-title">
            <IconClock className="ico ico-xl ico-accent" /> TIMER SETTING
          </div>
          <div className="timer-row">
            <Stepper
              label="Hour"
              value={String(s.hour).padStart(2, '0')}
              onUp={() => bump('hour', 1, 23)}
              onDown={() => bump('hour', -1, 23)}
            />
            <Stepper
              label="Minute"
              value={String(s.minute).padStart(2, '0')}
              onUp={() => bump('minute', 1, 59)}
              onDown={() => bump('minute', -1, 59)}
            />
            <Stepper
              label="Second"
              value={String(s.second).padStart(2, '0')}
              onUp={() => bump('second', 1, 59)}
              onDown={() => bump('second', -1, 59)}
            />
          </div>
          <div className="info-bar">
            <IconInfo className="ico ico-sm ico-muted" /> Measurement interval timer for monitoring
            process.
          </div>
        </div>

        <div className="boxed">
          <div className="boxed-title">
            <IconGear className="ico ico-xl ico-accent" /> SYSTEM OPTIONS
          </div>
          <div className="option-row">
            <span className="with-ico">
              <IconSun className="ico ico-xl ico-accent" /> Brightness
            </span>
            <Stepper
              compact
              value={`${s.brightness}%`}
              onUp={() => bump('brightness', 5, 100)}
              onDown={() => bump('brightness', -5, 100)}
            />
          </div>
          <div className="option-row">
            <span className="with-ico">
              <IconSound className="ico ico-xl ico-accent" /> Sound
            </span>
            <Toggle
              on={s.sound}
              onToggle={() =>
                setState((st) => ({
                  ...st,
                  settings: { ...st.settings, sound: !st.settings.sound },
                }))
              }
            />
          </div>
          <div className="option-row">
            <span className="with-ico">
              <IconDoc className="ico ico-xl ico-accent" /> Auto Save
            </span>
            <Toggle
              on={s.autoSave}
              onToggle={() =>
                setState((st) => ({
                  ...st,
                  settings: { ...st.settings, autoSave: !st.settings.autoSave },
                }))
              }
            />
          </div>
        </div>
      </div>
    </Screen>
  )
}

function Stepper({
  label,
  value,
  onUp,
  onDown,
  compact,
}: {
  label?: string
  value: string
  onUp: () => void
  onDown: () => void
  compact?: boolean
}) {
  return (
    <div className={`stepper${compact ? ' compact' : ''}`}>
      {label ? <span>{label}</span> : null}
      <strong>{value}</strong>
      <div className="stepper-arrows">
        <button type="button" aria-label="Increase" onClick={onUp}>
          ▴
        </button>
        <button type="button" aria-label="Decrease" onClick={onDown}>
          ▾
        </button>
      </div>
    </div>
  )
}

function Toggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button type="button" className={`toggle${on ? ' on' : ''}`} onClick={onToggle}>
      {on ? 'ON' : 'OFF'}
    </button>
  )
}

export function DeviceInfoScreen({ go }: Props) {
  return (
    <Screen
      title="DEVICE INFO"
      className="screen-device-info"
      subtitle="System and hardware information."
      rule="short"
      footer={
        <BtnGhost block withChevron onClick={() => go('main')}>
          BACK
        </BtnGhost>
      }
    >
      <div className="stack gap-sm">
        <InfoRow icon={<IconDevice className="ico ico-xl ico-accent" />} label="Device Name" value="ConMT Concrete Maturity System" />
        <InfoRow icon={<IconDoc className="ico ico-xl ico-accent" />} label="Device ID" value="CNMT-HK-001" />
        <InfoRow icon={<IconGear className="ico ico-xl ico-accent" />} label="Firmware Version" value="V1.0.3" />
        <InfoRow icon={<IconChip className="ico ico-xl ico-accent" />} label="Hardware" value="Nexion Touch Display" />
        <InfoRow icon={<IconThermo className="ico ico-xl ico-accent" />} label="Sensor Channels" value="3 Temperature Inputs" />
        <InfoRow icon={<IconDatabase className="ico ico-xl ico-accent" />} label="Communication" value="Serial / Modbus" />
        <div className="info-row info-row-status">
          <IconCheck className="ico ico-xl ico-accent" />
          <span className="info-status-label">Status</span>
          <StatusPill>
            <span className="status-spin" aria-hidden />
            READY
          </StatusPill>
        </div>
        <div className="about-box">
          <IconDoc className="ico ico-xl ico-accent" />
          <div>
            <strong>ABOUT</strong>
            <p>
              Concrete strength prediction based on maturity method. Developed for field monitoring
              and baseline evaluation.
            </p>
          </div>
        </div>
      </div>
    </Screen>
  )
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="info-row">
      {icon}
      <div>
        <span className="mini-label">{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  )
}
