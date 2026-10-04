import { useOnline } from './useOnline'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, problemMessage } from '../../api/client'
import { Button } from '../../ui/Button'
import { dayLabel, hm, remaining, useItems, useStoreHome, type OrderInput } from './api'
import { Stepper, StoreAction, StoreHeader, StoreIcon, StoreState } from './StoreShell'

export function NewOrder() {
  const online = useOnline()
  const home = useStoreHome()
  const items = useItems(home.data?.outlet_code)
  const [chilled, setChilled] = useState(true)
  const [quantities, setQuantities] = useState<Record<string, number>>({})
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const [keep, setKeep] = useState(false)
  const review = useRef<HTMLDialogElement>(null)
  const add = useRef<HTMLDialogElement>(null)
  const requestId = useRef<string>(crypto.randomUUID())
  const initialized = useRef('')
  const navigate = useNavigate()
  const cache = useQueryClient()
  const draft = home.data?.orders.find(
    (o) => o.submission_status === 'draft' && (o.temp_requirement === 'chilled') === chilled,
  )
  useEffect(() => {
    if (!items.data) return
    const key = `${home.data?.outlet_code}-${chilled}`
    if (initialized.current === key) return
    initialized.current = key
    setQuantities(
      draft
        ? Object.fromEntries(draft.lines.map((l) => [l.product_id, l.qty_ordered]))
        : Object.fromEntries(
            items.data
              .filter((i) => i.is_chilled === chilled && i.usual_qty != null)
              .map((i) => [i.product_id, i.usual_qty!]),
          ),
    )
    setKeep(false)
  }, [items.data, home.data?.outlet_code, chilled, draft])
  const lines = Object.entries(quantities)
    .filter(([, qty]) => qty > 0)
    .map(([product_id, qty]) => ({ product_id, qty }))
  const checked = useQuery({
    queryKey: ['store', 'order-check', lines],
    enabled: lines.length > 0,
    queryFn: async () => {
      const { data, error } = await api.POST('/api/v1/orders/check', { body: { lines } })
      if (error || !data) throw new Error(problemMessage(error))
      return data
    },
  })
  const warnings = checked.data?.warnings ?? []
  const total = lines.reduce((sum, l) => sum + l.qty, 0)
  const change = (id: string, qty: number) => {
    setQuantities((q) => ({ ...q, [id]: qty }))
    setKeep(false)
    requestId.current = crypto.randomUUID()
  }
  async function submit() {
    if (!checked.data) return
    setSending(true)
    setError('')
    const body: OrderInput = {
      request_id: requestId.current,
      draft_ref: draft?.ref,
      lines,
      confirm_unusual: keep,
    }
    try {
      const { data, error } = await api.POST('/api/v1/orders', { body })
      if (!data || error) throw new Error(problemMessage(error))
      await cache.invalidateQueries({ queryKey: ['store'] })
      navigate('/store')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Order could not be sent')
    } finally {
      setSending(false)
    }
  }
  if (home.isPending || (home.data && items.isPending))
    return (
      <>
        <StoreHeader title="New order" subtitle="Waypoint" />
        <StoreState loading />
      </>
    )
  if (!home.data || !items.data)
    return (
      <>
        <StoreHeader title="New order" subtitle="Waypoint" />
        <StoreState
          error={home.error ?? items.error}
          retry={() => {
            void home.refetch()
            void items.refetch()
          }}
        />
      </>
    )
  const data = home.data
  const ordering = checked.data ?? data.ordering
  const orderedItems = draft
    ? [
        ...draft.lines
          .map((l) => items.data!.find((i) => i.product_id === l.product_id)!)
          .filter(Boolean),
        ...items.data.filter((i) => !draft.lines.some((l) => l.product_id === i.product_id)),
      ]
    : items.data
  return (
    <>
      <StoreHeader
        title="New order"
        subtitle={`${data.outlet_code} · ${data.district} · ${data.brand}`}
      />
      <main className="store-body">
        <section className="store-row store-date">
          <StoreIcon name="calendar" />
          <div>
            <span className="store-caption">Delivery</span>
            <strong>
              {dayLabel(ordering.delivery_date)} · {hm(data.window_open)}–{hm(data.window_close)}
            </strong>
          </div>
        </section>
        <section className="store-cutoff new-order">
          <StoreIcon name="clock" />
          <strong>
            {ordering.after_cutoff
              ? `Orders closed · next delivery ${dayLabel(ordering.delivery_date)}`
              : `Orders close at 16:00 · ${remaining(ordering.cutoff_seconds)}`}
          </strong>
        </section>
        <div className="store-section">
          <h2 className="store-caption">Order type</h2>
        </div>
        <div className="store-type">
          <button className={chilled ? 'active' : ''} onClick={() => setChilled(true)}>
            {chilled && <StoreIcon name="snowflake" />}Chilled
          </button>
          <button className={!chilled ? 'active' : ''} onClick={() => setChilled(false)}>
            Dry
          </button>
        </div>
        <div className="store-section">
          <h2 className="store-caption">Your usual items</h2>
          <span className="store-mono store-small">Cases</span>
        </div>
        <div className="store-items">
          {orderedItems
            .filter((i) => i.is_chilled === chilled && (quantities[i.product_id] ?? 0) > 0)
            .map((item) => {
              const warning = warnings.find((w) => w.product_id === item.product_id)
              return (
                <section
                  className={`store-item-row ${warning ? 'warning' : ''}`}
                  key={item.product_id}
                >
                  <div className="store-item-main">
                    <div>
                      <h3>{item.name}</h3>
                      <p>{item.usual_qty == null ? 'Added item' : `Usual ${item.usual_qty}`}</p>
                    </div>
                    <button
                      className="store-trash"
                      aria-label={`Remove ${item.name}`}
                      onClick={() => change(item.product_id, 0)}
                    >
                      <StoreIcon name="trash" />
                    </button>
                    <Stepper
                      value={quantities[item.product_id] ?? 0}
                      onChange={(qty) => change(item.product_id, qty)}
                      label={item.name}
                    />
                  </div>
                  {warning && (
                    <div className="store-warning">
                      <p>{warning.message}</p>
                      <button onClick={() => change(item.product_id, warning.usual_qty)}>
                        Use {warning.usual_qty}
                      </button>
                    </div>
                  )}
                </section>
              )
            })}
          {!lines.length && (
            <p className="store-row">No items in this order. Add an item to continue.</p>
          )}
        </div>
        <button className="store-add" onClick={() => add.current?.showModal()}>
          <StoreIcon name="add" />
          Add item
        </button>
        {(error || checked.error) && (
          <p className="store-error" role="alert">
            {error || checked.error?.message}
          </p>
        )}
        <section className="store-order-total">
          <strong>{total} cases</strong>
          <p className="store-small">
            {warnings.length
              ? `${items.data.find((i) => i.product_id === warnings[0]!.product_id)?.name === 'Set yoghurt 1 kg' ? 'Yoghurt' : 'Quantity'} looks high · ${total - warnings[0]!.qty + warnings[0]!.usual_qty} if you use ${warnings[0]!.usual_qty}`
              : `${chilled ? 'Chilled' : 'Dry'} · ${lines.length} items`}
          </p>
        </section>
        <footer className="store-footer order">
          <StoreAction
            disabled={!lines.length || !checked.data || checked.isFetching}
            onClick={() => review.current?.showModal()}
          >
            Review order <StoreIcon name="arrow" />
          </StoreAction>
        </footer>
      </main>
      <dialog ref={review} className="store-dialog">
        <h2>Review order</h2>
        <p>
          {total} cases · {dayLabel(ordering.delivery_date)}
        </p>
        {lines.map((l) => (
          <p key={l.product_id} className="mt-2">
            {items.data.find((i) => i.product_id === l.product_id)?.name} · {l.qty}
          </p>
        ))}
        {warnings.length > 0 && (
          <label>
            <input type="checkbox" checked={keep} onChange={(e) => setKeep(e.target.checked)} />{' '}
            Keep this quantity
          </label>
        )}
        {error && (
          <p role="alert" className="store-error">
            {error}
          </p>
        )}
        <footer>
          <Button variant="outline" onClick={() => review.current?.close()}>
            Back
          </Button>
          <Button
            variant="secondary"
            disabled={sending || (warnings.length > 0 && !keep) || !online}
            onClick={() => void submit()}
          >
            {sending ? 'Sending…' : 'Submit order'}
          </Button>
        </footer>
      </dialog>
      <dialog ref={add} className="store-dialog">
        <h2>Add item</h2>
        {items.data
          .filter((i) => i.is_chilled === chilled && !((quantities[i.product_id] ?? 0) > 0))
          .map((i) => (
            <button
              className="store-row w-full text-left"
              key={i.product_id}
              onClick={() => {
                change(i.product_id, i.usual_qty ?? 1)
                add.current?.close()
              }}
            >
              {i.name}
            </button>
          ))}
        <footer>
          <Button variant="outline" onClick={() => add.current?.close()}>
            Close
          </Button>
        </footer>
      </dialog>
    </>
  )
}
