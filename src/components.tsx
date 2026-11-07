import type { InputHTMLAttributes, ReactNode } from 'react'
import { IconChevronRight, UiIcon } from './icons'

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
  rule = 'full',
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

export function MaturityChart({
  points,
  compact,
}: {
  points: { x: number; y: number }[]
  compact?: boolean
}) {
  const w = 400
  const h = compact ? 132 : 190
  const padL = 34
  const padR = 12
  const padT = 10
  const padB = 28
  const logMin = 1
  const logMax = 5
  const maxY = 50
  const sx = (x: number) =>
    padL + ((Math.log10(Math.max(x, 1)) - logMin) / (logMax - logMin)) * (w - padL - padR)
  const sy = (y: number) => padT + (1 - y / maxY) * (h - padT - padB)
  const d = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${sx(p.x).toFixed(1)} ${sy(p.y).toFixed(1)}`)
    .join(' ')
  const midY = padT + (h - padT - padB) / 2

  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Maturity chart">
      {[0, 10, 20, 30, 40, 50].map((y) => (
        <g key={y}>
          <line x1={padL} y1={sy(y)} x2={w - padR} y2={sy(y)} className="chart-grid" />
          <text x={padL - 5} y={sy(y) + 3} textAnchor="end" className="chart-tick">
            {y}
          </text>
        </g>
      ))}
      {[1, 2, 3, 4, 5].map((exp) => (
        <text
          key={exp}
          x={sx(10 ** exp)}
          y={h - 16}
          textAnchor="middle"
          className="chart-tick"
        >
          {`10${'¹²³⁴⁵'[exp - 1]}`}
        </text>
      ))}
      <path d={d} className="chart-line" fill="none" />
      {points.map((p) => (
        <circle key={`${p.x}-${p.y}`} cx={sx(p.x)} cy={sy(p.y)} r={4} className="chart-dot" />
      ))}
      <text
        className="chart-axis-label"
        textAnchor="middle"
        transform={`translate(11 ${midY}) rotate(-90)`}
      >
        Compressive Strength (MPa)
      </text>
      <text x={(padL + w - padR) / 2} y={h - 2} textAnchor="middle" className="chart-axis-label">
        Maturity Index, M (°C·hour)
      </text>
    </svg>
  )
}
