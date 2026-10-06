import { useQuery } from '@tanstack/react-query'
import { api, problemMessage } from '../../api/client'
import type { components } from '../../api/schema'
import { useSession } from '../../auth/useSession'
import { cacheGet, cachePut, syncClock } from '../field/outbox'
export type DockDetail = components['schemas']['DockDetail']
export type DockDay = components['schemas']['DockDay']
export const time = (t: string | null | undefined) => t?.slice(0, 5) ?? '--:--'
/** A server answer (e.g. 404) is not "no signal": say what the server said, stop polling. */
class ServerError extends Error {}

export const reasons: Record<string, string> = {
  short_from_chiller_pick: 'Short from chiller pick',
  not_on_dock: 'Not on the dock',
  damaged_in_pick: 'Damaged in pick',
  other: 'Other',
}
export function useDockDay() {
  const session = useSession()
  const key = `dock-day:${session?.user?.id}`
  return useQuery({
    queryKey: ['dock-day', session?.user?.id],
    networkMode: 'always',
    refetchInterval: (q) => (q.state.error instanceof ServerError ? false : 5000),
    queryFn: async (): Promise<DockDay> => {
      try {
        const { data, error } = await api.GET('/api/v1/dock/trips')
        if (error) throw new ServerError(problemMessage(error, 'Not available'))
        if (!data) throw new Error('unavailable')
        syncClock(data.server_time)
        await cachePut(key, data)
        return data
      } catch (e) {
        const saved = await cacheGet<DockDay>(key)
        if (saved) return saved
        if (e instanceof ServerError) throw e
        throw new Error('No trips saved on this phone yet. Connect to download today’s loads.')
      }
    },
  })
}
export function useDockTrip(id: string) {
  const session = useSession()
  const key = `dock-trip:${session?.user?.id}:${id}`
  return useQuery({
    queryKey: ['dock-trip', session?.user?.id, id],
    networkMode: 'always',
    refetchInterval: (q) => (q.state.error instanceof ServerError ? false : 5000),
    queryFn: async (): Promise<DockDetail> => {
      try {
        const { data, error } = await api.GET('/api/v1/dock/trips/{identifier}', {
          params: { path: { identifier: id } },
        })
        if (error) throw new ServerError(problemMessage(error, 'Not available'))
        if (!data) throw new Error('unavailable')
        syncClock(data.server_time)
        await cachePut(key, data)
        return data
      } catch (e) {
        const saved = await cacheGet<DockDetail>(key)
        if (saved) return saved
        if (e instanceof ServerError) throw e
        throw new Error('No load saved on this phone yet. Connect to download this trip.')
      }
    },
  })
}
