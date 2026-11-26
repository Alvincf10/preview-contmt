import { initialState } from './mockData'
import type { AppState, Baseline, TestRecord } from './types'

const STORAGE_KEY = 'conmt:app-state:v7'
const LEGACY_STORAGE_KEYS = [
  'conmt:app-state:v6',
  'conmt:app-state:v5',
  'conmt:app-state:v4',
  'conmt:app-state:v3',
]

/** Old split Excel demo rows — drop when migrating to unified TEST-EXCEL-01. */
const OBSOLETE_HISTORY_IDS = new Set(['h-excel-d1', 'h-excel-d7', 'h-excel-d28'])
const OBSOLETE_HISTORY_TEST_IDS = new Set(['TEST-EXCEL-D1', 'TEST-EXCEL-D7', 'TEST-EXCEL-D28'])

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

/** Keep user saves, but inject any seed baselines that are still missing (by id/name). */
function mergeSeedBaselines(persisted: unknown): Baseline[] {
  const saved = Array.isArray(persisted) ? (persisted as Baseline[]) : []
  const seedById = new Map(initialState.baselines.map((b) => [b.id, b]))
  const seedByName = new Map(
    initialState.baselines.map((b) => [b.name.toLowerCase(), b]),
  )
  // Refresh coeffs/FKZ on known seed baselines (Excel formula updates).
  const refreshed = saved.map((b) => {
    if (!b || typeof b !== 'object') return b
    const seed = seedById.get(b.id) ?? seedByName.get(b.name.toLowerCase())
    if (!seed) return b
    return {
      ...b,
      coeffA: seed.coeffA,
      coeffB: seed.coeffB,
      r2: seed.r2,
      fkzFactors: seed.fkzFactors,
      rows: seed.rows ?? b.rows,
    }
  })
  const missing = initialState.baselines.filter(
    (seed) =>
      !refreshed.some(
        (b) =>
          b &&
          typeof b === 'object' &&
          (b.id === seed.id || b.name.toLowerCase() === seed.name.toLowerCase()),
      ),
  )
  return missing.length
    ? [...missing, ...refreshed]
    : refreshed.length
      ? refreshed
      : initialState.baselines
}

/** Inject Excel seed history rows that are still missing (by id/testId). */
function mergeSeedHistory(persisted: unknown): TestRecord[] {
  const saved = Array.isArray(persisted)
    ? (persisted as TestRecord[]).filter(
        (h) =>
          h &&
          typeof h === 'object' &&
          !OBSOLETE_HISTORY_IDS.has(h.id) &&
          !OBSOLETE_HISTORY_TEST_IDS.has(h.testId),
      )
    : []
  const missing = initialState.history.filter(
    (seed) =>
      !saved.some(
        (h) =>
          h &&
          typeof h === 'object' &&
          (h.id === seed.id || h.testId === seed.testId),
      ),
  )
  return missing.length ? [...missing, ...saved] : saved.length ? saved : initialState.history
}

function sensorAvg(temps: unknown): number | null {
  if (!Array.isArray(temps) || temps.length === 0) return null
  const nums = temps.map(Number).filter((n) => Number.isFinite(n))
  if (!nums.length) return null
  return nums.reduce((s, n) => s + n, 0) / nums.length
}

/** Merge persisted JSON onto defaults so older saves stay loadable. */
export function loadAppState(referenceResult = false): AppState {
  const baselineDraft = referenceResult ? initialState.baselineDraft : { ...initialState.baselineDraft, rows: [] }
  const defaults = { ...initialState, baselineDraft }
  try {
    const raw =
      localStorage.getItem(STORAGE_KEY) ??
      LEGACY_STORAGE_KEYS.map((k) => localStorage.getItem(k)).find((v) => v != null) ??
      null
    if (!raw) return defaults
    const parsed: unknown = JSON.parse(raw)
    if (!isObject(parsed)) return defaults

    const draft = isObject(parsed.baselineDraft) ? parsed.baselineDraft : {}
    const measurement = isObject(parsed.measurement) ? parsed.measurement : {}
    const settings = isObject(parsed.settings) ? parsed.settings : {}

    const baselineEntry =
      parsed.baselineEntry === 'saved' || parsed.baselineEntry === 'create'
        ? parsed.baselineEntry
        : initialState.baselineEntry

    const baselines = mergeSeedBaselines(parsed.baselines)
    const history = mergeSeedHistory(parsed.history)
    const selectedBaselineId =
      typeof parsed.selectedBaselineId === 'string' &&
      baselines.some((b) => b.id === parsed.selectedBaselineId)
        ? parsed.selectedBaselineId
        : baselines[0]?.id ?? initialState.selectedBaselineId

    // Drop stale ambient (~25°C) sensor mocks / mid-test so Excel day-0 (~36°C) applies.
    const persistedAvg = sensorAvg(measurement.sensorTemps)
    const seedAvg = sensorAvg(initialState.measurement.sensorTemps) ?? 36
    const useSeedMeasurement =
      measurement.pourStartMs == null ||
      persistedAvg == null ||
      Math.abs(persistedAvg - seedAvg) > 5

    const next: AppState = {
      ...initialState,
      ...parsed,
      baselineEntry,
      selectedBaselineId,
      baselineDraft: {
        ...initialState.baselineDraft,
        ...draft,
        pourDate:
          typeof draft.pourDate === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(draft.pourDate.trim())
            ? draft.pourDate.trim()
            : initialState.baselineDraft.pourDate,
        pourClock:
          typeof draft.pourClock === 'string' && draft.pourClock.trim()
            ? draft.pourClock
            : initialState.baselineDraft.pourClock,
        rows: Array.isArray(draft.rows) ? draft.rows : baselineDraft.rows,
      },
      baselines,
      history,
      selectedHistoryId:
        typeof parsed.selectedHistoryId === 'string' &&
        history.some((h) => h.id === parsed.selectedHistoryId)
          ? parsed.selectedHistoryId
          : history[0]?.id ?? null,
      measurement: useSeedMeasurement
        ? { ...initialState.measurement }
        : {
            ...initialState.measurement,
            ...measurement,
            sensorTemps: Array.isArray(measurement.sensorTemps)
              ? (measurement.sensorTemps as AppState['measurement']['sensorTemps'])
              : initialState.measurement.sensorTemps,
            logs: Array.isArray(measurement.logs)
              ? (measurement.logs as AppState['measurement']['logs'])
              : initialState.measurement.logs,
          },
      settings: {
        ...initialState.settings,
        ...settings,
      },
    } as AppState

    // Persist migrated state under current key so Excel seeds stick after refresh.
    persistAppState(next)
    for (const k of LEGACY_STORAGE_KEYS) localStorage.removeItem(k)

    return next
  } catch {
    return defaults
  }
}

export function persistAppState(state: AppState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Quota / private mode — keep running in memory only.
  }
}
