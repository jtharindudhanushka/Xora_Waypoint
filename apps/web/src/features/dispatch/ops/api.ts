import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, problemMessage } from '../../../api/client'
import type { components } from '../../../api/schema'

export type LiveOps = components['schemas']['OpsOut']

export function useOps(date: string) {
  return useQuery({
    queryKey: ['ops', date],
    refetchInterval: 5000,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/ops/{operating_date}', {
        params: { path: { operating_date: date } },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
  })
}

export function useFix() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data, error } = await api.POST('/api/v1/exceptions/{identifier}/apply-fix', {
        params: { path: { identifier: id } },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ['ops'] })
      await client.invalidateQueries({ queryKey: ['plan'] })
    },
  })
}
