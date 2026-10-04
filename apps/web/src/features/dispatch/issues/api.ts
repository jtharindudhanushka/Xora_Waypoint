import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, problemMessage } from '../../../api/client'
import type { components } from '../../../api/schema'

export type Issue = components['schemas']['IssueOut']
export type Decision = components['schemas']['ResolveIn']

export function useIssue(id: string) {
  return useQuery({
    queryKey: ['issue', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/issues/{identifier}', {
        params: { path: { identifier: id } },
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
  })
}

export function useResolve(id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (body: Decision) => {
      const { data, error } = await api.POST('/api/v1/issues/{identifier}/resolve', {
        params: { path: { identifier: id } },
        body,
      })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
    onSuccess: async (data) => {
      client.setQueryData(['issue', id], data)
      await client.invalidateQueries({ queryKey: ['ops'] })
    },
  })
}
