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
}

export type MaturityRow = {
  day: number
  timeH: number
  fcLab: string
  temperature: string
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
}

export type AppState = {
  operatorId: string
  projectName: string
  date: string
  baselineDraft: {
    name: string
    targetFc: string
    datumTemp: string
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
