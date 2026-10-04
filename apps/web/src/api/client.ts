import createClient, { type Middleware } from 'openapi-fetch'

import { getSession } from '../auth/session'
import type { components, paths } from './schema'

/** RFC 7807 problem body returned by the API for every error (docs/05). */
export type Problem = {
  type: string
  title: string
  status: number
  detail: string
  code?: string
  rule_id?: string
}

export type User = components['schemas']['UserOut']

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = getSession()?.accessToken
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
}

/** Typed API client. Types are generated from the API's OpenAPI schema (`npm run gen:api`). */
export const api = createClient<paths>({ baseUrl: '' })
api.use(authMiddleware)

/** Turn an openapi-fetch error body into a readable message. */
export function problemMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    return String((error as Problem).detail)
  }
  return fallback
}
