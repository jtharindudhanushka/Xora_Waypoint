import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { FigmaIcon } from '../ui/FigmaIcon'

import { useSession } from '../auth/useSession'
import { formatClock, useClock, useSetClock } from './useClock'

/** Walkthrough jump points (docs/09 › Demo clock). */
const DEMO_JUMPS = [
  { label: 'Mon 14:50', iso: '2026-04-06T14:50:00+05:30' },
  { label: 'Mon 16:05', iso: '2026-04-06T16:05:00+05:30' },
  { label: 'Tue 04:15', iso: '2026-04-07T04:15:00+05:30' },
  { label: 'Tue 05:30', iso: '2026-04-07T05:30:00+05:30' },
  { label: 'Tue 07:45', iso: '2026-04-07T07:45:00+05:30' },
]

const NAV = [
  { to: '/dispatch/plan', label: 'Plan' },
  { to: '/dispatch/ops', label: 'Live ops' },
  { to: '/dispatch/outlook', label: 'Outlook' },
]

/** Dispatcher desktop frame: nav, depot, demo clock and user (Figma: Hi-fi · Dispatcher). */
export function DesktopShell() {
  const location = useLocation()
  const { user, signOut } = useSession()
  const clock = useClock()
  const setClock = useSetClock()

  return (
    <div className="flex h-full min-h-[900px] flex-col">
      <header className="flex h-14 shrink-0 items-center gap-8 border-b border-line bg-surface px-6">
        <div className="flex items-center gap-2">
          <span className="flex size-5 items-center justify-center">
            <span className="size-3.5 rotate-45 bg-brand" />
          </span>
          <span className="text-base font-semibold">Waypoint</span>
        </div>
        <nav className="flex h-full gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center border-b-2 px-3 text-sm font-semibold ${isActive || (item.to === '/dispatch/ops' && (location.pathname.startsWith('/dispatch/shortfalls/') || location.pathname.startsWith('/dispatch/issues/'))) ? 'border-brand text-primary' : 'border-transparent text-secondary'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <span className="ml-auto flex items-center gap-1.5 rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm leading-[18px] font-semibold">
          {user?.depot} DC
          <FigmaIcon name="chevron" />
        </span>
        <label className="relative flex items-center gap-1.5 text-sm text-secondary">
          <FigmaIcon name="clock" />
          <span className="font-mono text-[13px]">{formatClock(clock.data?.now)}</span>
          <select
            aria-label="Jump demo clock"
            className="absolute inset-0 cursor-pointer opacity-0"
            value=""
            onChange={(e) => e.target.value && void setClock(e.target.value)}
          >
            <option value="">Demo clock…</option>
            {DEMO_JUMPS.map((jump) => (
              <option key={jump.iso} value={jump.iso}>
                {jump.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={signOut}
          className="flex items-center gap-2 text-sm font-semibold text-primary"
        >
          <span className="flex size-7 items-center justify-center rounded-full bg-inverse font-semibold text-on-inverse">
            {user?.name
              .split(' ')
              .map((s) => s[0])
              .slice(0, 2)
              .join('')}
          </span>
          {user?.name} · Dispatcher
        </button>
      </header>
      <main className="flex min-h-0 flex-1 flex-col">
        <Outlet />
      </main>
    </div>
  )
}
