import { useQuery } from '@tanstack/react-query'

import { api, problemMessage } from '../../api/client'
import type { components } from '../../api/schema'

export type Home = components['schemas']['StoreHomeOut']
export type Order = components['schemas']['OrderOut']
export type Track = components['schemas']['TrackingOut']
export type Item = components['schemas']['UsualItemOut']
export type OrderInput = components['schemas']['OrderSubmitIn']
export type ProblemLine = components['schemas']['ProblemLineIn']
export type ReceiptDraft = components['schemas']['ReceiptDraftOut']
export type Language = NonNullable<components['schemas']['NotificationOut']['lang']>

export function useStoreHome() {
  return useQuery({
    queryKey: ['store', 'home'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/stores/me/orders')
      if (!data || error) throw new Error(problemMessage(error))
      return data
    },
    refetchInterval: 15_000,
  })
}
export function useItems(outlet: string | undefined) {
  return useQuery({
    queryKey: ['store', 'items', outlet],
    enabled: !!outlet,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/outlets/{code}/usual-items', {
        params: { path: { code: outlet! } },
      })
      if (!data || error) throw new Error(problemMessage(error))
      return data
    },
  })
}
export function useReceipt(ref: string | undefined) {
  return useQuery({
    queryKey: ['store', 'receipt', ref],
    enabled: !!ref,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/orders/{ref}/receipt-draft', {
        params: { path: { ref: ref! } },
      })
      if (!data || error) throw new Error(problemMessage(error))
      return data
    },
    refetchInterval: 15_000,
  })
}
export function useNotices() {
  return useQuery({
    queryKey: ['store', 'notices'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/notifications')
      if (!data || error) throw new Error(problemMessage(error))
      return data
    },
    refetchInterval: 15_000,
  })
}
export function useNotice(id: string | undefined, language?: 'en' | 'si' | 'ta') {
  return useQuery({
    queryKey: ['store', 'notice', id, language],
    enabled: !!id,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/notifications/{notice_id}', {
        params: { path: { notice_id: id! }, query: { language } },
      })
      if (!data || error) throw new Error(problemMessage(error))
      return data
    },
  })
}
export const hm = (value: string | null | undefined) =>
  value
    ? value.includes('T')
      ? new Intl.DateTimeFormat('en-GB', {
          timeZone: 'Asia/Colombo',
          hour: '2-digit',
          minute: '2-digit',
        }).format(new Date(value))
      : value.slice(0, 5)
    : '—'
export const dayLabel = (value: string) =>
  new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Colombo',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
    .format(new Date(value.includes('T') ? value : `${value}T12:00:00+05:30`))
    .replace(',', '')
export const weekday = (value: string) =>
  new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Colombo', weekday: 'long' }).format(
    new Date(value.includes('T') ? value : `${value}T12:00:00+05:30`),
  )
export const remaining = (seconds: number) =>
  `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} m left`
