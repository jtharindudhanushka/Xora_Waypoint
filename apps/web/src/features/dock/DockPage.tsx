import { useEffect, useState } from 'react'
import { Link, Outlet, useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { StatusBadge } from '../../ui/StatusBadge'
import {
  enqueue,
  hhmm,
  isPending,
  startSyncLoop,
  useOutbox,
  type OutboxEvent,
} from '../field/outbox'
import { Caption, FieldButton, FieldHeader, Icon, KeyValue, SyncBar } from '../field/ui'
import { reasons, time, useDockDay, useDockTrip, type DockDetail } from './data'

/** L1–L5: phone 390, with the exact field components and local outbox (BR-35). */
export function DockShell() {
  useEffect(() => startSyncLoop(), [])
  return (
    <div className="mx-auto flex min-h-[844px] w-full max-w-[390px] flex-col bg-canvas">
      <Outlet />
    </div>
  )
}
function PhoneStatus({ serverTime }: { serverTime?: string }) {
  return (
    <div className="flex h-11 shrink-0 items-center gap-1.5 bg-surface px-6 text-sm font-semibold">
      <span>{hhmm(serverTime)}</span>
      <span className="flex-1" />
      <span className="flex items-end gap-0.5" aria-hidden="true">
        {[4, 6, 8, 10].map((h) => (
          <span key={h} className="w-[3px] bg-primary" style={{ height: h }} />
        ))}
      </span>
      <span aria-hidden="true" className="h-[10px] w-[22px] rounded-[2px] bg-primary" />
    </div>
  )
}
function Message({ text, retry }: { text: string; retry?: () => void }) {
  return (
    <div role="status" className="flex flex-1 flex-col gap-4 p-4">
      <p>{text}</p>
      {retry && (
        <FieldButton kind="secondary" onClick={retry}>
          Try again
        </FieldButton>
      )}
    </div>
  )
}
export function DockPage() {
  const query = useDockDay(),
    events = useOutbox(),
    navigate = useNavigate()
  const [selection, setSelection] = useState('')
  if (query.isPending) return <Message text="Loading today’s trips…" />
  if (!query.data)
    return (
      <Message
        text={query.error?.message ?? 'Trips unavailable'}
        retry={() => void query.refetch()}
      />
    )
  const day = query.data
  const selected =
    day.trips.find((t) => t.id === selection) ??
    day.trips.find((t) => t.load_status !== 'loaded') ??
    day.trips[0]
  const date = new Date(`${day.date}T00:00:00`).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
  return (
    <>
      <PhoneStatus serverTime={day.server_time} />
      <FieldHeader
        signOut
        title={`Loading · ${date}`}
        subtitle={`${day.depot} DC · ${day.dock ?? 'Dock'} · Plan v${day.version?.number ?? '—'}`}
      />
      <SyncBar
        events={events}
        onlineTitle={`Online · plan v${day.version?.number ?? '—'} received ${hhmm(day.version?.published_at)}`}
      />
      <Caption meta="Departs">Trips at this dock</Caption>
      {day.trips.length === 0 && <Message text="No published loading trips at this dock today." />}
      {day.trips.map((t) => (
        <button
          key={t.id}
          onClick={() => setSelection(t.id)}
          className={`flex w-full items-center gap-3 border-b border-line py-[14px] pr-4 text-left ${selected?.id === t.id ? 'bg-brand-subtle' : 'bg-surface'}`}
        >
          <span
            className={`flex w-16 shrink-0 self-stretch items-center justify-center font-mono text-[13px] leading-[18px] ${selected?.id === t.id ? 'border-l-4 border-brand' : ''}`}
          >
            {time(t.departure)}
          </span>
          <span className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span className="text-base font-semibold leading-5">
              {t.vehicle} · Trip {t.trip_no}
            </span>
            <span className="text-xs leading-4 text-secondary">
              {t.district} · {t.stops} {t.stops === 1 ? 'stop' : 'stops'} · {t.volume_m3.toFixed(1)}{' '}
              m³ {t.temperature === 'reefer' ? 'chilled' : 'dry'}
            </span>
          </span>
          <StatusBadge
            status={
              t.on_hold
                ? 'on_hold'
                : events.some(
                      (e) =>
                        e.type === 'trip_loaded' && e.entity.id === t.id && e.status !== 'rejected',
                    )
                  ? 'loaded'
                  : t.load_status
            }
            variant="figma"
          />
        </button>
      ))}
      <div className="flex-1" />
      {selected && (
        <div className="px-4 pb-7 pt-3">
          <FieldButton className="w-full" onClick={() => navigate(`/dock/trips/${selected.id}`)}>
            Load {selected.vehicle} · Trip {selected.trip_no}
          </FieldButton>
        </div>
      )}
    </>
  )
}
function Meter({
  label,
  value,
  cap,
  unit,
}: {
  label: string
  value: number
  cap: number
  unit: string
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-1.5">
      <div className="flex gap-1.5 text-secondary">
        <span className="flex-1 text-xs font-semibold leading-4">{label}</span>
        <span className="font-mono text-[11px] leading-[14px]">
          {value.toLocaleString('en-GB', { maximumFractionDigits: 1 })} /{' '}
          {cap.toLocaleString('en-GB', { maximumFractionDigits: 1 })} {unit}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-[1px] bg-sunken">
        <div
          className="h-full bg-line-strong"
          style={{ width: `${Math.min(100, cap ? (value / cap) * 100 : 0)}%` }}
        />
      </div>
      <p className="text-xs leading-4 text-tertiary">Fits</p>
    </div>
  )
}
export function DockTripPage() {
  const { id = '' } = useParams(),
    query = useDockTrip(id),
    events = useOutbox(),
    client = useQueryClient()
  const [report, setReport] = useState(false)
  useEffect(() => {
    void client.invalidateQueries({ queryKey: ['dock-trip'] })
    void client.invalidateQueries({ queryKey: ['dock-day'] })
  }, [events, client])
  if (query.isPending) return <Message text="Loading trip…" />
  if (!query.data)
    return (
      <Message
        text={query.error?.message ?? 'Load unavailable'}
        retry={() => void query.refetch()}
      />
    )
  const trip = query.data,
    mine = events.filter(
      (e) => e.entity.id === trip.id && e.status !== 'rejected' && e.status !== 'conflict',
    )
  const pendingReport = [...mine]
    .reverse()
    .find((e) => e.type === 'shortfall_reported' && isPending(e))
  const pendingAck = mine.some(
    (e) => e.type === 'trip_acknowledged' && e.plan_version_id === trip.version.id && isPending(e),
  )
  const loaded = trip.load_status === 'loaded' || mine.some((e) => e.type === 'trip_loaded')
  if (report) return <ShortfallSheet trip={trip} events={events} close={() => setReport(false)} />
  if (trip.version.needs_acknowledgement)
    return <Revision trip={trip} events={events} pendingAck={pendingAck} />
  if (trip.hold || pendingReport)
    return <HoldScreen trip={trip} events={events} pendingReport={pendingReport} />
  const checked = new Map<string, boolean>()
  for (const e of mine)
    if (e.type === 'load_checked')
      checked.set(String(e.payload?.order_id), Boolean(e.payload?.checked))
  const count = trip.load_list.filter((l) => checked.get(l.order_id)).length
  return (
    <>
      <PhoneStatus serverTime={trip.server_time} />
      <FieldHeader
        back="/dock"
        title={`${trip.vehicle} · Trip ${trip.trip_no} · ${trip.district}`}
        subtitle={`${trip.temperature === 'reefer' ? 'Reefer van' : 'Dry vehicle'} · departs ${time(trip.departure)} · Plan v${trip.version.number}`}
      />
      <SyncBar events={events} onlineDetail="Ticks save as you go" />
      <div className="flex gap-6 border-b border-line bg-surface px-4 py-[14px]">
        <Meter label="Volume" value={trip.volume_m3} cap={trip.volume_cap_m3} unit="m³" />
        <Meter label="Weight" value={trip.weight_kg} cap={trip.weight_cap_kg} unit="kg" />
      </div>
      <div className="flex items-start gap-[10px] bg-info-bg px-4 py-3 text-sm leading-5 text-info-fg">
        <img src="/figma/dock/70862.svg" alt="" />
        <p>Last drop goes in first · {trip.load_list[0]?.outlet_code} by the doors</p>
      </div>
      <Caption meta={`${count} of ${trip.load_list.length} loaded`}>Load order</Caption>
      {trip.load_list.map((l, i) => (
        <label
          key={l.order_id}
          className={`flex cursor-pointer items-center gap-[14px] border-b border-line px-4 py-[14px] ${i === 0 ? 'bg-brand-subtle' : 'bg-surface'}`}
        >
          <input
            aria-label={`Loaded ${l.order_ref}`}
            type="checkbox"
            className="size-9 shrink-0 appearance-none rounded-md border-2 border-primary checked:border-brand checked:bg-brand"
            checked={loaded || Boolean(checked.get(l.order_id))}
            disabled={loaded}
            onChange={(e) =>
              void enqueue('load_checked', { type: 'trip', id: trip.id }, trip.version.id, {
                order_id: l.order_id,
                checked: e.target.checked,
              })
            }
          />
          <span className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span
              className={`text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] ${i === 0 ? 'text-brand-text' : 'text-secondary'}`}
            >
              {i === 0 ? '1st' : i === 1 ? '2nd' : `${i + 1}th`} in
            </span>
            <span className="text-base font-semibold leading-5">
              {l.outlet_code} · stop {l.stop_seq}
            </span>
            <span className="text-xs leading-4 text-secondary">
              {l.order_ref} · {l.temperature} · {l.weight_kg} kg
            </span>
          </span>
          <span className="flex flex-col items-end">
            <span className="font-mono text-xl leading-6 tracking-[-0.4px]">{l.cases}</span>
            <span className="text-xs leading-4 text-secondary">cases</span>
          </span>
        </label>
      ))}
      <div className="flex-1" />
      <div className="flex gap-2 px-4 pb-7 pt-3">
        <FieldButton
          kind="secondary"
          arrow={false}
          disabled={loaded}
          onClick={() => setReport(true)}
        >
          Report a problem
        </FieldButton>
        <FieldButton
          className="flex-1 px-3"
          disabled={loaded || count !== trip.load_list.length || !trip.load_list.length}
          onClick={() =>
            void enqueue('trip_loaded', { type: 'trip', id: trip.id }, trip.version.id)
          }
        >
          {loaded ? 'Loaded' : 'Mark loaded'}
        </FieldButton>
      </div>
    </>
  )
}
function ShortfallSheet({
  trip,
  events,
  close,
}: {
  trip: DockDetail
  events: OutboxEvent[]
  close: () => void
}) {
  const [orderId, setOrderId] = useState(trip.load_list[0]?.order_id ?? ''),
    [kind, setKind] = useState('missing'),
    [qty, setQty] = useState('2'),
    [reason, setReason] = useState(trip.shortfall_reasons[0] ?? ''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('')
  const line = trip.load_list.find((l) => l.order_id === orderId)
  const send = async () => {
    setBusy(true)
    try {
      await enqueue('shortfall_reported', { type: 'trip', id: trip.id }, trip.version.id, {
        order_id: orderId,
        kind,
        qty: Number(qty),
        reason,
      })
      close()
    } catch {
      setError('Could not save the report. Try again.')
      setBusy(false)
    }
  }
  return (
    <section
      role="dialog"
      aria-modal="true"
      aria-label="Report a problem"
      className="flex min-h-[844px] flex-1 flex-col"
    >
      <PhoneStatus serverTime={trip.server_time} />
      <div className="flex border-b border-line bg-surface px-4 pb-[10px] pt-2">
        <button aria-label="Back to load" className="flex h-11 w-10 items-center" onClick={close}>
          <Icon name="chevronLeft" />
        </button>
        <div className="flex flex-col justify-center font-semibold">
          <p className="text-base leading-5">Report a problem</p>
          <p className="text-sm leading-[18px] text-secondary">
            {trip.vehicle} · Trip {trip.trip_no} · departs {time(trip.departure)}
          </p>
        </div>
      </div>
      <SyncBar events={events} onlineDetail="If signal drops, the report queues and sends itself" />
      <Caption pad="pb-2 pt-[18px]">Which order</Caption>
      {trip.load_list.map((l) => (
        <label
          key={l.order_id}
          className={`flex items-center gap-3 border-b border-line px-4 py-3 ${orderId === l.order_id ? 'bg-brand-subtle' : 'bg-surface'}`}
        >
          <input
            type="radio"
            name="order"
            checked={orderId === l.order_id}
            onChange={() => setOrderId(l.order_id)}
            className="size-[22px] accent-brand"
          />
          <span className="flex-1 text-base font-semibold leading-5">
            {l.outlet_code} · {l.order_ref}
          </span>
          <span className="text-xs leading-4 text-secondary">
            {l.temperature === 'chilled' ? 'Chilled' : 'Dry'} · {l.cases} cases
          </span>
        </label>
      ))}
      <Caption pad="pb-2 pt-[18px]">What’s wrong</Caption>
      <div className="px-4">
        <div className="flex overflow-hidden rounded-md border border-line-strong">
          {['missing', 'damaged'].map((k) => (
            <button
              key={k}
              className={`h-12 flex-1 text-base font-semibold ${kind === k ? 'bg-inverse text-on-inverse' : 'bg-surface'}`}
              onClick={() => setKind(k)}
              aria-pressed={kind === k}
            >
              {k === 'missing' ? 'Missing' : 'Damaged'}
            </button>
          ))}
        </div>
        <label className="mt-4 flex flex-col gap-1.5 text-sm font-semibold">
          Cases short
          <input
            type="number"
            inputMode="numeric"
            min="1"
            max={line?.cases}
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="h-12 rounded-md border-2 border-brand bg-surface px-3 text-base font-normal"
          />
        </label>
        <p className="mt-1.5 text-xs leading-4 text-secondary">
          Of {line?.cases} cases on {line?.order_ref} ·{' '}
          {Math.max(0, (line?.cases ?? 0) - Number(qty))} will be loaded
        </p>
      </div>
      <Caption pad="pb-2 pt-[18px]">Reason</Caption>
      <div className="flex flex-wrap gap-2 px-4">
        {trip.shortfall_reasons.map((r) => (
          <button
            key={r}
            onClick={() => setReason(r)}
            aria-pressed={reason === r}
            className={`h-10 rounded-md border px-[14px] text-sm font-semibold ${reason === r ? 'border-inverse bg-inverse text-on-inverse' : 'border-line-strong bg-surface'}`}
          >
            {reasons[r] ?? r}
          </button>
        ))}
      </div>
      <div className="px-2 py-3">
        <FieldButton
          kind="ghost"
          arrow={false}
          onClick={() => setError('Photo upload is not available yet. Send without a photo.')}
        >
          + Add photo (optional)
        </FieldButton>
      </div>
      {error && (
        <p role="alert" className="px-4 text-sm text-danger-fg">
          {error}
        </p>
      )}
      <div className="flex-1" />
      <div className="flex flex-col gap-1.5 px-4 pb-7 pt-3">
        <FieldButton
          className="w-full"
          disabled={
            busy ||
            !line ||
            !reason ||
            !Number.isInteger(Number(qty)) ||
            Number(qty) < 1 ||
            Number(qty) > (line?.cases ?? 0)
          }
          onClick={() => void send()}
        >
          Send to dispatcher
        </FieldButton>
        <p className="text-center text-xs leading-4 text-secondary">
          {trip.vehicle} goes on hold until dispatch decides
        </p>
      </div>
    </section>
  )
}
function HoldScreen({
  trip,
  events,
  pendingReport,
}: {
  trip: DockDetail
  events: OutboxEvent[]
  pendingReport?: OutboxEvent
}) {
  const h = trip.hold,
    l = trip.load_list.find(
      (l) => l.order_id === (h?.order_id ?? pendingReport?.payload?.order_id),
    ),
    s = h?.waiting_seconds ?? 0
  return (
    <>
      <PhoneStatus serverTime={trip.server_time} />
      <FieldHeader
        back="/dock"
        title={`${trip.vehicle} · Trip ${trip.trip_no} · ${trip.district}`}
        subtitle={`On hold · Plan v${trip.version.number}`}
      />
      <div
        role="status"
        className="flex items-center gap-3 bg-warning-bg px-4 py-[10px] text-warning-fg"
      >
        <img alt="" src="/figma/102e0.svg" />
        <div>
          <p className="text-sm font-semibold leading-[18px]">Departure on hold</p>
          <p className="text-xs leading-4">
            Do not release {trip.vehicle} until the new plan arrives
          </p>
        </div>
      </div>
      {pendingReport && <SyncBar events={events} />}
      <div className="flex flex-col gap-1.5 border-b border-line bg-surface px-4 pb-4 pt-5">
        <p className="text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] text-secondary">
          {pendingReport ? 'Saved on this phone' : 'Sent to dispatch'} ·{' '}
          {hhmm(h?.reported_at ?? pendingReport?.event_time)}
        </p>
        <h1 className="text-[28px] font-semibold leading-[34px] tracking-[-0.28px]">
          Waiting for dispatcher
        </h1>
        <div className="flex gap-6 pt-2">
          <div>
            <p className="font-mono text-xl leading-6">
              {String(Math.floor(s / 60)).padStart(2, '0')}:{String(s % 60).padStart(2, '0')}
            </p>
            <p className="text-xs leading-4 text-secondary">Waiting</p>
          </div>
          <div>
            <p className="font-mono text-xl leading-6">{h?.to_departure_minutes ?? '—'} min</p>
            <p className="text-xs leading-4 text-secondary">To planned departure</p>
          </div>
        </div>
      </div>
      <Caption pad="pb-2 pt-[18px]">You reported</Caption>
      <KeyValue
        label="Order"
        value={`${h?.order_ref ?? l?.order_ref} · ${h?.outlet_code ?? l?.outlet_code}`}
      />
      <KeyValue
        label="Problem"
        value={
          <span className="text-warning-fg">
            {(h?.kind ?? pendingReport?.payload?.kind) === 'damaged' ? 'Damaged' : 'Missing'} ·{' '}
            {h?.qty ?? Number(pendingReport?.payload?.qty)} of {h?.planned_cases ?? l?.cases} cases
          </span>
        }
      />
      <KeyValue
        label="Reason"
        value={reasons[h?.reason ?? String(pendingReport?.payload?.reason)]}
      />
      <Caption pad="pb-2 pt-[18px]">What happens next</Caption>
      <div className="border-y border-line bg-surface py-1">
        {[
          [
            pendingReport ? 'Report waiting to upload' : 'Dispatch received your report',
            hhmm(h?.reported_at ?? pendingReport?.event_time),
          ],
          ['Dispatch picks an option', 'Usually a few minutes'],
          [`You check plan v${trip.version.number + 1} here`, 'Then release the van'],
        ].map(([title, detail], i) => (
          <div key={title} className="flex items-center gap-3 px-4 py-[10px]">
            <span
              className={`flex size-6 shrink-0 items-center justify-center rounded-full ${i === 0 && !pendingReport ? 'bg-success-fg' : i === 1 ? 'border-2 border-brand' : 'border-2 border-dashed border-line-strong'}`}
            >
              {i === 0 && !pendingReport && <Icon name="checkWhite" />}
            </span>
            <div>
              <p className="text-sm font-semibold leading-[18px]">{title}</p>
              <p className="font-mono text-[11px] leading-[14px] tracking-[0.22px] text-secondary">
                {detail}
              </p>
            </div>
          </div>
        ))}
      </div>
      <div className="flex-1" />
      <div className="px-4 pb-7 pt-3">
        <Link to="/dock">
          <FieldButton className="w-full" kind="secondary" arrow={false}>
            Load another trip meanwhile
          </FieldButton>
        </Link>
      </div>
    </>
  )
}
function Revision({
  trip,
  events,
  pendingAck,
}: {
  trip: DockDetail
  events: OutboxEvent[]
  pendingAck: boolean
}) {
  const own = trip.changes.filter((c) => c.vehicle === trip.vehicle && c.trip_no === trip.trip_no),
    other = trip.changes.filter((c) => c.vehicle !== trip.vehicle || c.trip_no !== trip.trip_no)
  return (
    <>
      <PhoneStatus serverTime={trip.server_time} />
      <FieldHeader
        back="/dock"
        title={`${trip.vehicle} · Trip ${trip.trip_no} · ${trip.district}`}
        subtitle={`Plan v${trip.version.number} · received ${hhmm(trip.version.published_at)}`}
      />
      <SyncBar
        events={events}
        onlineTitle="Hold lifted when you acknowledge"
        onlineDetail={trip.version.change_reason ?? 'Dispatcher published a revised load'}
      />
      <div className="flex flex-col gap-1.5 border-b border-line bg-surface px-4 py-5">
        <p className="text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] text-brand-text">
          Plan v{trip.previous_version} → v{trip.version.number}
        </p>
        <h1 className="text-[28px] font-semibold leading-[34px] tracking-[-0.28px]">
          {own.length + (trip.previous_departure !== trip.departure ? 1 : 0)}{' '}
          {own.length + (trip.previous_departure !== trip.departure ? 1 : 0) === 1
            ? 'change'
            : 'changes'}{' '}
          to this load
        </h1>
      </div>
      <Caption meta={`v${trip.previous_version} → v${trip.version.number}`}>Load order</Caption>
      {trip.load_list.map((l, i) => {
        const c = own.find((c) => c.order_id === l.order_id)
        return (
          <div
            key={l.order_id}
            className={`flex items-center gap-3 border-b border-line px-4 py-4 ${c ? 'bg-warning-bg' : 'bg-surface'}`}
          >
            <div className="flex-1">
              <p
                className={`text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] ${c ? 'text-warning-fg' : 'text-secondary'}`}
              >
                {i === 0 ? '1st' : i === 1 ? '2nd' : `${i + 1}th`} in
              </p>
              <p className="text-base font-semibold leading-5">
                {l.outlet_code} · {l.order_ref}
              </p>
            </div>
            {c && <del className="font-mono text-xl text-tertiary">{c.before}</del>}
            <span className={`font-mono text-xl leading-6 ${c ? 'text-warning-fg' : ''}`}>
              {l.cases}
            </span>
            <span className="text-xs text-secondary">cases</span>
          </div>
        )
      })}
      {own
        .filter((c) => c.after === 0)
        .map((c) => (
          <KeyValue
            key={c.order_id}
            label={`${c.outlet_code} · ${c.order_ref}`}
            value={`${c.before} → 0 cases`}
          />
        ))}
      {trip.previous_departure !== trip.departure && (
        <KeyValue
          label="Departure"
          value={time(trip.previous_departure) + ' → ' + time(trip.departure)}
        />
      )}
      {other.map((c) => (
        <div
          key={`${c.vehicle}:${c.trip_no}:${c.order_id}`}
          className="flex items-center gap-3 border-b border-line bg-surface px-4 py-4"
        >
          <img src="/figma/dock/plus.svg" alt="" />
          <div className="flex-1">
            <p className="text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] text-brand-text">
              {c.vehicle !== trip.vehicle ? `${c.vehicle} · ` : ''}Trip {c.trip_no} ·{' '}
              {time(c.departure)}
            </p>
            <p className="text-base font-semibold leading-5">
              {c.after - c.before > 0 ? '+' : ''}
              {c.after - c.before} cases for {c.outlet_code}
            </p>
          </div>
          <span className="font-mono text-xl text-brand-text">
            {c.before} → {c.after}
          </span>
        </div>
      ))}
      <div className="flex-1" />
      <div className="px-4 pb-7 pt-3">
        <FieldButton
          className="w-full"
          disabled={pendingAck}
          onClick={() =>
            void enqueue('trip_acknowledged', { type: 'trip', id: trip.id }, trip.version.id)
          }
        >
          {pendingAck
            ? 'Saved · waiting to upload'
            : `Acknowledge v${trip.version.number} · release van`}
        </FieldButton>
      </div>
    </>
  )
}
