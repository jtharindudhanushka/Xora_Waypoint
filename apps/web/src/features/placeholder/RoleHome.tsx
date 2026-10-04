import { useSession } from '../../auth/useSession'
import { StatusBadge } from '../../ui/StatusBadge'

/**
 * Temporary landing screen per role until the feature work packages (WP-2 to WP-5) replace it.
 * Lists the screens that will live here so the team can see the target at a glance.
 */
export function RoleHome({ title, screens }: { title: string; screens: string[] }) {
  const { user, signOut } = useSession()
  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <h1 className="text-[22px] leading-7 font-semibold">{title}</h1>
        <StatusBadge status="planned" label="Coming next" />
      </div>
      <p className="text-secondary">
        Signed in as <strong className="text-primary">{user?.name}</strong> ({user?.role}
        {user?.vehicle_code ? ` · ${user.vehicle_code}` : ''}
        {user?.outlet_code ? ` · ${user.outlet_code}` : ''}).
      </p>
      <ul className="divide-y divide-[var(--border-default)] rounded-lg border border-line bg-surface">
        {screens.map((screen) => (
          <li key={screen} className="px-4 py-3 font-mono text-sm">
            {screen}
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={signOut}
        className="self-start text-sm text-secondary underline"
      >
        Sign out
      </button>
    </section>
  )
}
