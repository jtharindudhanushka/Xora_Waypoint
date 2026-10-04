import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, problemMessage } from '../../../api/client'
import type { components } from '../../../api/schema'

export type Plan = components['schemas']['PlanOut']
export type Trip = components['schemas']['TripOut']
export type Deferral = components['schemas']['DeferralOut']
export type FleetVehicle = components['schemas']['FleetOut']

export function usePlan(date: string) {
  return useQuery({
    queryKey: ['plan', date],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/api/v1/plans/{operating_date}', {
        params: { path: { operating_date: date } },
      })
      if (response.status === 404) return null
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
  })
}

export function useFleet(date: string) {
  return useQuery({
    queryKey: ['fleet', date],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/fleet', { params: { query: { date } } })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
  })
}

export function usePlanningActions(date: string) {
  const client = useQueryClient()
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ['plan', date] })
    await client.invalidateQueries({ queryKey: ['fleet', date] })
  }
  const generate = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/api/v1/plans/{operating_date}/generate', {
        params: { path: { operating_date: date } },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
    onSuccess: refresh,
  })
  const confirm = useMutation({
    mutationFn: async ({
      id,
      items,
    }: {
      id: string
      items: components['schemas']['ConfirmItem'][]
    }) => {
      const { data, error } = await api.POST(
        '/api/v1/plan-versions/{version_id}/deferrals/confirm',
        { params: { path: { version_id: id } }, body: { items } },
      )
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
    onSuccess: refresh,
  })
  const publish = useMutation({
    mutationFn: async (id: string) => {
      const { data, error } = await api.POST('/api/v1/plan-versions/{version_id}/publish', {
        params: { path: { version_id: id } },
        body: { accept_late_risk: true },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
    onSuccess: refresh,
  })
  const switchFleet = useMutation({
    mutationFn: async ({
      vehicle,
      switched_on,
      off_reason,
    }: {
      vehicle: string
      switched_on: boolean
      off_reason?: string
    }) => {
      const { data, error } = await api.PATCH('/api/v1/fleet/{vehicle}/{operating_date}', {
        params: { path: { vehicle, operating_date: date } },
        body: { switched_on, off_reason },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
    onSuccess: refresh,
  })
  const lock = useMutation({
    mutationFn: async ({ trip, locked }: { trip: string; locked: boolean }) => {
      const path = { trip_id: trip }
      const result = locked
        ? await api.POST('/api/v1/trips/{trip_id}/lock', { params: { path } })
        : await api.DELETE('/api/v1/trips/{trip_id}/lock', { params: { path } })
      if (result.error || !result.data) throw new Error(problemMessage(result.error))
      return result.data
    },
    onSuccess: refresh,
  })
  return { generate, confirm, publish, switchFleet, lock }
}

export async function serveInstead(id: string, confirm: boolean) {
  const { data, error } = await api.POST('/api/v1/deferrals/{deferral_id}/serve-instead', {
    params: { path: { deferral_id: id } },
    body: { confirm },
  })
  if (error || !data) throw new Error(problemMessage(error))
  return data
}

export function usePublishCheck(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ['publish-check', id],
    enabled,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/plan-versions/{version_id}/publish-check', {
        params: { path: { version_id: id } },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
  })
}
