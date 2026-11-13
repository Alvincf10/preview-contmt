import { useEffect, useState, type InputHTMLAttributes, type ReactNode } from 'react'
import { IconChevronRight, IconThermo, UiIcon } from './icons'

export function TempStrip({
  temps,
  live = true,
}: {
  temps: [number, number, number]
  live?: boolean
}) {
  const [values, setValues] = useState(temps)

  useEffect(() => {
    setValues(temps)
  }, [temps])

  useEffect(() => {
    if (!live) return
    const t = window.setInterval(() => {
      setValues((prev) =>
        prev.map((v) => +(v + (Math.random() - 0.5) * 0.12).toFixed(1)) as [
          number,
          number,
          number,
        ],
      )
    }, 1000)
    return () => window.clearInterval(t)
  }, [live])

  return (
    <div className="temp-strip" aria-label="Live sensor temperatures">
      {values.map((t, i) => (
        <div key={i} className="temp-strip-cell">
          <IconThermo className="ico ico-accent temp-strip-ico" />
          <span className="temp-strip-label">S{i + 1}</span>
          <strong className="temp-strip-value">{t.toFixed(1)}°</strong>
        </div>
      ))}
    </div>
  )
}

export function PhoneShell({ children }: { children: ReactNode }) {
  return (
    <div className="desk">
      <div className="phone">{children}</div>
    </div>
  )
}

export function Screen({
  title,
  subtitle,
  children,
  footer,
  topLeft,
  back,
  scroll = true,
  bare,
  overlay,
  bodyClassName,
  className,
  rule = 'short',
}: {
  title?: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
  topLeft?: ReactNode
  back?: ReactNode
  scroll?: boolean
  bare?: boolean
  overlay?: ReactNode
  bodyClassName?: string
  className?: string
  rule?: 'full' | 'short'
}) {
  return (
    <div className={`screen${className ? ` ${className}` : ''}`}>
      <div className="screen-bg" aria-hidden />
      <div className="brand-bar" aria-hidden />
      {topLeft ? <div className="top-left-slot">{topLeft}</div> : null}
      <div className="stage">
        <div className={`panel${scroll ? '' : ' panel-fixed'}${bare ? ' panel-bare' : ''}`}>
          {back || title ? (
            <div className={`panel-head${back ? ' panel-head-back' : ''}`}>
              {back ? <div className="panel-back">{back}</div> : null}
              {title ? (
                <>
                  <h1 className="panel-title">{title}</h1>
                  <div className={`panel-rule${rule === 'short' ? ' panel-rule-short' : ''}`} />
                  {subtitle ? <p className="panel-sub">{subtitle}</p> : null}
                </>
              ) : null}
            </div>
          ) : null}
          <div className={`panel-body${bodyClassName ? ` ${bodyClassName}` : ''}`}>{children}</div>
          {footer ? <div className="panel-footer">{footer}</div> : null}
        </div>
      </div>
      {overlay}
    </div>
  )
}

export function BtnPrimary({
  children,
  onClick,
  iconLeft,
  iconRight,
  block,
  compact,
  className,
}: {
  children: ReactNode
  onClick?: () => void
  iconLeft?: ReactNode
  iconRight?: ReactNode
  block?: boolean
  compact?: boolean
  className?: string
}) {
  return (
    <button
      type="button"
      className={`btn btn-orange${block ? ' btn-block' : ''}${compact ? ' btn-compact' : ''}${className ? ` ${className}` : ''}`}
      onClick={onClick}
    >
      {iconLeft}
      {!compact && (iconLeft || iconRight) ? <span className="btn-divider" /> : null}
      <span className="btn-label">{children}</span>
      {iconRight}
    </button>
  )
}

export function BtnGhost({
  children,
  onClick,
  withChevron,
  block,
  className,
}: {
  children: ReactNode
  onClick?: () => void
  withChevron?: boolean
  block?: boolean
  className?: string
}) {
  return (
    <button
      type="button"
      className={`btn btn-dark${block ? ' btn-block' : ''}${className ? ` ${className}` : ''}`}
      onClick={onClick}
    >
      {withChevron ? <UiIcon name="back-chevron" size="back" className="ico-accent" /> : null}
      <span className="btn-label">{children}</span>
    </button>
  )
}

export function NavFooter({
  onBack,
  onNext,
  nextLabel = 'NEXT',
  backLabel = 'BACK',
  nextIcon,
  nextClassName,
  backClassName,
  backWithChevron = true,
}: {
  onBack?: () => void
  onNext?: () => void
  nextLabel?: string
  backLabel?: string
  nextIcon?: ReactNode
  nextClassName?: string
  backClassName?: string
  backWithChevron?: boolean
}) {
  return (
    <div className={`nav-row${onNext ? '' : ' nav-row-single'}`}>
      {onBack ? (
        <BtnGhost onClick={onBack} withChevron={backWithChevron} className={backClassName}>
          {backLabel}
        </BtnGhost>
      ) : null}
      {onNext ? (
        <BtnPrimary onClick={onNext} iconRight={nextIcon} className={nextClassName}>
          {nextLabel}
        </BtnPrimary>
      ) : null}
    </div>
  )
}

export function MenuRow({
  icon,
  label,
  desc,
  onClick,
}: {
  icon: ReactNode
  label: string
  desc?: string
  onClick: () => void
}) {
  return (
    <button type="button" className={`menu-row${desc ? ' menu-row-desc' : ''}`} onClick={onClick}>
      <span className="menu-row-icon">{icon}</span>
      <span className="menu-row-text">
        <strong>{label}</strong>
        {desc ? <em>{desc}</em> : null}
      </span>
      <IconChevronRight className="ico ico-sm ico-white menu-row-chevron" />
    </button>
  )
}

export function FieldBlock({
  label,
  icon,
  children,
}: {
  label: string
  icon?: ReactNode
  children: ReactNode
}) {
  return (
    <label className="field-block">
      <span className="field-label">
        {icon}
        {label}
      </span>
      {children}
    </label>
  )
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="text-input" {...props} />
}

export function UnitBox({ children }: { children: ReactNode }) {
  return <span className="unit-box">{children}</span>
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="section-title">{children}</div>
}

export function StatusPill({
  children,
  tone = 'orange',
}: {
  children: ReactNode
  tone?: 'orange' | 'green'
}) {
  return <span className={`status-pill status-${tone}`}>{children}</span>
}

export function ConfirmDialog({
  title,
  body,
  confirmLabel = 'DELETE',
  cancelLabel = 'CANCEL',
  onConfirm,
  onCancel,
}: {
  title: string
  body?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="confirm-overlay" role="presentation" onClick={onCancel}>
      <div
        className="confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="confirm-title" className="confirm-title">
          {title}
        </h2>
        {body ? <div className="confirm-body">{body}</div> : null}
        <div className="confirm-actions">
          <BtnGhost onClick={onCancel}>{cancelLabel}</BtnGhost>
          <BtnPrimary onClick={onConfirm}>{confirmLabel}</BtnPrimary>
        </div>
      </div>
    </div>
  )
}

const MATURITY_X_MAJOR = 5000
const MATURITY_X_MINOR = 2500
const MATURITY_Y_MAJOR = 10
const MATURITY_Y_MINOR = 5

function formatMaturityTick(v: number): string {
  if (v === 0) return '0'
  if (v % 1000 === 0) return `${v / 1000}k`
  return v.toLocaleString('en-US')
}

function rangeStep(max: number, step: number): number[] {
  const n = Math.floor(max / step)
  return Array.from({ length: n + 1 }, (_, i) => i * step)
}

export function MaturityChart({
  points,
  compact,
}: {
  points: { x: number; y: number }[]
  compact?: boolean
}) {
  const w = 400
  const h = compact ? 160 : 210
  const padL = 36
  const padR = 14
  const padT = 10
  const padB = 36
  const maxY = 50
  const dataMaxX = Math.max(0, ...points.map((p) => p.x))
  // Linear axis like lab Excel: major X every 5000 °C·h, dense helper grid
  const maxX = Math.max(
    MATURITY_X_MAJOR * 4,
    Math.ceil(dataMaxX / MATURITY_X_MAJOR) * MATURITY_X_MAJOR,
  )
  const xMajor = rangeStep(maxX, MATURITY_X_MAJOR)
  const xMinor = rangeStep(maxX, MATURITY_X_MINOR)
  const yMajor = rangeStep(maxY, MATURITY_Y_MAJOR)
  const yMinor = rangeStep(maxY, MATURITY_Y_MINOR)
  const sorted = [...points].sort((a, b) => a.x - b.x)
  const sx = (x: number) => padL + (x / maxX) * (w - padL - padR)
  const sy = (y: number) => padT + (1 - y / maxY) * (h - padT - padB)
  const d = sorted
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${sx(p.x).toFixed(1)} ${sy(p.y).toFixed(1)}`)
    .join(' ')
  const midY = padT + (h - padT - padB) / 2
  const labelEvery = xMajor.length > 9 ? 2 : 1

  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Maturity chart">
      {/* Minor helper grid (Excel-style) */}
      {yMinor.map((y) =>
        y % MATURITY_Y_MAJOR === 0 ? null : (
          <line
            key={`hy-min-${y}`}
            x1={padL}
            y1={sy(y)}
            x2={w - padR}
            y2={sy(y)}
            className="chart-grid-minor"
          />
        ),
      )}
      {xMinor.map((x) =>
        x % MATURITY_X_MAJOR === 0 ? null : (
          <line
            key={`vx-min-${x}`}
            x1={sx(x)}
            y1={padT}
            x2={sx(x)}
            y2={h - padB}
            className="chart-grid-minor"
          />
        ),
      )}
      {/* Major grid + labels */}
      {yMajor.map((y) => (
        <g key={`hy-${y}`}>
          <line x1={padL} y1={sy(y)} x2={w - padR} y2={sy(y)} className="chart-grid-major" />
          <text x={padL - 5} y={sy(y) + 3} textAnchor="end" className="chart-tick">
            {y}
          </text>
        </g>
      ))}
      {xMajor.map((x) => (
        <line
          key={`vx-${x}`}
          x1={sx(x)}
          y1={padT}
          x2={sx(x)}
          y2={h - padB}
          className="chart-grid-major"
        />
      ))}
      {xMajor.map((x, i) =>
        i % labelEvery === 0 ? (
          <text key={`xl-${x}`} x={sx(x)} y={h - padB + 14} textAnchor="middle" className="chart-tick">
            {formatMaturityTick(x)}
          </text>
        ) : null,
      )}
      <rect
        x={padL}
        y={padT}
        width={w - padL - padR}
        height={h - padT - padB}
        className="chart-frame"
      />
      <path d={d} className="chart-line" fill="none" />
      {sorted.map((p) => (
        <circle key={`${p.x}-${p.y}`} cx={sx(p.x)} cy={sy(p.y)} r={4} className="chart-dot" />
      ))}
      <text
        className="chart-axis-label"
        textAnchor="middle"
        transform={`translate(11 ${midY}) rotate(-90)`}
      >
        Compressive Strength (MPa)
      </text>
      <text
        x={(padL + w - padR) / 2}
        y={h - 4}
        textAnchor="middle"
        className="chart-axis-label"
      >
        Maturity Index, M (°C·hour)
      </text>
    </svg>
  )
}
