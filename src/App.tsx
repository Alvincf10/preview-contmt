import { useCallback, useEffect, useMemo, useState } from 'react'
import { PhoneShell } from './components'
import {
  BaselineMenuScreen,
  BaselineResultScreen,
  DeviceInfoScreen,
  HistoryDetailScreen,
  HistoryScreen,
  KuatTekanMenuScreen,
  MainMenuScreen,
  MaterialDataScreen,
  MaturityDataScreen,
  NewBaselineScreen,
  RealtimeScreen,
  SavedBaselineScreen,
  SelectBaselineScreen,
  SettingsScreen,
  SplashScreen,
  StrengthResultScreen,
  UserInfoScreen,
} from './screens'
import { loadAppState, persistAppState } from './storage'
import type { AppState, ScreenId } from './types'
import './App.css'

const screens = {
  splash: SplashScreen,
  userInfo: UserInfoScreen,
  main: MainMenuScreen,
  baselineMenu: BaselineMenuScreen,
  newBaseline: NewBaselineScreen,
  materialData: MaterialDataScreen,
  maturityData: MaturityDataScreen,
  baselineResult: BaselineResultScreen,
  savedBaseline: SavedBaselineScreen,
  kuatTekanMenu: KuatTekanMenuScreen,
  selectBaseline: SelectBaselineScreen,
  realtime: RealtimeScreen,
  strengthResult: StrengthResultScreen,
  history: HistoryScreen,
  historyDetail: HistoryDetailScreen,
  settings: SettingsScreen,
  deviceInfo: DeviceInfoScreen,
} as const

const designOverlay: Partial<Record<ScreenId, string>> = {
  splash: '/design/initialization.png',
  userInfo: '/design/user-info.png',
  main: '/design/main-menu.png',
  baselineMenu: '/design/baseline.png',
  newBaseline: '/design/new-baseline.png',
  materialData: '/design/material-data.png',
  maturityData: '/design/maturity-data.png',
  baselineResult: '/design/baseline-result.png',
  savedBaseline: '/design/saved-baseline.png',
  kuatTekanMenu: '/design/kuat-tekan.png',
  selectBaseline: '/design/select-baseline.png',
  realtime: '/design/realtime.png',
  strengthResult: '/design/strength-result.png',
  history: '/design/test-history.png',
  historyDetail: '/design/result-detail.png',
  settings: '/design/settings.png',
  deviceInfo: '/design/device-info.png',
}

function readScreenParam(): ScreenId {
  const q = new URLSearchParams(window.location.search)
  const s = q.get('screen') as ScreenId | null
  return s && s in screens ? s : 'splash'
}

export default function App() {
  const [screen, setScreen] = useState<ScreenId>(() => readScreenParam())
  const [state, setStateRaw] = useState<AppState>(() => loadAppState())
  const [compare, setCompare] = useState(() =>
    new URLSearchParams(window.location.search).get('compare') === '1',
  )

  const setState = useCallback((updater: (s: AppState) => AppState) => {
    setStateRaw((prev) => {
      const next = updater(prev)
      persistAppState(next)
      return next
    })
  }, [])

  const go = useCallback((id: ScreenId) => {
    setScreen(id)
    const url = new URL(window.location.href)
    url.searchParams.set('screen', id)
    window.history.replaceState({}, '', url)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'c' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
        e.preventDefault()
        setCompare((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const Active = screens[screen]
  const overlaySrc = useMemo(() => designOverlay[screen], [screen])

  return (
    <PhoneShell>
      <Active state={state} setState={setState} go={go} />
      {compare && overlaySrc ? (
        <img className="design-overlay" src={overlaySrc} alt="" draggable={false} />
      ) : null}
      <div className="size-badge" aria-hidden>
        480×800{compare ? ' · compare' : ''}
      </div>
    </PhoneShell>
  )
}
