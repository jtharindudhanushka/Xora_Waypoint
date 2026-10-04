import { useOnline } from './useOnline'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { api, problemMessage } from '../../api/client'
import { hm, useReceipt, type ProblemLine } from './api'
import { Stepper, StoreAction, StoreHeader, StoreIcon, StoreNav, StoreState } from './StoreShell'

export function ReceiptPage() {
  const online = useOnline()
  const { ref } = useParams()
  const receipt = useReceipt(ref)
  const [counts, setCounts] = useState<Record<string, number>>({})
  const initialized = useRef(false)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const cache = useQueryClient()
  const navigate = useNavigate()
  useEffect(() => {
    if (!receipt.data || initialized.current) return
    initialized.current = true
    setCounts(
      Object.fromEntries(
        receipt.data.lines.map((l) => [l.order_line_id, l.store_qty ?? l.ordered_qty]),
      ),
    )
  }, [receipt.data])
  if (receipt.isPending)
    return (
      <>
        <StoreHeader title="Confirm what arrived" subtitle={ref ?? ''} />
        <StoreState loading />
        <StoreNav />
      </>
    )
  if (!receipt.data)
    return (
      <>
        <StoreHeader title="Confirm what arrived" subtitle={ref ?? ''} />
        <StoreState error={receipt.error} retry={() => void receipt.refetch()} />
        <StoreNav />
      </>
    )
  const data = receipt.data
  const total = Object.values(counts).reduce((sum, qty) => sum + qty, 0)
  async function confirm() {
    if (!ref) return
    setSending(true)
    setError('')
    try {
      const { data, error } = await api.POST('/api/v1/orders/{ref}/receipt', {
        params: { path: { ref } },
        body: {
          lines: Object.entries(counts).map(([order_line_id, store_qty]) => ({
            order_line_id,
            store_qty,
          })),
        },
      })
      if (!data || error) throw new Error(problemMessage(error))
      await cache.invalidateQueries({ queryKey: ['store'] })
      navigate('/store')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Receipt could not be sent')
    } finally {
      setSending(false)
    }
  }
  function report() {
    const problems: ProblemLine[] = data.lines
      .filter((l) => (counts[l.order_line_id] ?? 0) < (l.driver_qty ?? 0))
      .map((l) => ({
        order_line_id: l.order_line_id,
        problem: 'missing',
        qty: (l.driver_qty ?? 0) - (counts[l.order_line_id] ?? 0),
      }))
    navigate(`/store/orders/${ref}/issue`, { state: { problems } })
  }
  return (
    <>
      <StoreHeader
        title="Confirm what arrived"
        subtitle={`${ref} · ${data.temp_requirement === 'chilled' ? 'chilled' : 'dry'} · ${data.outlet_code}`}
      />
      <main className="store-body store-receipt">
        <div className="store-section">
          <h2 className="store-caption">Driver’s record</h2>
          <span className="store-mono store-caption">
            {data.driver_event_id
              ? `REC-${data.driver_event_id.slice(0, 4).toUpperCase()}`
              : 'Awaiting sync'}
          </span>
        </div>
        <section className="store-row store-receipt-meta">
          <div className="store-photo">
            {data.photo_url ? (
              <img src={data.photo_url} alt="Driver’s handover" />
            ) : (
              <StoreIcon name="camera" />
            )}
          </div>
          <div>
            <h2>
              {data.total_cases} cases delivered
              {data.delivered_at ? ` at ${hm(data.delivered_at)}` : ''}
            </h2>
            <p>
              {data.vehicle_code ?? 'Driver’s counts'}
              {data.receiver ? ` · received by ${data.receiver}` : ''}
            </p>
          </div>
        </section>
        <div className="store-section">
          <h2 className="store-caption">Check each line</h2>
          <span className="store-mono store-small">Driver · You</span>
        </div>
        {data.lines.map((line) => (
          <section className="store-row store-count-row" key={line.order_line_id}>
            <h3>{line.name}</h3>
            <span>{line.driver_qty ?? '—'}</span>
            <Stepper
              compact
              label={line.name}
              value={counts[line.order_line_id] ?? line.store_qty ?? 0}
              onChange={(qty) => setCounts((c) => ({ ...c, [line.order_line_id]: qty }))}
            />
          </section>
        ))}
        {!data.lines.length && <StoreState />}
        <p className="store-count-help store-small">
          <StoreIcon name="receiptInfo" />
          {data.confirmed
            ? 'Receipt confirmed. Report any item problems below.'
            : data.can_confirm
              ? 'Change a count if it’s different.'
              : 'Driver counts have not arrived yet. You can enter your counts.'}
        </p>
        {error && (
          <p className="store-error" role="alert">
            {error}
          </p>
        )}
        <footer className="store-footer">
          <StoreAction secondary onClick={report}>
            Report a problem
          </StoreAction>
          <StoreAction
            disabled={sending || !data.lines.length || data.confirmed || !online}
            onClick={() => void confirm()}
          >
            {sending ? 'Sending…' : data.confirmed ? 'Confirmed' : `Confirm ${total} cases`}
          </StoreAction>
        </footer>
      </main>
      <StoreNav />
    </>
  )
}
