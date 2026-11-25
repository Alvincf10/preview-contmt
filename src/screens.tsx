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
  IconTrash,
  IconUser,
  IconBaselineNew,
  IconBaselineSaved,
  UiIcon,
} from './icons'
import { DATUM_TEMPS } from './mockData'
import {
  accumulateNurseSaulM,
  computeFkzFactors,
  fitLogMaturity,
  formatCoeff,
  formatFcEquation,
  lookupFkz,
  nurseSaulIntervalDm,
  nurseSaulMaturityLocked,
  predictFcWithFkz,
} from './maturityFit'
import type { AppState, ScreenId } from './types'

type Props = {
  state: AppState
  setState: (updater: (s: AppState) => AppState) => void
  go: (id: ScreenId) => void
}

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

function fmtDate(iso: string) {
  const [y, m, d] = iso.split('-')
  if (!d) return iso
  return `${d}-${m}-${y}`
}

function todayIso(date = new Date()): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

/** Prefer app date field when it is ISO; otherwise device today. */
function resolvePourDate(appDate: string): string {
  return /^\d{4}-\d{2}-\d{2}$/.test(appDate.trim()) ? appDate.trim() : todayIso()
}

/** DD-MM-YYYY (createdAt) → YYYY-MM-DD */
function createdAtToIso(createdAt: string): string | null {
  const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(createdAt.trim())
  if (!m) return null
  return `${m[3]}-${m[2]}-${m[1]}`
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
          <span>CONCRETE MATURITY TEST</span>
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
      className="screen-user-info"
      footer={
        <BtnPrimary block iconLeft={<IconSave className="ico ico-xl ico-white" />} onClick={() => go('main')}>
          SAVE
        </BtnPrimary>
      }
    >
      <div className="stack user-info-stack">
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
            <IconCalendar className="ico ico-white trailing" />
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
              baselineEntry: 'create',
              baselineDraft: {
                ...s.baselineDraft,
                pourDate: resolvePourDate(s.date),
                pourClock: nowPourClock(),
              },
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

/**
 * Wall clock HH:MM → elapsed age hours for a given lab day.
 * Offset within the day is measured from pour start; wraps past midnight.
 */
function clockToTimeH(pourClock: string, clockRaw: string, day: number): number | null {
  const p = parseHHMM(normalizePourClock(pourClock))
  const c = parseHHMM(clockRaw)
  if (!p || !c || !Number.isFinite(day) || day < 0) return null
  let deltaMin = c.h * 60 + c.m - (p.h * 60 + p.m)
  if (deltaMin < 0) deltaMin += 24 * 60
  return Number((day * 24 + deltaMin / 60).toFixed(4))
}

function parseIsoDate(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim())
  if (!m) return null
  const dt = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return Number.isNaN(dt.getTime()) ? null : dt
}

function pourStartMs(pourDate: string, pourClock: string): number | null {
  const d = parseIsoDate(pourDate)
  const p = parseHHMM(normalizePourClock(pourClock))
  if (!d || !p) return null
  d.setHours(p.h, p.m, 0, 0)
  return d.getTime()
}

const WEEKDAYS_ID = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'] as const

function weekdayId(date: Date): string {
  return WEEKDAYS_ID[date.getDay()] ?? '—'
}

/** Absolute calendar date + clock for a maturity row from locked pour start. */
function rowSchedule(
  pourDate: string,
  pourClock: string,
  timeH: number,
): { weekday: string; date: string; time: string } {
  const start = pourStartMs(pourDate, pourClock)
  if (start == null) {
    const d = parseIsoDate(pourDate)
    return {
      weekday: d ? weekdayId(d) : '—',
      date: fmtDate(pourDate),
      time: elapsedToClock(pourClock, timeH),
    }
  }
  const at = new Date(start + Math.round(timeH * 3600 * 1000))
  return {
    weekday: weekdayId(at),
    date: `${pad2(at.getDate())}-${pad2(at.getMonth() + 1)}-${at.getFullYear()}`,
    time: formatHHMM(at.getHours() * 60 + at.getMinutes()),
  }
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
  const pourDate =
    state.baselineDraft.pourDate && /^\d{4}-\d{2}-\d{2}$/.test(state.baselineDraft.pourDate)
      ? state.baselineDraft.pourDate
      : resolvePourDate(state.date)
  const pourClock = normalizePourClock(state.baselineDraft.pourClock || nowPourClock())
  const canDelete = rows.length > MIN_MATURITY_ROWS
  const [pendingDelete, setPendingDelete] = useState<number | null>(null)
  const [addSheetOpen, setAddSheetOpen] = useState(false)
  const [scheduleOpen, setScheduleOpen] = useState(false)
  const [focusDayIndex, setFocusDayIndex] = useState<number | null>(null)
  const [dayDraft, setDayDraft] = useState<{ i: number; value: string } | null>(null)
  const [timeDraft, setTimeDraft] = useState<{ i: number; value: string } | null>(null)
  const [clockDraft, setClockDraft] = useState<string | null>(null)
  const [activeRow, setActiveRow] = useState<number | null>(null)
  const [sensorHint, setSensorHint] = useState<string | null>(null)
  const [sensorBusy, setSensorBusy] = useState(false)
  const dayInputRefs = useRef<(HTMLInputElement | null)[]>([])
  const nextLab = nextLabDay(rows)
  const clockLabel = (timeH: number) => elapsedToClock(pourClock, timeH)
  const scheduleRows = sortMaturityRows(rows).map((r) => ({
    day: r.day,
    ...rowSchedule(pourDate, pourClock, r.timeH),
  }))

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

  const commitTime = (i: number, raw: string) => {
    const row = rows[i]
    if (!row) {
      setTimeDraft(null)
      return
    }
    const draftDay =
      dayDraft?.i === i && dayDraft.value.trim() !== '' ? Number(dayDraft.value) : NaN
    const day = Number.isFinite(draftDay) && draftDay >= 0 ? draftDay : row.day
    const timeH = clockToTimeH(pourClock, raw, day)
    if (timeH != null) {
      setRows(
        sortMaturityRows(rows.map((r, idx) => (idx === i ? { ...r, timeH } : r))),
      )
    }
    setTimeDraft(null)
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
      titleAside={
        <button
          type="button"
          className="title-info-btn"
          aria-label="Sample schedule"
          onClick={() => setScheduleOpen(true)}
        >
          <IconInfo className="ico ico-xl" />
        </button>
      }
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
        ) : scheduleOpen ? (
          <div
            className="confirm-overlay"
            role="presentation"
            onClick={() => setScheduleOpen(false)}
          >
            <div
              className="confirm-dialog schedule-sheet"
              role="dialog"
              aria-modal="true"
              aria-labelledby="schedule-sheet-title"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 id="schedule-sheet-title" className="confirm-title">
                Sample schedule
              </h2>
              <p className="add-sheet-hint">
                Locked from start {fmtDate(pourDate)} {pourClock}
              </p>
              <div className="schedule-list" role="list">
                <div className="schedule-row schedule-row-head" role="presentation">
                  <span>Day</span>
                  <span>Hari</span>
                  <span>Date</span>
                  <span>Time</span>
                </div>
                {scheduleRows.map((r, i) => (
                  <div
                    key={`${r.day}-${r.date}-${r.time}-${i}`}
                    className="schedule-row"
                    role="listitem"
                  >
                    <span>{r.day}</span>
                    <span>{r.weekday}</span>
                    <span>{r.date}</span>
                    <span>{r.time}</span>
                  </div>
                ))}
              </div>
              <div className="confirm-actions confirm-actions-single">
                <BtnGhost onClick={() => setScheduleOpen(false)}>CLOSE</BtnGhost>
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
                    <input
                      className="time-select"
                      inputMode="numeric"
                      placeholder="HH:MM"
                      aria-label={`Clock time day ${r.day}`}
                      value={
                        timeDraft?.i === i
                          ? timeDraft.value
                          : dayDraft?.i === i &&
                              dayDraft.value.trim() !== '' &&
                              Number.isFinite(Number(dayDraft.value)) &&
                              Number(dayDraft.value) >= 0
                            ? clockLabel(timeFromDay(Number(dayDraft.value)))
                            : clockLabel(r.timeH)
                      }
                      onClick={(e) => e.stopPropagation()}
                      onFocus={() => {
                        setActiveRow(i)
                        setTimeDraft({ i, value: clockLabel(r.timeH) })
                      }}
                      onChange={(e) => setTimeDraft({ i, value: e.target.value })}
                      onBlur={() =>
                        commitTime(
                          i,
                          timeDraft?.i === i ? timeDraft.value : clockLabel(r.timeH),
                        )
                      }
                    />
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
          <div className="info-box-item">Datum Temperature: {state.baselineDraft.datumTemp} °C</div>
          <div className="info-box-item">Formula: M = Σ(T − T₀)Δt</div>
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
      const day = Number(r.day)
      if (!Number.isFinite(timeH) || !Number.isFinite(temp)) return null
      return {
        day: Number.isFinite(day) ? day : 0,
        timeH,
        temp,
        fc: Number.isFinite(fc) ? fc : 0,
      }
    })
    .filter(
      (s): s is { day: number; timeH: number; temp: number; fc: number } => s != null,
    )
  const withM = accumulateNurseSaulM(samples, t0)
  const points = withM
    .filter((s) => Number.isFinite(s.fc) && s.fc > 0 && s.m > 0)
    .map((s) => ({ x: s.m, y: s.fc }))
    .sort((a, b) => a.x - b.x)

  const fit = fitLogMaturity(points)
  const fkzFactors =
    fit && Number.isFinite(fit.a) && Number.isFinite(fit.b)
      ? computeFkzFactors(samples, t0, fit.a, fit.b)
      : []

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
            pourDate:
              d.pourDate && /^\d{4}-\d{2}-\d{2}$/.test(d.pourDate)
                ? d.pourDate
                : resolvePourDate(s.date),
            pourClock: normalizePourClock(d.pourClock || nowPourClock()),
            rows: d.rows.map((r) => ({ ...r })),
            coeffA: fit?.a,
            coeffB: fit?.b,
            r2: fit?.r2,
            fkzFactors,
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
              <div className="br-equation br-equation-fkz">fc_FKZ = fc · FKZ</div>
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
              <div className="br-kv">
                <span>FKZ ages</span>
                <span className="br-colon">:</span>
                <strong>{fkzFactors.length > 0 ? fkzFactors.length : '—'}</strong>
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
            setState((s) => {
              const b = s.baselines.find((x) => x.id === s.selectedBaselineId)
              if (!b) return { ...s, baselineEntry: 'saved' }
              const pourDate =
                (b.pourDate && /^\d{4}-\d{2}-\d{2}$/.test(b.pourDate) && b.pourDate) ||
                createdAtToIso(b.createdAt) ||
                s.baselineDraft.pourDate ||
                resolvePourDate(s.date)
              return {
                ...s,
                baselineEntry: 'saved',
                baselineDraft: {
                  ...s.baselineDraft,
                  name: b.name,
                  targetFc: String(b.targetFc),
                  datumTemp: String(b.datumTemp),
                  pourDate,
                  pourClock: b.pourClock
                    ? normalizePourClock(b.pourClock)
                    : s.baselineDraft.pourClock || nowPourClock(),
                  cement: String(b.cement),
                  water: String(b.water),
                  coarseAgg: String(b.coarseAgg),
                  fineAgg: String(b.fineAgg),
                  retarderPct: String(b.retarder.pct),
                  retarderBrand: b.retarder.brand,
                  acceleratorPct: String(b.accelerator.pct),
                  acceleratorBrand: b.accelerator.brand,
                  flyAshPct: String(b.flyAsh.pct),
                  flyAshBrand: b.flyAsh.brand,
                  rows: b.rows?.length ? b.rows.map((r) => ({ ...r })) : s.baselineDraft.rows,
                },
              }
            })
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
      <div className="stack baseline-list">
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
              <div className="baseline-card-body">
                <div className="baseline-card-top">
                  <strong title={b.name}>{b.name}</strong>
                  <button
                    type="button"
                    className="trash-btn"
                    aria-label={`Delete ${b.name}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      setPendingDeleteId(b.id)
                    }}
                  >
                    <IconTrash className="ico" />
                  </button>
                </div>
                <div className="baseline-meta">
                  <div className="baseline-meta-row">
                    <span>
                      <span className="mini-label">Target Fc'</span>
                      <b>{b.targetFc} MPa</b>
                    </span>
                    <span>
                      <span className="mini-label">Datum Temp.</span>
                      <b>{b.datumTemp} °C</b>
                    </span>
                  </div>
                  <div className="baseline-meta-created">Created: {b.createdAt}</div>
                </div>
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
        logs: [{ day: 0, atMs: pourStartMs, temp: initialPourTemp }],
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
      <div className="stack baseline-list">
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
              <div className="baseline-card-body">
                <strong title={b.name}>{b.name}</strong>
                <div className="baseline-meta">
                  <div className="baseline-meta-row">
                    <span>
                      <span className="mini-label">Target Fc'</span>
                      <b>{b.targetFc} MPa</b>
                    </span>
                    <span>
                      <span className="mini-label">Datum Temp.</span>
                      <b>{b.datumTemp} °C</b>
                    </span>
                  </div>
                  <div className="baseline-meta-created">Created: {b.createdAt}</div>
                </div>
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

function formatDayMonthYear(d: Date) {
  return `${pad2(d.getDate())}-${pad2(d.getMonth() + 1)}-${d.getFullYear()}`
}

function formatElapsed(totalSec: number) {
  const sec = Math.max(0, Math.floor(totalSec))
  const hh = String(Math.floor(sec / 3600)).padStart(2, '0')
  const mm = String(Math.floor((sec % 3600) / 60)).padStart(2, '0')
  const ss = String(sec % 60).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

function nextAutoLogDay(logs: { day: number }[]): number {
  if (logs.length === 0) return 0
  return Math.max(...logs.map((l) => l.day)) + 1
}

/** One checkpoint per day from baseline maturity rows (Excel demo fill). */
// function demoLogsFromBaseline(
//   rows: MaturityRow[] | undefined,
//   pourStartMs: number,
// ): { day: number; atMs: number; temp: number }[] {
//   if (!rows?.length) return []
//   const byDay = new Map<number, { timeH: number; temp: number }>()
//   for (const r of rows) {
//     const day = Number(r.day)
//     const timeH = Number(r.timeH)
//     const temp = Number(r.temperature)
//     if (!Number.isFinite(day) || !Number.isFinite(timeH) || !Number.isFinite(temp)) continue
//     const prev = byDay.get(day)
//     if (day === 0) {
//       if (!prev || timeH < prev.timeH) byDay.set(day, { timeH, temp })
//       continue
//     }
//     const target = day * 24
//     if (!prev || Math.abs(timeH - target) < Math.abs(prev.timeH - target)) {
//       byDay.set(day, { timeH, temp })
//     }
//   }
//   return [...byDay.entries()]
//     .sort((a, b) => a[0] - b[0])
//     .map(([day, v]) => ({
//       day,
//       atMs: pourStartMs + Math.round(Math.max(0, v.timeH) * 3_600_000),
//       temp: v.temp,
//     }))
// }

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
  const logs = state.measurement.logs ?? []
  const logRows = useMemo(
    () =>
      enrichHistoryLogs(
        logs,
        datumTemp,
        baseline?.coeffA,
        baseline?.coeffB,
        baseline?.fkzFactors,
      ),
    [logs, datumTemp, baseline?.coeffA, baseline?.coeffB, baseline?.fkzFactors],
  )
  const [now, setNow] = useState(() => new Date())
  const [dayHint, setDayHint] = useState<string | null>(null)
  const [logDraft, setLogDraft] = useState<{
    key: string
    field: 'time' | 'temp'
    value: string
  } | null>(null)
  // Excel Σ: accumulate dM each second with trapezoid ((T_prev+T_now)/2 − T₀)·Δt
  const maturityRef = useRef(0)
  const prevTempRef = useRef(initialPourTemp ?? averageReadableTemps(temps)?.avg ?? 0)
  const caughtUpRef = useRef(false)

  useEffect(() => {
    const startMs = pourStartRef.current.getTime()
    setState((s) => {
      const hasDay0 = (s.measurement.logs ?? []).some((l) => l.day === 0)
      const pourTemp = s.measurement.initialPourTemp ?? 0
      const nextLogs =
        hasDay0 || s.measurement.pourStartMs == null
          ? s.measurement.logs ?? []
          : [{ day: 0, atMs: startMs, temp: pourTemp }, ...(s.measurement.logs ?? [])]
      if (s.measurement.pourStartMs === startMs && hasDay0) return s
      return {
        ...s,
        measurement: {
          ...s.measurement,
          pourStartMs: startMs,
          endMs: null,
          logs: nextLogs.length ? nextLogs : [{ day: 0, atMs: startMs, temp: pourTemp }],
        },
      }
    })
  }, [setState])

  // If realtime resumed mid-session, catch up M for elapsed so far (one Excel interval).
  useEffect(() => {
    if (caughtUpRef.current) return
    caughtUpRef.current = true
    const startMs = pourStartRef.current.getTime()
    const elapsedSec = Math.max(0, Math.floor((Date.now() - startMs) / 1000))
    const tStart = initialPourTemp ?? averageReadableTemps(temps)?.avg ?? 0
    const tNow = averageReadableTemps(temps)?.avg ?? tStart
    if (elapsedSec > 0) {
      maturityRef.current = nurseSaulMaturityLocked(tStart, tNow, datumTemp, elapsedSec)
      prevTempRef.current = tNow
    }
  }, [])

  useEffect(() => {
    if (!dayHint) return
    const t = window.setTimeout(() => setDayHint(null), 2200)
    return () => window.clearTimeout(t)
  }, [dayHint])

  useEffect(() => {
    const t = window.setInterval(() => {
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
  const pourStart = pourStartRef.current
  const pourDateLabel = formatDayMonthYear(pourStart)
  const pourTimeLabel = formatClock(pourStart)
  const currentDateLabel = formatDayMonthYear(now)
  const currentTimeLabel = formatClock(now)
  const nextDay = nextAutoLogDay(logs)

  const logKey = (l: { day: number; atMs: number }) => `${l.day}-${l.atMs}`

  const addDayAuto = () => {
    // Prefer Excel/baseline temp for that day when available (demo-friendly).
    const row = baseline?.rows?.find((r) => Number(r.day) === nextDay)
    const tempFromBaseline = row ? Number(row.temperature) : NaN
    const atMs = Date.now()
    const temp = Number.isFinite(tempFromBaseline) ? tempFromBaseline : avg
    const startMs = pourStartRef.current.getTime()
    const scheduledMs =
      nextDay > 0 ? startMs + nextDay * 24 * 3_600_000 : atMs
    setState((s) => {
      const prev = s.measurement.logs ?? []
      const without = prev.filter((l) => l.day !== nextDay)
      const next = [...without, { day: nextDay, atMs: scheduledMs, temp }].sort(
        (a, b) => a.day - b.day || a.atMs - b.atMs,
      )
      return {
        ...s,
        measurement: { ...s.measurement, logs: next, sensorTemps: temps },
      }
    })
    setDayHint(`Day ${nextDay} logged · ${temp.toFixed(1)} °C`)
  }

  // Demo fill kept for later (button currently commented out)
  // const fillDemoDays = () => {
  //   const startMs = pourStartRef.current.getTime()
  //   const demo = demoLogsFromBaseline(baseline?.rows, startMs)
  //   if (demo.length < 2) {
  //     setDayHint('Baseline has no demo temperature rows.')
  //     return
  //   }
  //   setState((s) => ({
  //     ...s,
  //     measurement: {
  //       ...s.measurement,
  //       pourStartMs: startMs,
  //       endMs: null,
  //       logs: demo,
  //       sensorTemps: temps,
  //       initialPourTemp: demo[0]?.temp ?? s.measurement.initialPourTemp,
  //     },
  //   }))
  //   setDayHint(`Loaded ${demo.length} demo days from baseline / Excel`)
  // }

  const commitLogTemp = (day: number, atMs: number, raw: string) => {
    const temp = Number(raw)
    if (!Number.isFinite(temp)) {
      setLogDraft(null)
      return
    }
    setState((s) => ({
      ...s,
      measurement: {
        ...s.measurement,
        logs: (s.measurement.logs ?? []).map((l) =>
          l.day === day && l.atMs === atMs ? { ...l, temp } : l,
        ),
        initialPourTemp: day === 0 ? temp : s.measurement.initialPourTemp,
      },
    }))
    setLogDraft(null)
  }

  const commitLogTime = (day: number, atMs: number, raw: string) => {
    const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(String(raw).trim())
    if (!m) {
      setLogDraft(null)
      return
    }
    const hh = Number(m[1])
    const mm = Number(m[2])
    const ss = m[3] != null ? Number(m[3]) : 0
    if (hh > 23 || mm > 59 || ss > 59) {
      setLogDraft(null)
      return
    }
    const next = new Date(atMs)
    next.setHours(hh, mm, ss, 0)
    const nextMs = next.getTime()
    if (day === 0) pourStartRef.current = new Date(nextMs)
    setState((s) => ({
      ...s,
      measurement: {
        ...s.measurement,
        pourStartMs: day === 0 ? nextMs : s.measurement.pourStartMs,
        logs: (s.measurement.logs ?? []).map((l) =>
          l.day === day && l.atMs === atMs ? { ...l, atMs: nextMs } : l,
        ),
      },
    }))
    setLogDraft(null)
  }

  const maturityFromLogs = (endMs: number, liveTemp: number) => {
    const startMs = pourStartRef.current.getTime()
    const pourAvg = initialPourTemp ?? liveTemp
    const points = [...logs]
      .map((l) => ({
        timeH: Math.max(0, (l.atMs - startMs) / 3_600_000),
        temp: l.temp,
      }))
      .sort((a, b) => a.timeH - b.timeH)
    const liveTimeH = Math.max(0, (endMs - startMs) / 3_600_000)
    const last = points[points.length - 1]
    if (!last || liveTimeH > last.timeH + 1 / 3600) {
      points.push({ timeH: liveTimeH, temp: liveTemp })
    }
    if (points.length < 2) {
      return nurseSaulMaturityLocked(pourAvg, liveTemp, datumTemp, (endMs - startMs) / 1000)
    }
    const withM = accumulateNurseSaulM(points, datumTemp)
    return withM[withM.length - 1]?.m ?? 0
  }

  const goToResult = () => {
    const startMs = pourStartRef.current.getTime()
    // Elapsed / result lock to last logged checkpoint (not NEXT click time).
    const lastLogMs =
      logs.length > 0 ? Math.max(...logs.map((l) => l.atMs)) : Date.now()
    const endMs = Math.max(startMs, lastLogMs)
    const lastTemp =
      logs.length > 0
        ? [...logs].sort((a, b) => b.atMs - a.atMs)[0]?.temp ?? avg
        : avg
    const pourAvg = initialPourTemp ?? avg
    let m = maturityFromLogs(endMs, lastTemp)
    if (m < 1e-9) m = maturityRef.current
    const maturityIndex = Math.round(m)
    setState((s) => ({
      ...s,
      measurement: {
        ...s.measurement,
        pourStartMs: startMs,
        endMs,
        avgTemp: pourAvg,
        maturityIndex,
        sensorTemps: temps,
      },
    }))
    go('strengthResult')
  }

  const lastLog = logRows.length > 0 ? logRows[logRows.length - 1] : null
  const liveM = lastLog?.maturity ?? Math.round(maturityRef.current)
  const liveFc = lastLog?.predictedFc ?? null
  const targetFc = baseline?.targetFc ?? 0
  const livePct =
    liveFc != null && targetFc > 0 ? Math.max(0, (liveFc / targetFc) * 100) : null
  // const canFillDemo = (baseline?.rows?.length ?? 0) > 1

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

        <div className="rt-live-strip" aria-label="Live prediction">
          <div className="rt-live-cell">
            <span>Maturity M</span>
            <strong>
              {liveM.toLocaleString()}
              <small> °C·h</small>
            </strong>
          </div>
          <div className="rt-live-cell rt-live-fc">
            <span>Predicted Fc'</span>
            <strong>
              {liveFc != null ? `${liveFc.toFixed(1)} MPa` : '—'}
              {livePct != null ? (
                <span className="rt-live-pct"> ({livePct.toFixed(0)}%)</span>
              ) : null}
            </strong>
          </div>
        </div>

        <div className="sensor-row">
          {temps.map((t, i) => (
            <div key={i} className="sensor-box">
              <IconThermo className="ico ico-accent" />
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
          <div className="rt-monitor-grid rt-monitor-grid-3" role="group" aria-label="Pour monitoring">
            <div className="rt-cell">
              <span className="rt-cell-label">Initial Pour Date</span>
              <strong className="rt-cell-value">{pourDateLabel}</strong>
            </div>
            <div className="rt-cell rt-cell-end">
              <span className="rt-cell-label">Current Date</span>
              <strong className="rt-cell-value">{currentDateLabel}</strong>
            </div>
            <div className="rt-cell">
              <span className="rt-cell-label">Initial Pour Time</span>
              <strong className="rt-cell-value">{pourTimeLabel}</strong>
            </div>
            <div className="rt-cell rt-cell-end">
              <span className="rt-cell-label">Current Time</span>
              <strong className="rt-cell-value rt-clock">{currentTimeLabel}</strong>
            </div>
            <div className="rt-cell">
              <span className="rt-cell-label">Initial Temp.</span>
              <strong className="rt-cell-value rt-pour-temp">
                {initialPourTemp != null ? `${initialPourTemp.toFixed(1)} °C` : '—'}
              </strong>
            </div>
            <div className="rt-cell rt-cell-end">
              <span className="rt-cell-label">Current Temp.</span>
              <strong className="rt-cell-value">{avg.toFixed(1)} °C</strong>
            </div>
          </div>
        </div>

        <div className="rt-day-actions">
          <button type="button" className="rt-day-btn" onClick={addDayAuto}>
            + ADD DAY {nextDay > 0 ? `(Day ${nextDay})` : ''}
          </button>
          {/* {canFillDemo ? (
            <button type="button" className="rt-day-btn rt-day-btn-ghost" onClick={fillDemoDays}>
              LOAD EXCEL DEMO DAYS
            </button>
          ) : null} */}
        </div>

        <div className="rt-log-card" aria-label="Logged days">
          <div className="rt-log-head">
            <IconCalendar className="ico ico-accent ico-sm" />
            <span>LOGGED DAYS</span>
            <span className="rt-log-count">{logRows.length}</span>
          </div>
          {logRows.length === 1 && logRows[0]?.day === 0 ? (
            <p className="rt-log-hint">
              Day 0 = saat tuang (M = 0). Tekan ADD DAY atau LOAD EXCEL DEMO DAYS untuk isi hari
              berikutnya.
            </p>
          ) : null}
          {logRows.length > 0 ? (
            <div className="rt-log-list" role="list">
              {logRows.map((l) => {
                const at = new Date(l.atMs)
                const key = logKey(l)
                const timeValue =
                  logDraft?.key === key && logDraft.field === 'time'
                    ? logDraft.value
                    : formatClock(at)
                const tempValue =
                  logDraft?.key === key && logDraft.field === 'temp'
                    ? logDraft.value
                    : l.temp.toFixed(1)
                const pct =
                  l.predictedFc != null && targetFc > 0
                    ? Math.max(0, (l.predictedFc / targetFc) * 100)
                    : null
                return (
                  <div key={key} className="rt-log-item" role="listitem">
                    <div className="rt-log-item-top">
                      <strong className="rt-log-day">Day {l.day}</strong>
                      <span className="rt-log-when">{formatDayMonthYear(at)}</span>
                    </div>
                    <div className="rt-log-item-edit">
                      <label>
                        <span>Time</span>
                        <input
                          className="rt-log-input"
                          inputMode="numeric"
                          aria-label={`Day ${l.day} time`}
                          value={timeValue}
                          onFocus={() =>
                            setLogDraft({ key, field: 'time', value: formatClock(at) })
                          }
                          onChange={(e) =>
                            setLogDraft({ key, field: 'time', value: e.target.value })
                          }
                          onBlur={() =>
                            commitLogTime(
                              l.day,
                              l.atMs,
                              logDraft?.key === key && logDraft.field === 'time'
                                ? logDraft.value
                                : formatClock(at),
                            )
                          }
                        />
                      </label>
                      <label>
                        <span>Temp °C</span>
                        <input
                          className="rt-log-input"
                          inputMode="decimal"
                          aria-label={`Day ${l.day} temperature`}
                          value={tempValue}
                          onFocus={() =>
                            setLogDraft({ key, field: 'temp', value: l.temp.toFixed(1) })
                          }
                          onChange={(e) =>
                            setLogDraft({ key, field: 'temp', value: e.target.value })
                          }
                          onBlur={() =>
                            commitLogTemp(
                              l.day,
                              l.atMs,
                              logDraft?.key === key && logDraft.field === 'temp'
                                ? logDraft.value
                                : String(l.temp),
                            )
                          }
                        />
                      </label>
                    </div>
                    <div className="rt-log-item-metrics">
                      <span>
                        M <b>{l.maturity.toLocaleString()}</b>
                      </span>
                      <span className="rt-log-fc">
                        Fc'{' '}
                        <b>
                          {l.predictedFc != null ? l.predictedFc.toFixed(1) : '—'}
                          {pct != null ? ` (${pct.toFixed(0)}%)` : ''}
                        </b>
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="rt-log-empty">No days logged yet. Tap ADD DAY.</p>
          )}
        </div>
        {dayHint ? <p className="rt-day-hint">{dayHint}</p> : null}
      </div>
    </Screen>
  )
}

export function StrengthResultScreen({ state, setState, go }: Props) {
  const baseline = selectedBaseline(state)
  const m = state.measurement
  const pourStartMs = m.pourStartMs ?? Date.now()
  const logs = m.logs ?? []
  const lastLogMs =
    logs.length > 0 ? Math.max(...logs.map((l) => l.atMs)) : (m.endMs ?? Date.now())
  const endMs = Math.max(pourStartMs, lastLogMs)
  // Elapsed = last logged checkpoint − initial pour (not NEXT click).
  const elapsedLabel = formatElapsed((endMs - pourStartMs) / 1000)
  // Suhu awal penuangan (saat START) — sama dengan Initial Temp. di realtime.
  const avgTemp = m.initialPourTemp ?? m.avgTemp
  const maturityIndex = m.maturityIndex
  const lastLogDay =
    logs.length > 0
      ? [...logs].sort((a, b) => b.atMs - a.atMs)[0]?.day ?? 0
      : 0
  const fkz = lookupFkz(baseline?.fkzFactors, lastLogDay)
  const strength =
    baseline?.coeffA != null &&
    baseline?.coeffB != null &&
    Number.isFinite(baseline.coeffA) &&
    Number.isFinite(baseline.coeffB)
      ? predictFcWithFkz(maturityIndex, baseline.coeffA, baseline.coeffB, fkz)
      : 0
  const targetFc = baseline?.targetFc ?? 0
  const strengthPct =
    targetFc > 0 && Number.isFinite(strength)
      ? Math.max(0, (strength / targetFc) * 100)
      : null

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
          logs: (s.measurement.logs ?? []).map((l) => ({ ...l })),
          coeffA: baseline?.coeffA,
          coeffB: baseline?.coeffB,
          fkzFactors: baseline?.fkzFactors?.map((f) => ({ ...f })),
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
            <strong className="sr-baseline-name" title={baseline?.name}>
              {baseline?.name}
            </strong>
            <div className="sr-baseline-split">
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
            <strong className="huge">
              {strength.toFixed(1)} MPa
              {strengthPct != null ? (
                <span className="predict-pct"> ({strengthPct.toFixed(0)}%)</span>
              ) : null}
            </strong>
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
        </div>
      </div>
    </Screen>
  )
}

export function HistoryScreen({ state, setState, go }: Props) {
  const selected = state.selectedHistoryId ?? state.history[0]?.id

  const openDetail = (id: string) => {
    setState((s) => ({ ...s, selectedHistoryId: id }))
    go('historyDetail')
  }

  return (
    <Screen
      title="TEST HISTORY"
      className="screen-history"
      rule="short"
      footer={
        <NavFooter
          onBack={() => go('kuatTekanMenu')}
          onNext={() => {
            if (!selected) return
            openDetail(selected)
          }}
          nextLabel="VIEW LOG"
        />
      }
    >
      <div className="stack history-list">
        {state.history.map((h) => {
          const logCount = h.logs?.length ?? 0
          return (
            <button
              key={h.id}
              type="button"
              className={`history-card${selected === h.id ? ' selected' : ''}`}
              onClick={() => openDetail(h.id)}
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
                  LOG <span aria-hidden>›</span>
                </span>
              </div>
              <div className="history-bottom">
                <div className="history-field">
                  <span className="mini-label">Predicted Strength</span>
                  <strong className="orange-text">
                    {Math.max(0, h.strengthMpa).toFixed(1)}
                    <span> MPa</span>
                  </strong>
                </div>
                <div className="history-field">
                  <span className="mini-label">Date</span>
                  <strong>{h.date}</strong>
                </div>
                <div className="history-field history-logs">
                  <span className="mini-label">Logged Days</span>
                  <strong>
                    {logCount > 0 ? `${logCount} day${logCount > 1 ? 's' : ''}` : '—'}
                  </strong>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </Screen>
  )
}

/** Per-log Nurse–Saul M + Predicted Fc (× FKZ) from checkpoints. */
function enrichHistoryLogs(
  logs: { day: number; atMs: number; temp: number }[],
  datumTemp: number,
  coeffA?: number,
  coeffB?: number,
  fkzFactors?: { day: number; fkz: number }[],
) {
  const sorted = [...logs].sort((a, b) => a.day - b.day || a.atMs - b.atMs)
  if (sorted.length === 0) return []
  const t0 = sorted[0].atMs
  const samples = sorted.map((l) => ({
    ...l,
    timeH: Math.max(0, (l.atMs - t0) / 3_600_000),
  }))
  const withM = accumulateNurseSaulM(samples, datumTemp)
  const canPredict =
    coeffA != null &&
    coeffB != null &&
    Number.isFinite(coeffA) &&
    Number.isFinite(coeffB)
  return withM.map((row) => {
    const maturity = Math.round(row.m)
    const predictedFc = canPredict
      ? predictFcWithFkz(row.m, coeffA, coeffB, lookupFkz(fkzFactors, row.day))
      : null
    return { ...row, maturity, predictedFc }
  })
}

export function HistoryDetailScreen({ state, go }: Props) {
  const h = state.history.find((x) => x.id === state.selectedHistoryId) ?? state.history[0]
  const [openLogKey, setOpenLogKey] = useState<string | null>(null)

  if (!h) {
    return (
      <Screen title="RESULT DETAIL HISTORY" footer={<NavFooter onBack={() => go('history')} />}>
        <p className="panel-sub">No history selected.</p>
      </Screen>
    )
  }

  const baselineMatch = state.baselines.find((b) => b.name === h.baselineName)
  const coeffA = h.coeffA ?? baselineMatch?.coeffA
  const coeffB = h.coeffB ?? baselineMatch?.coeffB
  const fkzFactors = h.fkzFactors ?? baselineMatch?.fkzFactors
  const logRows = enrichHistoryLogs(h.logs ?? [], h.datumTemp, coeffA, coeffB, fkzFactors)

  return (
    <Screen
      title="RESULT DETAIL HISTORY"
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
          <div className="rdh-label">LOGGED DAYS</div>
          <div className="rdh-card rdh-log-card">
            {logRows.length > 0 ? (
              <div className="rdh-log-accordion" role="list">
                {logRows.map((l) => {
                  const key = `${l.day}-${l.atMs}`
                  const open = openLogKey === key
                  const at = new Date(l.atMs)
                  const pct =
                    l.predictedFc != null && h.targetFc > 0
                      ? Math.max(0, (l.predictedFc / h.targetFc) * 100)
                      : null
                  const fcLabel =
                    l.predictedFc != null
                      ? pct != null
                        ? `${l.predictedFc.toFixed(1)} (${pct.toFixed(0)}%)`
                        : l.predictedFc.toFixed(1)
                      : '—'
                  return (
                    <div key={key} className={`rdh-log-item${open ? ' is-open' : ''}`} role="listitem">
                      <button
                        type="button"
                        className="rdh-log-toggle"
                        aria-expanded={open}
                        onClick={() => setOpenLogKey(open ? null : key)}
                      >
                        <span className="rdh-log-day">Day {l.day}</span>
                        <span className="rdh-log-summary">
                          <span>
                            {formatDayMonthYear(at)} · {formatClock(at)} · {l.temp.toFixed(1)}°C
                          </span>
                          <span className="rdh-log-metrics">
                            M {l.maturity.toLocaleString()}
                            {' · '}
                            Fc' {fcLabel}
                          </span>
                        </span>
                        <span className="rdh-log-chevron" aria-hidden>
                          {open ? '▴' : '▾'}
                        </span>
                      </button>
                      {open ? (
                        <div className="rdh-log-panel">
                          <div className="rdh-log-kv">
                            <span>Time</span>
                            <strong>{formatClock(at)}</strong>
                          </div>
                          <div className="rdh-log-kv">
                            <span>Temperature</span>
                            <strong>{l.temp.toFixed(1)} °C</strong>
                          </div>
                          <div className="rdh-log-kv">
                            <span>Maturity Index</span>
                            <strong>
                              {l.maturity.toLocaleString()}
                              <small> °C·h</small>
                            </strong>
                          </div>
                          <div className="rdh-log-kv rdh-log-fc">
                            <span>Predicted Fc'</span>
                            <strong>
                              {l.predictedFc != null
                                ? pct != null
                                  ? `${l.predictedFc.toFixed(1)} MPa (${pct.toFixed(0)}%)`
                                  : `${l.predictedFc.toFixed(1)} MPa`
                                : '—'}
                            </strong>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="rdh-log-empty">No day logs saved for this test.</p>
            )}
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
          <div className="rdh-calc rdh-calc-2">
            <div className="rdh-cell">
              <IconChart className="ico ico-accent" />
              <span>Maturity Index</span>
              <strong>{h.maturityIndex.toLocaleString()}</strong>
              <em>°C·hours</em>
            </div>
            <div className="rdh-cell rdh-predict">
              <IconChart className="ico ico-accent" />
              <span>Predicted Strength</span>
              <strong>
                {Math.max(0, h.strengthMpa).toFixed(1)} MPa
                {h.targetFc > 0
                  ? ` (${Math.max(0, (h.strengthMpa / h.targetFc) * 100).toFixed(0)}%)`
                  : ''}
              </strong>
            </div>
          </div>
        </div>

        <div className="rdh-note">
          <IconInfo className="ico ico-muted" />
          <p>
            Day logs are the checkpoints saved during realtime measurement (ADD DAY / MANUAL).
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
      {label ? <span className="stepper-label">{label}</span> : null}
      <button type="button" className="stepper-btn" aria-label="Increase" onClick={onUp}>
        +
      </button>
      <strong className="stepper-value">{value}</strong>
      <button type="button" className="stepper-btn" aria-label="Decrease" onClick={onDown}>
        −
      </button>
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
      <div className="stack device-info-stack">
        <InfoRow
          icon={<IconDevice className="ico ico-xl ico-accent" />}
          label="Device Name"
          value="Concrete Maturity Test"
        />
        <InfoRow icon={<IconDoc className="ico ico-xl ico-accent" />} label="Device ID" value="HK ConMT" />

        <div className="device-info-tiles">
          <InfoRow icon={<IconGear className="ico ico-xl ico-accent" />} label="Firmware" value="V1.0.1" />
          <InfoRow
            icon={<IconChip className="ico ico-xl ico-accent" />}
            label="Hardware"
            value="Nextion Touch Display"
          />
          <InfoRow icon={<IconThermo className="ico ico-xl ico-accent" />} label="Sensors" value="3 Temp Inputs" />
          <InfoRow
            icon={<IconDatabase className="ico ico-xl ico-accent" />}
            label="Comm"
            value="Serial / Modbus"
          />
        </div>

        <div className="info-row info-row-status">
          <IconCheck className="ico ico-xl ico-accent" />
          <div className="info-row-text">
            <span className="mini-label">Status</span>
            <strong>Device ready</strong>
          </div>
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
      <div className="info-row-text">
        <span className="mini-label">{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  )
}
