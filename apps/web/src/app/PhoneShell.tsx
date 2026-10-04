import { NavLink, Outlet } from 'react-router-dom'

type Tab = { to: string; label: string }

/**
 * Field frame for loader, driver and store screens: designed at 390 px first (judged at phone
 * size), stretching to the dock tablet and desktop. Bottom navigation per role (docs/08).
 */
export function PhoneShell({ tabs }: { tabs: Tab[] }) {
  return (
    <div className="mx-auto flex min-h-full max-w-[1194px] flex-col bg-canvas">
      <main className="flex-1 px-4 pb-24 pt-4 sm:px-6">
        <Outlet />
      </main>
      <nav className="fixed inset-x-0 bottom-0 border-t border-line bg-surface">
        <ul className="mx-auto flex max-w-[1194px]">
          {tabs.map((tab) => (
            <li key={tab.to} className="flex-1">
              <NavLink
                to={tab.to}
                end
                className={({ isActive }) =>
                  `flex h-16 items-center justify-center text-sm font-semibold ${isActive ? 'text-primary' : 'text-tertiary'}`
                }
              >
                {tab.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
