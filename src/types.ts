export type ScreenId =
  | 'splash'
  | 'userInfo'
  | 'main'
  | 'baselineMenu'
  | 'newBaseline'
  | 'materialData'
  | 'maturityData'
  | 'baselineResult'
  | 'savedBaseline'
  | 'kuatTekanMenu'
  | 'selectBaseline'
  | 'realtime'
  | 'strengthResult'
  | 'history'
  | 'historyDetail'
  | 'settings'
  | 'deviceInfo'

export type Baseline = {
  id: string
  name: string
  targetFc: number
  datumTemp: number
  createdAt: string
  cement: number
  water: number
  coarseAgg: number
  fineAgg: number
  retarder: { pct: number; brand: string }
  accelerator: { pct: number; brand: string }
  flyAsh: { pct: number; brand: string }
  /** Maturity lab table captured at save time (optional on older saves). */
  rows?: MaturityRow[]
  /** Pour / casting calendar date YYYY-MM-DD — locked at create/save. */
  pourDate?: string
  /** Pour start clock HH:MM — locked with pourDate for schedule lookup. */
  pourClock?: string
  /** Log fit fc = a + b·ln(M) from lab points (optional on older saves). */
  coeffA?: number
  coeffB?: number
  r2?: number
  /** Excel FKZ factors by lab day: fc_FKZ = fc_NS · FKZ. */
  fkzFactors?: { day: number; fkz: number }[]
}

export type MaturityRow = {
  day: number
  timeH: number
  fcLab: string
  temperature: string
  requiresFc?: boolean
}

/** Logged sample for multi-day realtime maturity (Nurse–Saul checkpoints). */
export type MeasurementLogPoint = {
  day: number
  atMs: number
  temp: number
}

export type TestRecord = {
  id: string
  testId: string
  baselineName: string
  date: string
  time: string
  strengthMpa: number
  avgTemp: number
  maturityIndex: number
  elapsed: string
  sensorTemps: [number, number, number]
  operatorId: string
  project: string
  targetFc: number
  datumTemp: number
  status: 'COMPLETED' | 'RUNNING'
  /** Day checkpoints captured during realtime (optional on older history). */
  logs?: MeasurementLogPoint[]
  /** Baseline log-fit coeffs at save time — for per-log Predicted Fc. */
  coeffA?: number
  coeffB?: number
  /** Excel FKZ factors copied from baseline at save time. */
  fkzFactors?: { day: number; fkz: number }[]
}

export type MeasurementSession = {
  pourStartMs: number | null
  endMs: number | null
  /** Rata-rata suhu saat tombol START ditekan (suhu awal penuangan). */
  initialPourTemp: number | null
  avgTemp: number
  maturityIndex: number
  sensorTemps: [number, number, number]
  /** Day checkpoints: Day 0 at pour, then ADD DAY auto/manual. */
  logs: MeasurementLogPoint[]
}

/** How the user entered the maturity / generate-baseline wizard. */
export type BaselineEntry = 'create' | 'saved'

export type AppState = {
  operatorId: string
  projectName: string
  date: string
  /** 'create' = New Baseline wizard; 'saved' = opened from SAVED BASELINE. */
  baselineEntry: BaselineEntry
  baselineDraft: {
    name: string
    targetFc: string
    datumTemp: string
    /** Pour / casting calendar date YYYY-MM-DD — locked; Day 0 date does not drift. */
    pourDate: string
    /** Pour start clock HH:MM — UI shows actual time; timeH = elapsed from this. */
    pourClock: string
    cement: string
    water: string
    coarseAgg: string
    fineAgg: string
    retarderPct: string
    retarderBrand: string
    acceleratorPct: string
    acceleratorBrand: string
    flyAshPct: string
    flyAshBrand: string
    rows: MaturityRow[]
  }
  baselines: Baseline[]
  selectedBaselineId: string | null
  measurement: MeasurementSession
  history: TestRecord[]
  selectedHistoryId: string | null
  settings: {
    hour: number
    minute: number
    second: number
    brightness: number
    sound: boolean
    autoSave: boolean
  }
}
