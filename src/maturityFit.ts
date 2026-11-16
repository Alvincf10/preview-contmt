/** Log maturity–strength fit: fc = a + b·ln(M) (same as Excel trendline). */

export type MaturityFit = {
  a: number
  b: number
  r2: number
  n: number
}

/**
 * Excel Nurse–Saul one interval (Buat Rumus Maturitas):
 * dM = ((T_i + T_{i-1}) / 2 − T₀) · Δt
 */
export function nurseSaulIntervalDm(
  tPrev: number,
  tNow: number,
  t0: number,
  dtHours: number,
): number {
  if (!(dtHours > 0) || !Number.isFinite(tPrev) || !Number.isFinite(tNow)) return 0
  return ((tPrev + tNow) / 2 - t0) * dtHours
}

/**
 * Accumulate M = Σ(T − T₀)·Δt over time samples (trapezoid T, like Excel col H→I).
 * First sample at earliest time gets M = 0.
 */
export function accumulateNurseSaulM<T extends { timeH: number; temp: number }>(
  samples: T[],
  t0: number,
): (T & { m: number })[] {
  const sorted = [...samples]
    .filter((s) => Number.isFinite(s.timeH) && Number.isFinite(s.temp))
    .sort((a, b) => a.timeH - b.timeH)
  let m = 0
  const out: (T & { m: number })[] = []
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0) {
      const dt = sorted[i].timeH - sorted[i - 1].timeH
      m += nurseSaulIntervalDm(sorted[i - 1].temp, sorted[i].temp, t0, dt)
      m = Math.max(0, m)
    }
    out.push({ ...sorted[i], m: i === 0 ? 0 : m })
  }
  return out
}

/** Lock start→now as one Excel interval (when only two temps are known). */
export function nurseSaulMaturityLocked(
  tStart: number,
  tNow: number,
  t0: number,
  elapsedSec: number,
): number {
  const hours = Math.max(0, elapsedSec) / 3600
  return Math.max(0, nurseSaulIntervalDm(tStart, tNow, t0, hours))
}

export function fitLogMaturity(points: { x: number; y: number }[]): MaturityFit | null {
  const samples = points.filter((p) => p.x > 0 && p.y > 0)
  if (samples.length < 2) return null

  const xs = samples.map((p) => Math.log(p.x))
  const ys = samples.map((p) => p.y)
  const n = samples.length
  const meanX = xs.reduce((s, v) => s + v, 0) / n
  const meanY = ys.reduce((s, v) => s + v, 0) / n

  let sxx = 0
  let sxy = 0
  let syy = 0
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - meanX
    const dy = ys[i] - meanY
    sxx += dx * dx
    sxy += dx * dy
    syy += dy * dy
  }
  if (sxx === 0) return null

  const b = sxy / sxx
  const a = meanY - b * meanX
  const r2 = syy === 0 ? 1 : Math.min(1, Math.max(0, (sxy * sxy) / (sxx * syy)))

  return { a, b, r2, n }
}

export function formatFcEquation(a: number, b: number): string {
  const aPart = a < 0 ? `−${Math.abs(a).toFixed(3)}` : a.toFixed(3)
  const bPart =
    b < 0 ? `− ${Math.abs(b).toFixed(4)}` : `+ ${b.toFixed(4)}`
  return `fc = ${aPart} ${bPart} ln(M)`
}

export function formatCoeff(v: number, digits = 4): string {
  if (!Number.isFinite(v)) return '—'
  const rounded = Number(v.toFixed(digits))
  if (Object.is(rounded, -0) || rounded === 0) return (0).toFixed(digits)
  return rounded < 0 ? `−${Math.abs(rounded).toFixed(digits)}` : rounded.toFixed(digits)
}

/** Excel FKZ row: factor keyed by lab age day. */
export type FkzFactor = { day: number; fkz: number }

/**
 * Excel FAKTOR KOREKSI ZAKKI from Error = (fc_NS − fc_lab) / fc_lab:
 * - Error > 0            → FKZ = 1 / (1 + Error)
 * - −10% < Error ≤ 0%    → FKZ = 1
 * - Error ≤ −10%         → FKZ = 1 + (|Error| − 10%)
 */
export function fkzFromError(error: number): number {
  if (!Number.isFinite(error)) return 1
  if (error > 0) return 1 / (1 + error)
  if (error > -0.1) return 1
  return 1 + (Math.abs(error) - 0.1)
}

/**
 * Build per-age FKZ using Excel piecewise rules (not raw fc_lab/fc_NS).
 * Only ages with crushing-test fc are calibrated.
 */
export function computeFkzFactors(
  samples: { day: number; timeH: number; temp: number; fc: number }[],
  t0: number,
  a: number,
  b: number,
): FkzFactor[] {
  const withM = accumulateNurseSaulM(samples, t0)
  const byDay = new Map<number, number>()
  for (const s of withM) {
    if (!(s.fc > 0) || !(s.m > 0)) continue
    const pred = a + b * Math.log(s.m)
    if (!(pred > 0) || !Number.isFinite(pred)) continue
    const error = (pred - s.fc) / s.fc
    const fkz = fkzFromError(error)
    if (!Number.isFinite(fkz) || fkz <= 0) continue
    byDay.set(s.day, fkz)
  }
  return [...byDay.entries()]
    .map(([day, fkz]) => ({ day, fkz }))
    .sort((x, y) => x.day - y.day)
}

/**
 * Exact day match; if missing, use next calibrated day forward
 * (e.g. FKZ on 5 & 7, day 6 empty → use day 7). Past last age → last FKZ.
 * No factors → 1 (no correction).
 */
export function lookupFkz(factors: FkzFactor[] | undefined, day: number): number {
  if (!factors?.length || !Number.isFinite(day)) return 1
  const sorted = [...factors]
    .filter((f) => f.fkz > 0 && Number.isFinite(f.fkz))
    .sort((a, b) => a.day - b.day)
  if (sorted.length === 0) return 1
  const exact = sorted.find((f) => f.day === day)
  if (exact) return exact.fkz
  const next = sorted.find((f) => f.day > day)
  if (next) return next.fkz
  return sorted[sorted.length - 1].fkz
}

/**
 * Excel: fc_FKZ = (a + b·ln(M)) · FKZ; floor at 0.
 */
export function predictFcWithFkz(
  maturity: number,
  a: number,
  b: number,
  fkz = 1,
): number {
  if (!(maturity > 0) || !Number.isFinite(a) || !Number.isFinite(b)) return 0
  const raw = a + b * Math.log(maturity)
  const factor = Number.isFinite(fkz) && fkz > 0 ? fkz : 1
  return Math.max(0, raw * factor)
}
