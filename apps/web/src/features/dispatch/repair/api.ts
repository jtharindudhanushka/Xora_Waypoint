import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, problemMessage } from '../../../api/client'
import type { components } from '../../../api/schema'

export type Shortfall = components['schemas']['ShortfallOptionsOut']

export function useShortfall(id: string) {
  return useQuery({
    queryKey: ['shortfall', id],
    refetchInterval: 5000,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/shortfalls/{shortfall_id}/options', {
        params: { path: { shortfall_id: id } },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
  })
}

export function useApplyRepair(id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (option_id: string) => {
      const { data, error } = await api.POST('/api/v1/shortfalls/{shortfall_id}/apply', {
        params: { path: { shortfall_id: id } },
        body: { option_id },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ['plan'] })
    },
  })
}
