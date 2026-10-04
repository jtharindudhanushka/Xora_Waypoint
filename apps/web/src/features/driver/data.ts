import { useQuery } from '@tanstack/react-query'

import { api } from '../../api/client'
import type { components } from '../../api/schema'
import { useSession } from '../../auth/useSession'
import { cacheGet, cachePut, type OutboxEvent, syncClock } from '../field/outbox'

export type VehicleToday = components['schemas']['VehicleTodayOut']
export type TripView = components['schemas']['TripView']
export type StopView = components['schemas']['StopView']

const cacheKey = (code: string) => `vehicle-today:${code}`

/**
 * Today's published plan for the driver's vehicle. Cached on the phone so the driver can reopen
 * it without signal (BR-38, docs/07 › Bootstrap).
 */
export function useVehicleToday() {
  const session = useSession()
  const code = session?.user?.vehicle_code ?? ''
  return useQuery({
    queryKey: ['vehicle-today', code],
    enabled: Boolean(code),
    networkMode: 'always',
    refetchInterval: 30_000,
    queryFn: async (): Promise<VehicleToday> => {
      try {
        const { data, error } = await api.GET('/api/v1/vehicles/{code}/today', {
          params: { path: { code } },
        })
        if (error || !data) throw new Error('unavailable')
        syncClock(data.server_time)
        await cachePut(cacheKey(code), data)
        return data
      } catch {
        const cached = await cacheGet<VehicleToday>(cacheKey(code))
        if (cached) return cached
        throw new Error('No plan saved on this phone yet. Connect once to download today’s trip.')
      }
    },
  })
}

/** Local state = server state + what this phone has already recorded (the UI reads local first). */
export function localState(events: OutboxEvent[]) {
  const acked = new Set<string>()
  const arrived = new Map<string, OutboxEvent>()
  const outcomes = new Map<string, OutboxEvent>()
  for (const e of events) {
    if (e.status === 'rejected') continue
    if (e.type === 'trip_acknowledged' && e.plan_version_id) acked.add(e.plan_version_id)
    if (e.type === 'arrived') arrived.set(e.entity.id, e)
    if (e.type === 'outcome_recorded') outcomes.set(e.entity.id, e)
  }
  return { acked, arrived, outcomes }
}

/** The trip the driver is working on: the first with a stop not yet done. */
export function currentTrip(
  day: VehicleToday,
  outcomes: Map<string, OutboxEvent>,
): TripView | undefined {
  return (
    day.trips.find((t) => t.stops.some((s) => !s.outcome && !outcomes.has(s.id))) ??
    day.trips.at(-1)
  )
}

export const vehicleLabel = (day: VehicleToday) =>
  `${day.vehicle_temp === 'reefer' ? 'Reefer' : 'Ambient'} ${day.vehicle_type}`

export const time = (value: string | null | undefined) => (value ? value.slice(0, 5) : '--:--')

export const pad2 = (n: number) => String(n).padStart(2, '0')

export function accessLine(stop: StopView): string {
  const parts = [`Window ${time(stop.window_open)}–${time(stop.window_close)}`]
  parts.push(
    stop.dock_type === 'street'
      ? 'street'
      : stop.dock_type === 'mall_bay'
        ? 'mall bay'
        : 'rear dock',
  )
  if (stop.parking_constraint === 'van_only') parts.push('van only')
  return parts.join(' · ')
}

export function cases(stop: StopView) {
  const planned = stop.orders.reduce((sum, o) => sum + o.planned_cases, 0)
  const short = stop.orders.reduce((sum, o) => sum + (o.known_shortfall?.qty ?? 0), 0)
  return { planned, ordered: planned + short, short }
}

/** Short reference for a record on this phone, e.g. REC-0741. */
export const recordRef = (eventId: string) =>
  `REC-${(parseInt(eventId.slice(0, 4), 16) % 10000).toString().padStart(4, '0')}`
