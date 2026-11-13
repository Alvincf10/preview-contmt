type IconProps = { className?: string }

export type UiIconName =
  | 'menu-baseline'
  | 'menu-kuat-tekan'
  | 'menu-settings'
  | 'menu-device-info'
  | 'baseline-new'
  | 'baseline-saved'
  | 'kuat-start'
  | 'kuat-history'
  | 'back-chevron'

/** Design-exported glyphs via CSS mask so color follows currentColor. */
export function UiIcon({
  name,
  size = 'md',
  className,
}: {
  name: UiIconName
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'back'
  className?: string
}) {
  const src = `/ui-icons/${name}.png`
  return (
    <span
      className={`ui-ico ui-ico-${size}${className ? ` ${className}` : ''}`}
      style={{ WebkitMaskImage: `url(${src})`, maskImage: `url(${src})` }}
      aria-hidden
    />
  )
}

/** Exact paths from Figma export: Baseline — 480 × 800.svg */
export function IconBaselineNew({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 48 58" fill="none" aria-hidden>
      <path d="M30 0V14H42" stroke="currentColor" strokeWidth="3" />
      <path
        d="M18.9 57H5.25C1.75 57 0 55.241 0 51.722V5.278C0 1.759 1.75 0 5.25 0H29.4L42 13.722V23.222"
        stroke="currentColor"
        strokeWidth="3.5"
      />
      <circle cx="32.5" cy="38.5" r="14.5" fill="currentColor" />
      <rect x="30.75" y="30.25" width="3.5" height="17" rx="1.75" fill="#F27B09" />
      <rect x="24" y="37" width="17" height="3.5" rx="1.75" fill="#F27B09" />
    </svg>
  )
}

/** Exact paths from Figma export: Baseline — 480 × 800.svg */
export function IconBaselineSaved({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 43 64" fill="none" aria-hidden>
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M0 12.887C0 0 43 0 43 12.887C43 25.774 0 25.774 0 12.887ZM0 18.835C9 27.757 34 27.757 43 18.835V27.757C43 40.644 0 40.644 0 27.757V18.835ZM0 32.713C9 41.635 34 41.635 43 32.713V41.635C43 54.522 0 54.522 0 41.635V32.713ZM0 46.592C9 55.513 34 55.513 43 46.592V50.557C43 63.444 0 63.444 0 50.557V46.592Z"
        fill="currentColor"
      />
    </svg>
  )
}

export function IconUser({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.45" />
      <path d="M5 19c1.8-3.2 4-4.8 7-4.8S17.2 15.8 19 19" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

export function IconDoc({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M7 3.5h7l4 4V20.5H7V3.5Z" stroke="currentColor" strokeWidth="1.45" />
      <path d="M14 3.5V8h4" stroke="currentColor" strokeWidth="1.45" />
      <path d="M9.5 12h5M9.5 15.5h5" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
    </svg>
  )
}

export function IconCalendar({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="4" y="5" width="16" height="15" rx="2" stroke="currentColor" strokeWidth="1.45" />
      <path d="M8 3.5v3M16 3.5v3M4 9.5h16" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

export function IconSave({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M5 4h11l3 3v13H5V4Z" stroke="currentColor" strokeWidth="1.45" />
      <path d="M8 4v5h8V4M8 18v-5h8v5" stroke="currentColor" strokeWidth="1.45" />
    </svg>
  )
}

export function IconChart({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M5 19V5M5 19h14" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
      <path d="M8 15l3.5-4 3 2.5L18 8" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function IconPress({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M7 4h10M8 8h8M12 8v5" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
      <path d="M9 13h6l1 6H8l1-6Z" stroke="currentColor" strokeWidth="1.45" />
    </svg>
  )
}

export function IconGear({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.45" />
      <path
        d="M12 3.5v2.2M12 18.3v2.2M3.5 12h2.2M18.3 12h2.2M6.1 6.1l1.6 1.6M16.3 16.3l1.6 1.6M17.9 6.1l-1.6 1.6M7.7 16.3l-1.6 1.6"
        stroke="currentColor"
        strokeWidth="1.45"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function IconInfo({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.45" />
      <path d="M12 10.5V17M12 7.2v1.2" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

export function IconChevronRight({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M9 5l7 7-7 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function IconChevronLeft({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M15 5l-7 7 7 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function IconPlusDoc({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M7 3.5h7l4 4V20.5H7V3.5Z" stroke="currentColor" strokeWidth="1.45" />
      <path d="M14 3.5V8h4M10 14h4M12 12v4" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

export function IconDatabase({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <ellipse cx="12" cy="6" rx="6.5" ry="2.5" stroke="currentColor" strokeWidth="1.45" />
      <path d="M5.5 6v4c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5V6" stroke="currentColor" strokeWidth="1.45" />
      <path d="M5.5 10v4c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5v-4" stroke="currentColor" strokeWidth="1.45" />
      <path d="M5.5 14v4c0 1.4 2.9 2.5 6.5 2.5s6.5-1.1 6.5-2.5v-4" stroke="currentColor" strokeWidth="1.45" />
    </svg>
  )
}

export function IconThermo({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M10 14.5V5.5a2 2 0 1 1 4 0v9" stroke="currentColor" strokeWidth="1.45" />
      <circle cx="12" cy="17" r="3.2" stroke="currentColor" strokeWidth="1.45" />
    </svg>
  )
}

export function IconClock({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.45" />
      <path d="M12 7.5V12l3 2" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

/** Nextion-friendly battery glyph: body + tip, fill level via CSS var --batt-pct. */
export function IconBattery({ className, pct = 80 }: IconProps & { pct?: number }) {
  const level = Math.max(0, Math.min(100, pct))
  const fillW = 12.5 * (level / 100)
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="2.5" y="7" width="16" height="10" rx="1.6" stroke="currentColor" strokeWidth="1.45" />
      <path d="M19.5 10v4h1.2a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1H19.5Z" fill="currentColor" />
      <rect x="4.2" y="8.7" width={fillW} height="6.6" rx="0.8" fill="currentColor" opacity={0.95} />
    </svg>
  )
}

export function IconCheck({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.45" />
      <path d="M8 12.2l2.6 2.6L16.2 9" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function IconHistory({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M7 3.5h7l4 4V20.5H7V3.5Z" stroke="currentColor" strokeWidth="1.45" />
      <circle cx="15.5" cy="16.5" r="4" stroke="currentColor" strokeWidth="1.35" fill="rgba(0,0,0,.35)" />
      <path d="M15.5 14.6V16.5l1.3.9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

export function IconDevice({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="3.5" y="5" width="17" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.45" />
      <path d="M8 19h8M12 16v3" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

export function IconChip({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="7" y="7" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.45" />
      <path d="M10 4v3M14 4v3M10 17v3M14 17v3M4 10h3M4 14h3M17 10h3M17 14h3" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

export function IconSun({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="3.5" stroke="currentColor" strokeWidth="1.45" />
      <path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M6 6l1.4 1.4M16.6 16.6L18 18M18 6l-1.4 1.4M7.4 16.6 6 18" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

export function IconSound({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 10v4h3l4 3.5V6.5L7 10H4Z" stroke="currentColor" strokeWidth="1.45" strokeLinejoin="round" />
      <path d="M15 9.2a3.5 3.5 0 0 1 0 5.6M17.5 7a6 6 0 0 1 0 10" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

export function IconBuilding({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M5 20V6l7-2.5L19 6v14H5Z" stroke="currentColor" strokeWidth="1.45" />
      <path d="M9 10h1.5M13.5 10H15M9 14h1.5M13.5 14H15M11 20v-3" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
    </svg>
  )
}
