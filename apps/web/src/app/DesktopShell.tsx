import { NavLink, Outlet } from 'react-router-dom'

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
]

/** Dispatcher desktop frame: nav, depot, demo clock and user (Figma: Hi-fi · Dispatcher). */
export function DesktopShell() {
  const { user, signOut } = useSession()
  const clock = useClock()
  const setClock = useSetClock()

  return (
    <div className="flex min-h-full flex-col">
      <header className="flex h-14 items-center gap-6 border-b border-line bg-surface px-6">
        <span className="text-base font-semibold">Waypoint</span>
        <nav className="flex gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 text-sm font-semibold ${isActive ? 'bg-sunken text-primary' : 'text-secondary hover:text-primary'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <span className="ml-auto text-sm text-secondary">{user?.depot} DC</span>
        <label className="flex items-center gap-2 text-sm">
          <span className="font-mono text-base">{formatClock(clock.data?.now)}</span>
          <select
            aria-label="Jump demo clock"
            className="rounded-md border border-line bg-surface px-2 py-1 text-xs"
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
          className="text-sm text-secondary hover:text-primary"
        >
          {user?.name} · Sign out
        </button>
      </header>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
