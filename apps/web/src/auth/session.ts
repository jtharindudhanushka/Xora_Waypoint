import type { components } from '../api/schema'

type User = components['schemas']['UserOut']

export type Session = { accessToken: string; expiresAt: number; user: User }

const KEY = 'xora.session'
const listeners = new Set<() => void>()

/**
 * The session survives reloads and loss of signal, so drivers and loaders can reopen their last
 * session offline (BR-38). Queued offline events are never dropped when a token expires; they
 * are sent after the user signs in again (docs/07).
 */
export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export function setSession(session: Session | null): void {
  if (session) localStorage.setItem(KEY, JSON.stringify(session))
  else localStorage.removeItem(KEY)
  listeners.forEach((notify) => notify())
}

export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export type Role = User['role']

/** Each role lands on its own home screen (X1). */
export const ROLE_HOME: Record<Role, string> = {
  dispatcher: '/dispatch',
  loader: '/dock',
  driver: '/driver',
  store_manager: '/store',
}
