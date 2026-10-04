import { type ReactNode } from 'react'
import { Link, Outlet, useNavigate, useSearchParams } from 'react-router-dom'

import { useClock } from '../../app/useClock'
import { Button } from '../../ui/Button'
import { hm } from './api'
import { useOnline } from './useOnline'
import './store.css'

const icons = {
  arrow: 'ac5dd.svg',
  arrowDark: 'a503e.svg',
  back: '9b7f2.svg',
  info: 'fc4fe.svg',
  receiptInfo: '69525.svg',
  package: '2acc0.svg',
  pin: 'a7639.svg',
  clock: '51022.svg',
  home: '54911.svg',
  list: 'f426d.svg',
  alert: '62116.svg',
  user: 'e7954.svg',
  calendar: '5cc80.svg',
  snowflake: 'f0fee.svg',
  minus: 'ba655.svg',
  plus: '8f150.svg',
  add: '2c1ca.svg',
  trash: '8ee50.svg',
  camera: 'a9c0e.svg',
  smallMinus: '46483.svg',
  smallPlus: '3451f.svg',
  chevron: '7e3bc.svg',
  reportAdd: 'db816.svg',
  globe: '9d7fd.svg',
} as const
export function StoreIcon({ name }: { name: keyof typeof icons }) {
  return <img alt="" className="store-icon" src={`/figma/store/${icons[name]}`} />
}
export function StoreShell() {
  const clock = useClock()
  const online = useOnline()
  return (
    <div className="store-shell">
      <div className="store-os">
        <span>{hm(clock.data?.now)}</span>
        <div className="store-signals" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </div>
        <span className="store-battery" aria-hidden="true" />
      </div>
      {!online && (
        <p className="store-offline" role="status">
          No signal · reconnect to send changes
        </p>
      )}
      <Outlet />
    </div>
  )
}
export function StoreHeader({
  title,
  subtitle,
  back = true,
}: {
  title: string
  subtitle: string
  back?: boolean
}) {
  const navigate = useNavigate()
  return (
    <header className={`store-header ${back ? '' : 'store-header-home'}`}>
      {back && (
        <button aria-label="Back" onClick={() => navigate('/store')}>
          <StoreIcon name="back" />
        </button>
      )}
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
    </header>
  )
}
export function StoreNav() {
  const [params] = useSearchParams()
  const active = params.get('view') ?? 'home'
  return (
    <nav className="store-nav" aria-label="Store navigation">
      {(
        [
          { to: '/store', label: 'Home', icon: 'home' },
          { to: '/store?view=orders', label: 'Orders', icon: 'list' },
          { to: '/store?view=issues', label: 'Issues', icon: 'alert' },
          { to: '/store?view=account', label: 'Account', icon: 'user' },
        ] as const
      ).map((t) => (
        <Link
          key={t.label}
          to={t.to}
          className={active === t.label.toLowerCase() ? 'active' : ''}
          aria-current={active === t.label.toLowerCase() ? 'page' : undefined}
        >
          <StoreIcon name={t.icon} />
          <span>{t.label}</span>
        </Link>
      ))}
    </nav>
  )
}
export function StoreAction({
  children,
  onClick,
  disabled,
  secondary = false,
}: {
  children: ReactNode
  onClick: () => void
  disabled?: boolean
  secondary?: boolean
}) {
  return (
    <Button
      size="lg"
      variant={secondary ? 'outline' : 'secondary'}
      className="store-action"
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </Button>
  )
}
export function Stepper({
  value,
  onChange,
  label,
  compact = false,
}: {
  value: number
  onChange: (n: number) => void
  label: string
  compact?: boolean
}) {
  return (
    <div className={`store-stepper ${compact ? 'compact' : ''}`}>
      <button aria-label={`Decrease ${label}`} onClick={() => onChange(Math.max(0, value - 1))}>
        <StoreIcon name={compact ? 'smallMinus' : 'minus'} />
      </button>
      <input
        aria-label={`${label} cases`}
        type="number"
        min="0"
        inputMode="numeric"
        value={value}
        onChange={(e) => onChange(Math.max(0, Number(e.target.value) || 0))}
      />
      <button aria-label={`Increase ${label}`} onClick={() => onChange(value + 1)}>
        <StoreIcon name={compact ? 'smallPlus' : 'plus'} />
      </button>
    </div>
  )
}
export function StoreState({
  loading,
  error,
  retry,
}: {
  loading?: boolean
  error?: Error | null
  retry?: () => void
}) {
  return (
    <div className="store-state" role={error ? 'alert' : 'status'}>
      <p>{loading ? 'Loading…' : error?.message || 'No orders yet'}</p>
      {error && retry && (
        <Button variant="outline" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  )
}
