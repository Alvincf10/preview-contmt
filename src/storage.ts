import { initialState } from './mockData'
import type { AppState } from './types'

const STORAGE_KEY = 'conmt:app-state:v3'

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

/** Merge persisted JSON onto defaults so older saves stay loadable. */
export function loadAppState(): AppState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return initialState
    const parsed: unknown = JSON.parse(raw)
    if (!isObject(parsed)) return initialState

    const draft = isObject(parsed.baselineDraft) ? parsed.baselineDraft : {}
    const measurement = isObject(parsed.measurement) ? parsed.measurement : {}
    const settings = isObject(parsed.settings) ? parsed.settings : {}

    const baselineEntry =
      parsed.baselineEntry === 'saved' || parsed.baselineEntry === 'create'
        ? parsed.baselineEntry
        : initialState.baselineEntry

    return {
      ...initialState,
      ...parsed,
      baselineEntry,
      baselineDraft: {
        ...initialState.baselineDraft,
        ...draft,
        pourClock:
          typeof draft.pourClock === 'string' && draft.pourClock.trim()
            ? draft.pourClock
            : initialState.baselineDraft.pourClock,
        rows: Array.isArray(draft.rows) ? draft.rows : initialState.baselineDraft.rows,
      },
      baselines: Array.isArray(parsed.baselines) ? parsed.baselines : initialState.baselines,
      history: Array.isArray(parsed.history) ? parsed.history : initialState.history,
      measurement: {
        ...initialState.measurement,
        ...measurement,
        sensorTemps: Array.isArray(measurement.sensorTemps)
          ? (measurement.sensorTemps as AppState['measurement']['sensorTemps'])
          : initialState.measurement.sensorTemps,
      },
      settings: {
        ...initialState.settings,
        ...settings,
      },
    } as AppState
  } catch {
    return initialState
  }
}

export function persistAppState(state: AppState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Quota / private mode — keep running in memory only.
  }
}
