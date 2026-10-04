import { useOnline } from './useOnline'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import { api, problemMessage } from '../../api/client'
import { Button } from '../../ui/Button'
import { hm, useItems, useReceipt, type ProblemLine } from './api'
import { StoreAction, StoreHeader, StoreIcon, StoreState } from './StoreShell'

export function ReportProblem() {
  const online = useOnline()
  const { ref } = useParams()
  const location = useLocation()
  const receipt = useReceipt(ref)
  const items = useItems(receipt.data?.outlet_code)
  const [problems, setProblems] = useState<ProblemLine[]>(
    () => (location.state as { problems?: ProblemLine[] } | null)?.problems ?? [],
  )
  const [editing, setEditing] = useState<ProblemLine | null>(null)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const request = useRef(crypto.randomUUID())
  const editor = useRef<HTMLDialogElement>(null)
  const add = useRef<HTMLDialogElement>(null)
  const navigate = useNavigate()
  const cache = useQueryClient()
  const [name, setName] = useState('')
  const preview = useQuery({
    queryKey: ['store', 'report-preview', ref, problems],
    enabled: !!ref && problems.length > 0,
    queryFn: async () => {
      const { data, error } = await api.POST('/api/v1/orders/{ref}/issues/check', {
        params: { path: { ref: ref! } },
        body: { request_id: request.current, lines: problems },
      })
      if (!data || error) throw new Error(problemMessage(error))
      return data
    },
  })
  const open = (problem: ProblemLine, name: string) => {
    setEditing(problem)
    setName(name)
    editor.current?.showModal()
  }
  function save() {
    if (!editing) return
    setProblems((p) => [
      ...p.filter((v) =>
        editing.order_line_id
          ? v.order_line_id !== editing.order_line_id
          : v.product_id !== editing.product_id,
      ),
      editing,
    ])
    request.current = crypto.randomUUID()
    editor.current?.close()
  }
  async function send() {
    if (!ref) return
    setError('')
    setSending(true)
    try {
      const { data, error } = await api.POST('/api/v1/orders/{ref}/issues', {
        params: { path: { ref } },
        body: { request_id: request.current, lines: problems },
      })
      if (!data || error) throw new Error(problemMessage(error))
      await cache.invalidateQueries({ queryKey: ['store'] })
      navigate('/store')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Report could not be sent')
    } finally {
      setSending(false)
    }
  }
  if (receipt.isPending)
    return (
      <>
        <StoreHeader title="Report a problem" subtitle={ref ?? ''} />
        <StoreState loading />
      </>
    )
  if (!receipt.data)
    return (
      <>
        <StoreHeader title="Report a problem" subtitle={ref ?? ''} />
        <StoreState error={receipt.error} retry={() => void receipt.refetch()} />
      </>
    )
  const data = receipt.data
  const named = problems
    .toSorted(
      (a, b) =>
        data.lines.findIndex((l) => l.order_line_id === a.order_line_id) -
        data.lines.findIndex((l) => l.order_line_id === b.order_line_id),
    )
    .map((p) => ({
      ...p,
      name:
        data.lines.find((l) => l.order_line_id === p.order_line_id)?.name ??
        items.data?.find((i) => i.product_id === p.product_id)?.name ??
        'Item',
    }))
  const good = preview.data?.good_cases ?? data.total_cases
  const shortName = (name: string) =>
    name === 'Set yoghurt 1 kg' ? 'yoghurt' : name === 'Fish, fillet' ? 'fish' : name
  const labels = {
    missing: 'Missing',
    damaged: 'Damaged',
    wrong_item: 'Wrong item',
    warm: 'Chilled-arrived-warm',
  }
  return (
    <>
      <StoreHeader
        title="Report a problem"
        subtitle={`${ref} · delivered ${hm(data.delivered_at)} · ${data.vehicle_code ?? data.outlet_code}`}
      />
      <main className="store-body store-report">
        <div className="store-section">
          <h2 className="store-caption">Tap the item that has a problem</h2>
        </div>
        {data.lines.map((line) => {
          const problem = problems.find((p) => p.order_line_id === line.order_line_id)
          return (
            <button
              className={`store-row store-report-row ${problem ? 'warning' : ''}`}
              key={line.order_line_id}
              onClick={() =>
                open(
                  problem ?? { order_line_id: line.order_line_id, problem: 'missing', qty: 1 },
                  line.name,
                )
              }
            >
              <div>
                <h3>{line.name}</h3>
                <p className="store-small">
                  {problem ? (
                    <>
                      <span className={`store-problem-chip ${problem.problem}`}>
                        {labels[problem.problem]} · {problem.qty}
                      </span>
                      {problem.photo_url && <span className="ml-1">1 photo</span>}
                    </>
                  ) : (
                    `${line.driver_qty ?? line.ordered_qty} cases · OK`
                  )}
                </p>
              </div>
              {problem ? <span className="edit">Edit</span> : <StoreIcon name="chevron" />}
            </button>
          )
        })}
        {problems
          .filter((p) => !p.order_line_id)
          .map((p) => (
            <button
              className="store-row store-report-row warning"
              key={p.product_id}
              onClick={() =>
                open(p, items.data?.find((i) => i.product_id === p.product_id)?.name ?? 'Item')
              }
            >
              <div>
                <h3>{items.data?.find((i) => i.product_id === p.product_id)?.name}</h3>
                <p className="store-small">Wrong item · {p.qty}</p>
              </div>
              <span className="edit">Edit</span>
            </button>
          ))}
        <button className="store-add report" onClick={() => add.current?.showModal()}>
          <StoreIcon name="reportAdd" />
          Add an item not on this delivery
        </button>
        <section className="store-report-summary">
          <span className="store-caption">Your report</span>
          <h2>
            {named.length
              ? named
                  .map((p) => `${labels[p.problem]}: ${shortName(p.name)} × ${p.qty}`)
                  .join(' · ')
              : 'No problems selected'}
          </h2>
          <p>
            The other {Math.max(0, good)} cases are confirmed.{' '}
            {data.photo_url
              ? 'The driver’s handover photo is attached.'
              : 'The driver’s record is attached.'}
          </p>
        </section>
        {(error || preview.error) && (
          <p className="store-error" role="alert">
            {error || preview.error?.message}
          </p>
        )}
        <footer className="store-footer tall">
          <StoreAction
            disabled={sending || !problems.length || !preview.data || preview.isFetching || !online}
            onClick={() => void send()}
          >
            {sending ? 'Sending…' : 'Send to dispatch'} <StoreIcon name="arrow" />
          </StoreAction>
        </footer>
      </main>
      <dialog className="store-dialog" ref={editor}>
        <h2>{name}</h2>
        {editing && (
          <>
            <label>
              Problem
              <select
                aria-label="Problem"
                value={editing.problem}
                onChange={(e) =>
                  setEditing((p) =>
                    p ? { ...p, problem: e.target.value as ProblemLine['problem'] } : p,
                  )
                }
              >
                {Object.entries(labels).map(([value, label]) => (
                  <option value={value} key={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Cases
              <input
                type="number"
                min="1"
                inputMode="numeric"
                value={editing.qty}
                onChange={(e) => setEditing((p) => (p ? { ...p, qty: Number(e.target.value) } : p))}
              />
            </label>
            <label>
              Photo link (optional)
              <input
                type="url"
                value={editing.photo_url ?? ''}
                onChange={(e) =>
                  setEditing((p) => (p ? { ...p, photo_url: e.target.value || null } : p))
                }
              />
            </label>
          </>
        )}
        <footer>
          <Button
            variant="outline"
            onClick={() => {
              setProblems((p) =>
                p.filter((v) =>
                  editing?.order_line_id
                    ? v.order_line_id !== editing.order_line_id
                    : v.product_id !== editing?.product_id,
                ),
              )
              request.current = crypto.randomUUID()
              editor.current?.close()
            }}
          >
            Remove
          </Button>
          <Button variant="secondary" onClick={save}>
            Save problem
          </Button>
        </footer>
      </dialog>
      <dialog className="store-dialog" ref={add}>
        <h2>Add an item not on this delivery</h2>
        {items.isPending ? (
          <StoreState loading />
        ) : items.error ? (
          <StoreState error={items.error} retry={() => void items.refetch()} />
        ) : (
          items.data
            ?.filter((i) => !data.lines.some((l) => l.product_id === i.product_id))
            .map((i) => (
              <button
                className="store-row w-full text-left"
                key={i.product_id}
                onClick={() => {
                  add.current?.close()
                  open({ product_id: i.product_id, problem: 'wrong_item', qty: 1 }, i.name)
                }}
              >
                {i.name}
              </button>
            ))
        )}
        <footer>
          <Button variant="outline" onClick={() => add.current?.close()}>
            Close
          </Button>
        </footer>
      </dialog>
    </>
  )
}
