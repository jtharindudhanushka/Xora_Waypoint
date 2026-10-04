import { describe, expect, it } from 'vitest'
import { getSession, setSession } from './session'

describe('Session snapshot', () => {
  it('keeps the same object until storage changes, avoiding repeated React renders', () => {
    localStorage.setItem(
      'xora.session',
      JSON.stringify({ accessToken: 'test-token', expiresAt: 999, user: { role: 'dispatcher' } }),
    )
    expect(getSession()).toBe(getSession())
    setSession(null)
    expect(getSession()).toBeNull()
  })
})
