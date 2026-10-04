import { useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../api/client'

/** Operating time (demo clock, BR-56). Times come from the API, never from Date.now(). */
export function useClock() {
  return useQuery({
    queryKey: ['clock'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/clock')
      if (error || !data) throw new Error('Clock unavailable')
      return data
    },
    refetchInterval: 30_000,
  })
}

export function useSetClock() {
  const client = useQueryClient()
  return async (demoNow: string | null) => {
    await api.PUT('/api/v1/clock', { body: { demo_now: demoNow } })
    await client.invalidateQueries()
  }
}

export function formatClock(iso: string | undefined): string {
  if (!iso) return '--:--'
  // The API sends Asia/Colombo times with their offset; display the wall-clock part as-is.
  const [day, time] = iso.split('T')
  const date = new Date(`${day}T00:00:00`)
  const weekday = date.toLocaleDateString('en-GB', { weekday: 'short' })
  return `${weekday} ${(time ?? '').slice(0, 5)}`
}
