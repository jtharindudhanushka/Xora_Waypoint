import Dexie, { liveQuery, type Table } from 'dexie'
import { useEffect, useState } from 'react'

import { api } from '../../api/client'
import type { components } from '../../api/schema'
import { getSession } from '../../auth/session'

type SyncEventIn = components['schemas']['SyncEventIn']
export type SyncResult = components['schemas']['SyncResultOut']
export type OutboxStatus = 'queued' | 'sending' | SyncResult['status']

/** One field action, stored on the phone first (BR-35, docs/07 › Client side). */
export type OutboxEvent = SyncEventIn & {
  seq: number
  attempts: number
  status: OutboxStatus
  uploaded_at?: string
  result?: SyncResult
}

type CacheRow = { key: string; value: unknown }

class FieldDb extends Dexie {
  outbox!: Table<OutboxEvent, string>
  cache!: Table<CacheRow, string>

  constructor() {
    super('xora-field')
    this.version(1).stores({ outbox: 'event_id, seq, status', cache: 'key' })
  }
}

export const db = new FieldDb()

// ── device clock that follows the server (demo) clock, BR-56 ─────────────────
const OFFSET_KEY = 'xora.clockOffsetMs'

/** Remember how far the operating clock is from this phone's clock (from server_time). */
export function syncClock(serverTime: string): void {
  try {
    localStorage.setItem(OFFSET_KEY, String(new Date(serverTime).getTime() - Date.now()))
  } catch {
    /* storage unavailable: fall back to the device clock */
  }
}

function offsetMs(): number {
  try {
    return Number(localStorage.getItem(OFFSET_KEY) ?? 0) || 0
  } catch {
    return 0
  }
}

/** Operating "now" as ISO with the Colombo offset: the event time that counts (BR-37). */
export function fieldNow(): string {
  const local = new Date(Date.now() + offsetMs() + 5.5 * 3600_000)
  return `${local.toISOString().slice(0, 19)}+05:30`
}

/** HH:MM of an ISO time, shown in Colombo time. */
export function hhmm(iso: string | null | undefined): string {
  if (!iso) return '--:--'
  const local = new Date(new Date(iso).getTime() + 5.5 * 3600_000)
  return local.toISOString().slice(11, 16)
}

export function deviceId(): string {
  const key = 'xora.deviceId'
  try {
    let id = localStorage.getItem(key)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(key, id)
    }
    return id
  } catch {
    return 'device'
  }
}

// ── outbox ───────────────────────────────────────────────────────────────────
export async function enqueue(
  type: SyncEventIn['type'],
  entity: SyncEventIn['entity'],
  planVersionId: string | null,
  payload: Record<string, unknown> = {},
): Promise<OutboxEvent> {
  const last = await db.outbox.orderBy('seq').last()
  const event: OutboxEvent = {
    event_id: crypto.randomUUID(),
    type,
    entity,
    plan_version_id: planVersionId,
    event_time: fieldNow(),
    seq: (last?.seq ?? 0) + 1,
    payload,
    attempts: 0,
    status: 'queued',
  }
  await db.outbox.put(event)
  void flush()
  return event
}

let flushing = false

/** Send queued events in order, 50 at a time. Events are never dropped (BR-35, BR-38). */
export async function flush(): Promise<void> {
  if (flushing || !navigator.onLine || !getSession()) return
  flushing = true
  try {
    for (;;) {
      const batch = (await db.outbox.orderBy('seq').toArray())
        .filter((e) => e.status === 'queued' || e.status === 'sending')
        .slice(0, 50)
      if (batch.length === 0) return
      await db.outbox.bulkPut(batch.map((e) => ({ ...e, status: 'sending' as const })))
      const { data, error } = await api.POST('/api/v1/sync', {
        body: {
          device_id: deviceId(),
          events: batch.map(
            ({ event_id, type, entity, plan_version_id, event_time, seq, payload }) => ({
              event_id,
              type,
              entity,
              plan_version_id,
              event_time,
              seq,
              payload,
            }),
          ),
        },
      })
      if (error || !data) {
        // Offline, expired token or server error: keep everything queued and retry later.
        await db.outbox.bulkPut(
          batch.map((e) => ({ ...e, status: 'queued' as const, attempts: e.attempts + 1 })),
        )
        return
      }
      syncClock(data.server_time)
      const byId = new Map(data.results.map((r) => [r.event_id, r]))
      await db.outbox.bulkPut(
        batch.map((e) => {
          const result = byId.get(e.event_id)
          return result
            ? { ...e, status: result.status, result, uploaded_at: data.server_time }
            : { ...e, status: 'queued' as const }
        }),
      )
    }
  } finally {
    flushing = false
  }
}

/** Flush on `online`, on app focus and every 30 s while anything is queued (docs/07). */
export function startSyncLoop(): () => void {
  const run = () => void flush()
  window.addEventListener('online', run)
  window.addEventListener('focus', run)
  const timer = window.setInterval(run, 30_000)
  run()
  return () => {
    window.removeEventListener('online', run)
    window.removeEventListener('focus', run)
    window.clearInterval(timer)
  }
}

export function useOutbox(): OutboxEvent[] {
  const [events, setEvents] = useState<OutboxEvent[]>([])
  useEffect(() => {
    const sub = liveQuery(() => db.outbox.orderBy('seq').toArray()).subscribe({
      next: setEvents,
      error: () => setEvents([]),
    })
    return () => sub.unsubscribe()
  }, [])
  return events
}

export function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine)
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])
  return online
}

export async function cachePut(key: string, value: unknown): Promise<void> {
  await db.cache.put({ key, value })
}

export async function cacheGet<T>(key: string): Promise<T | undefined> {
  return (await db.cache.get(key))?.value as T | undefined
}

export const isPending = (e: OutboxEvent) => e.status === 'queued' || e.status === 'sending'
