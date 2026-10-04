import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'

import { setSession } from '../../auth/session'
import { isPending, type OutboxEvent, useOnline } from './outbox'

/** Exact exported Figma assets for field screens (Hi-fi · Driver / Loader); sizes preserved. */
const ICONS = {
  arrowRight: '815c3.svg',
  chevronLeft: '9b7f2.svg',
  check: '46947.svg',
  checkWhite: 'a6c6e.svg',
  snowSmall: 'c6f57.svg',
  info: '69525.svg',
  tabTrip: '28ac5.svg',
  tabUploads: '27fa2.svg',
  tabDispatch: '2c785.svg',
  tabMe: 'e7954.svg',
  alertTriangle: 'a0a42.svg',
  truck: '2ea93.svg',
  pin: 'bce03.svg',
  snowflake: '835a9.svg',
  lock: '9dbf4.svg',
  camera: '24d78.svg',
  warning: '1b0a1.svg',
  wifiOff: 'a1482.svg',
} as const

export type IconName = keyof typeof ICONS

export function Icon({ name }: { name: IconName }) {
  return <img alt="" src={`/figma/${ICONS[name]}`} className="block max-w-none shrink-0" />
}

/** Header / Mobile: names the vehicle, trip and plan version on every field screen (C4). */
export function FieldHeader({
  title,
  subtitle,
  back,
  signOut = false,
}: {
  title: string
  subtitle: string
  back?: string
  /** Show a Sign out action, for field roles without the tab bar (loader). */
  signOut?: boolean
}) {
  const navigate = useNavigate()
  return (
    <header className="flex w-full items-center gap-2 border-b border-line bg-surface px-4 pb-[10px] pt-2">
      {back && (
        <Link to={back} aria-label="Back" className="flex h-11 w-8 shrink-0 items-center">
          <Icon name="chevronLeft" />
        </Link>
      )}
      <div className="flex min-w-0 flex-1 flex-col font-semibold">
        <p className="truncate text-base leading-5 text-primary">{title}</p>
        <p className="truncate text-sm leading-[18px] text-secondary">{subtitle}</p>
      </div>
      {signOut && (
        <button
          type="button"
          className="flex h-11 shrink-0 items-center text-sm font-semibold text-brand-text"
          onClick={() => {
            setSession(null)
            navigate('/login')
          }}
        >
          Sign out
        </button>
      )}
    </header>
  )
}

/**
 * Sync bar: pinned under the header on every driver and loader screen (D-006, docs/07 › 6).
 * Offline is a working state, not an alert.
 */
export function SyncBar({
  events,
  onlineTitle = 'Online',
  onlineDetail = 'Nothing waiting to upload',
  reviewTo,
}: {
  events: OutboxEvent[]
  onlineTitle?: string
  onlineDetail?: string
  reviewTo?: (event: OutboxEvent) => string
}) {
  const online = useOnline()
  const pending = events.filter(isPending).length
  const conflicts = events.filter((e) => e.status === 'conflict' || e.status === 'rejected')
  const saved = `${pending} ${pending === 1 ? 'record' : 'records'} saved on this phone`

  if (conflicts.length > 0) {
    const first = conflicts[0]!
    return (
      <Bar tone="bg-warning-bg text-warning-fg" icon="warning">
        <BarText
          title={`${conflicts.length} ${conflicts.length === 1 ? 'record needs' : 'records need'} dispatcher review`}
          detail={
            first.status === 'conflict'
              ? 'Store count differs from yours'
              : (first.result?.detail ?? '')
          }
        />
        {reviewTo && (
          <Link
            to={reviewTo(first)}
            className="shrink-0 text-sm font-semibold leading-[18px] underline"
          >
            Review
          </Link>
        )}
      </Bar>
    )
  }
  if (!online) {
    return (
      <Bar tone="bg-inverse text-on-inverse" icon="wifiOff">
        <BarText
          title="No signal · keep working"
          detail={pending ? `${saved} · uploads by itself` : 'Nothing waiting to upload'}
        />
      </Bar>
    )
  }
  if (pending > 0) {
    return (
      <Bar tone="bg-inverse text-on-inverse" icon="wifiOff">
        <BarText title={`Uploading ${pending}`} detail={saved} />
      </Bar>
    )
  }
  return (
    <Bar tone="bg-success-bg text-success-fg" icon="check">
      <BarText title={onlineTitle} detail={onlineDetail} />
    </Bar>
  )
}

function Bar({ tone, icon, children }: { tone: string; icon: IconName; children: ReactNode }) {
  return (
    <div role="status" className={`flex w-full items-center gap-3 px-4 py-[10px] ${tone}`}>
      <span className="flex size-5 shrink-0 items-center justify-center">
        <Icon name={icon} />
      </span>
      {children}
    </div>
  )
}

function BarText({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <p className="text-sm font-semibold leading-[18px]">{title}</p>
      <p className="text-xs leading-4 opacity-85">{detail}</p>
    </div>
  )
}

/** Section header: Xora/Caption, optional mono meta on the right. */
export function Caption({
  children,
  meta,
  tone = 'text-secondary',
  pad = 'pb-2 pt-5',
}: {
  children: ReactNode
  meta?: ReactNode
  tone?: string
  pad?: string
}) {
  return (
    <div className={`flex w-full items-center gap-2 px-4 ${pad}`}>
      <p
        className={`flex-1 text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] ${tone}`}
      >
        {children}
      </p>
      {meta && (
        <p className="shrink-0 font-mono text-[11px] font-medium leading-[14px] tracking-[0.22px] text-secondary">
          {meta}
        </p>
      )}
    </div>
  )
}

type Kind = 'accent' | 'secondary' | 'ghost'

/** Field button: L = 56 px targets; Accent = orange for field-critical actions (Figma Button). */
export function FieldButton({
  kind = 'accent',
  arrow = kind === 'accent',
  className = '',
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { kind?: Kind; arrow?: boolean }) {
  const styles: Record<Kind, string> = {
    accent: 'h-14 px-5 text-base leading-5 bg-brand text-on-brand',
    secondary: 'h-14 px-5 text-base leading-5 border border-line-strong bg-surface text-primary',
    ghost: 'h-10 px-4 text-sm leading-[18px] text-primary',
  }
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-md font-semibold disabled:cursor-not-allowed disabled:bg-disabled disabled:text-[var(--text-disabled)] ${styles[kind]} ${className}`}
      {...props}
    >
      {children}
      {arrow && <Icon name="arrowRight" />}
    </button>
  )
}

/** Key/value row (KV component). */
export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex w-full items-start gap-3 border-b border-line bg-surface px-4 py-[11px] text-sm">
      <p className="shrink-0 leading-5 text-secondary">{label}</p>
      <p className="flex-1 text-right font-semibold leading-[18px] text-primary">{value}</p>
    </div>
  )
}

/** Tab bar / Field: docked, flat, upload count always visible. */
export function FieldTabBar({
  pending,
  home,
  uploads,
}: {
  pending: number
  home: string
  uploads?: string
}) {
  const navigate = useNavigate()
  const tab =
    'flex flex-1 flex-col items-center gap-1 pb-2 pt-[10px] text-xs font-semibold leading-4'
  const indicator = (active: boolean) => `h-[3px] w-8 ${active ? 'bg-brand' : 'bg-surface'}`
  return (
    <nav className="sticky bottom-0 flex w-full items-start border-t border-line bg-surface pb-5">
      <NavLink to={home} end className={tab}>
        {({ isActive }) => (
          <>
            <span className={indicator(isActive)} />
            <Icon name="tabTrip" />
            <span className={isActive ? 'text-primary' : 'text-tertiary'}>Trip</span>
          </>
        )}
      </NavLink>
      {uploads && (
        <NavLink to={uploads} className={tab}>
          {({ isActive }) => (
            <>
              <span className={indicator(isActive)} />
              <Icon name="tabUploads" />
              <span className={isActive ? 'text-primary' : 'text-tertiary'}>
                {pending > 0 ? `Uploads · ${pending}` : 'Uploads'}
              </span>
            </>
          )}
        </NavLink>
      )}
      <a href="tel:" className={tab} aria-label="Call dispatch">
        <span className={indicator(false)} />
        <Icon name="tabDispatch" />
        <span className="text-tertiary">Dispatch</span>
      </a>
      <button
        type="button"
        className={tab}
        onClick={() => {
          setSession(null)
          navigate('/login')
        }}
      >
        <span className={indicator(false)} />
        <Icon name="tabMe" />
        <span className="text-tertiary">Me</span>
      </button>
    </nav>
  )
}

/** Shared status vocabulary (D-005, BR-54): pip + label, colour is never alone. */
export function StatusPip({
  label,
  tone,
}: {
  label: string
  tone: 'brand' | 'success' | 'danger' | 'neutral'
}) {
  const tones = {
    brand: ['bg-brand-subtle text-brand-text', 'bg-brand'],
    success: ['bg-success-bg text-success-fg', 'bg-success-fg'],
    danger: ['bg-danger-bg text-danger-fg', 'bg-danger-fg'],
    neutral: ['bg-neutral-bg text-neutral-fg', 'bg-neutral-fg'],
  }[tone]
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-sm py-[3px] pl-[7px] pr-2 ${tones[0]}`}
    >
      <span className={`size-1.5 rounded-[1px] ${tones[1]}`} />
      <span className="text-xs font-semibold leading-4">{label}</span>
    </span>
  )
}
