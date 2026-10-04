import { useCallback, useSyncExternalStore } from 'react'

import { api, problemMessage } from '../api/client'
import { getSession, setSession, subscribeSession } from './session'

export function useSession() {
  const session = useSyncExternalStore(subscribeSession, getSession, () => null)

  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await api.POST('/api/v1/auth/login', { body: { email, password } })
    if (error || !data) throw new Error(problemMessage(error, 'Email or password is incorrect'))
    setSession({
      accessToken: data.access_token,
      expiresAt: Date.now() + data.expires_in * 1000,
      user: data.user,
    })
    return data.user
  }, [])

  const signOut = useCallback(() => setSession(null), [])

  return { session, user: session?.user ?? null, signIn, signOut }
}
