import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { ROLE_HOME, type Role } from '../auth/session'
import { useSession } from '../auth/useSession'

/** Route guard: signed-in users of the right role only; others go to their own home (BR-55). */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user } = useSession()
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to={ROLE_HOME[user.role]} replace />
  return <>{children}</>
}

export function HomeRedirect() {
  const { user } = useSession()
  return <Navigate to={user ? ROLE_HOME[user.role] : '/login'} replace />
}
