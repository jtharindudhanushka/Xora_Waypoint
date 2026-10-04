import { useOnline } from './useOnline'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { api, problemMessage } from '../../api/client'
import { StatusBadge } from '../../ui/StatusBadge'
import { dayLabel, hm, useNotice, useStoreHome, weekday } from './api'
import { StoreAction, StoreHeader, StoreIcon, StoreState } from './StoreShell'

export function DeliveryNotice() {
  const online = useOnline()
  const { id } = useParams()
  const [language, setLanguage] = useState<'en' | 'si' | 'ta' | undefined>()
  const notice = useNotice(id, language)
  const home = useStoreHome()
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const cache = useQueryClient()
  const navigate = useNavigate()
  if (notice.isPending || home.isPending)
    return (
      <>
        <StoreHeader title="Delivery update" subtitle="Waypoint" />
        <StoreState loading />
      </>
    )
  if (!notice.data || !home.data)
    return (
      <>
        <StoreHeader title="Delivery update" subtitle="Waypoint" />
        <StoreState
          error={notice.error ?? home.error}
          retry={() => {
            void notice.refetch()
            void home.refetch()
          }}
        />
      </>
    )
  const n = notice.data
  const store = home.data
  const moved = store.orders.find((o) => o.ref === n.order_ref)
  const dry = store.orders.find(
    (o) => o.temp_requirement === 'ambient' && o.delivery_date === moved?.delivery_date,
  )
  const next = n.next_run && n.next_run !== 'None' ? n.next_run : null
  async function acknowledge() {
    if (!id) return
    setSending(true)
    setError('')
    try {
      const { data, error } = await api.POST('/api/v1/notifications/{notice_id}/read', {
        params: { path: { notice_id: id } },
      })
      if (!data || error) throw new Error(problemMessage(error))
      await cache.invalidateQueries({ queryKey: ['store'] })
      navigate('/store')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Notice could not be acknowledged')
    } finally {
      setSending(false)
    }
  }
  return (
    <>
      <StoreHeader
        title={n.title}
        subtitle={`${store.outlet_code} · ${store.district} · Waypoint ${store.brand}`}
      />
      <main className="store-body store-notice">
        <section className="store-notice-lead">
          <div className="store-delivery-head">
            <span className="store-caption">
              Changed · {dayLabel(moved?.delivery_date ?? n.created_at)}
            </span>
            <span className="store-status deferred">
              <StatusBadge status="deferred" />
            </span>
          </div>
          <h2>
            {n.lang === 'en'
              ? `Your ${moved?.temp_requirement === 'ambient' ? 'dry' : 'chilled'} order moves${next ? ` to ${weekday(next)}` : ''}`
              : n.title}
          </h2>
          <p>
            {n.lang === 'en'
              ? `New time: ${next ? `${dayLabel(next)}, ${hm(store.window_open)}–${hm(store.window_close)}` : 'to be confirmed'}.${dry ? ` Your dry order still comes ${weekday(dry.delivery_date)}.` : ''}`
              : next
                ? `${dayLabel(next)} · ${hm(store.window_open)}–${hm(store.window_close)}`
                : ''}
          </p>
        </section>
        <div className="store-section">
          <h2 className="store-caption">Why</h2>
        </div>
        <section className="store-row store-notice-reason">
          <p lang={n.lang}>{n.body}</p>
          <span className="store-mono">
            {n.source} · reason {n.reason_code}
          </span>
        </section>
        <div className="store-section">
          <h2 className="store-caption">What changes</h2>
        </div>
        <section className="store-row store-change">
          <span>
            {moved?.temp_requirement === 'ambient' ? 'Dry' : 'Chilled'} · {n.order_ref}
          </span>
          <strong className="text-danger-fg">
            {next
              ? `${dayLabel(next)} · ${hm(store.window_open)}–${hm(store.window_close)}`
              : 'To be confirmed'}
          </strong>
        </section>
        {dry && (
          <section className="store-row store-change">
            <span>Dry · {dry.ref}</span>
            <strong className="text-success-fg">{dayLabel(dry.delivery_date)} · as planned</strong>
          </section>
        )}
        <section className="store-row store-change">
          <span>Priority{next ? ` on ${weekday(next)}` : ''}</span>
          <strong lang={n.lang}>{n.protection}</strong>
        </section>
        <p className="store-language store-small">
          <StoreIcon name="globe" />
          Read in <button onClick={() => setLanguage('si')}>සිංහල</button> ·{' '}
          <button onClick={() => setLanguage('ta')}>தமிழ்</button>
          {n.lang !== 'en' && <button onClick={() => setLanguage('en')}>English</button>}
          <span className="text-[11px]"> · language set in Account</span>
        </p>
        {error && (
          <p className="store-error" role="alert">
            {error}
          </p>
        )}
        <footer className="store-footer">
          <StoreAction
            secondary
            onClick={() => {
              const phone = import.meta.env.VITE_DISPATCH_PHONE as string | undefined
              if (phone) window.location.href = `tel:${phone}`
              else setError('Dispatch phone number has not been configured')
            }}
          >
            Call dispatch
          </StoreAction>
          <StoreAction disabled={sending || !online} onClick={() => void acknowledge()}>
            {sending ? 'Sending…' : 'Got it'}
          </StoreAction>
        </footer>
      </main>
    </>
  )
}
