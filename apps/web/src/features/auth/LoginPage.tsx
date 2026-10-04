import { type FormEvent, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import { ROLE_HOME } from '../../auth/session'
import { useSession } from '../../auth/useSession'
import { Button } from '../../ui/Button'

/** Demo accounts listed for judges (Figma X1). Password: demo1234. */
const DEMO_ACCOUNTS = [
  { email: 'dispatch.peliyagoda@waypoint.demo', role: 'Dispatcher', lands: 'D1 Plan workspace' },
  { email: 'loader.dock2@waypoint.demo', role: 'Loader · Dock 2', lands: 'L1 Loading trips' },
  { email: 'driver.veh036@waypoint.demo', role: 'Driver · VEH036', lands: 'R1 Today’s trip' },
  { email: 'store.out001@waypoint.demo', role: 'Store · OUT001', lands: 'S1 Home' },
]

/** X1 · Sign in. The account decides where you land; nobody picks a "mode". */
export function LoginPage() {
  const { user, signIn } = useSession()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const signedIn = await signIn(email, password)
      navigate(ROLE_HOME[signedIn.role], { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col justify-center gap-6 px-4 py-10">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-text">Waypoint</p>
        <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">Sign in</h1>
        <p className="text-secondary">You’ll land on the screen for your role.</p>
      </div>

      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <label className="flex flex-col gap-1 text-sm font-semibold">
          Work email
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="h-12 rounded-lg border border-line bg-surface px-3 text-base font-normal"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-semibold">
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="h-12 rounded-lg border border-line bg-surface px-3 text-base font-normal"
          />
        </label>
        {error && (
          <p role="alert" className="rounded-md bg-danger-bg px-3 py-2 text-sm text-danger-fg">
            {error}
          </p>
        )}
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>
        <p className="text-sm text-secondary">
          No signal? Drivers and loaders can reopen their last session on this device and keep
          working.
        </p>
      </form>

      <section aria-labelledby="demo-accounts" className="rounded-lg border border-line bg-surface">
        <h2
          id="demo-accounts"
          className="border-b border-line px-4 py-2 text-xs font-semibold uppercase text-secondary"
        >
          Demo accounts · password demo1234
        </h2>
        <ul>
          {DEMO_ACCOUNTS.map((account) => (
            <li key={account.email}>
              <button
                type="button"
                onClick={() => {
                  setEmail(account.email)
                  setPassword('demo1234')
                }}
                className="flex w-full items-center justify-between border-b border-line px-4 py-3 text-left last:border-b-0 hover:bg-sunken"
              >
                <span className="font-semibold">{account.role}</span>
                <span className="text-sm text-secondary">{account.lands}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
