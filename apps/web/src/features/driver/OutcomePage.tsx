import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { enqueue, fieldNow, hhmm, useOutbox } from '../field/outbox'
import { Caption, FieldButton, FieldHeader, Icon, SyncBar } from '../field/ui'
import { useVehicleToday } from './data'
import { findStop } from './StopPage'
import { Message, reviewLink } from './TripPage'

type Outcome = 'delivered' | 'partial' | 'failed'
const OUTCOMES: [Outcome, string][] = [
  ['delivered', 'Delivered'],
  ['partial', 'Partial'],
  ['failed', 'Failed'],
]

/**
 * R3 · Record outcome (Figma 143:176). A known loading shortfall is pre-filled and locked, never
 * re-reported (BR-34). Saving writes to the phone first (BR-35); the API validates it.
 */
export function OutcomePage() {
  const { id } = useParams()
  const { data: day } = useVehicleToday()
  const events = useOutbox()
  const navigate = useNavigate()
  const found = findStop(day, id)
  const [outcome, setOutcome] = useState<Outcome>('delivered')
  const [counts, setCounts] = useState<Record<string, string>>({})
  const [extra, setExtra] = useState(false)
  const [damaged, setDamaged] = useState('0')
  const [refused, setRefused] = useState('0')
  const [receiver, setReceiver] = useState('')
  const [photoAt, setPhotoAt] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  if (!day || !found) return <Message text="Stop not found on this phone." />
  const { stop, trip } = found
  const chilled = stop.orders.some((o) => o.temp_requirement === 'chilled')
  const refs = stop.orders.map((o) => o.order_ref).join(', ')
  const shortfall = stop.orders.find((o) => o.known_shortfall)
  const followsOn = day.trips.find(
    (t) =>
      t.id !== trip.id &&
      t.stops.some((s) => s.orders.some((o) => o.top_up_of_order_ref === shortfall?.order_ref)),
  )

  const save = async () => {
    setSaving(true)
    const event = await enqueue(
      'outcome_recorded',
      { type: 'stop', id: stop.id },
      day.version?.id ?? null,
      {
        outcome,
        receiver_name: receiver || null,
        // Read by the store receipt draft (BR-46): total cases handed over at this stop.
        cases_handed_over:
          outcome === 'failed'
            ? 0
            : stop.orders.reduce(
                (sum, o) => sum + (Number(counts[o.order_id] ?? o.planned_cases) || 0),
                0,
              ),
        photo_taken_at: photoAt,
        damaged: Number(damaged) || 0,
        refused: Number(refused) || 0,
        orders: stop.orders.map((o) => ({
          order_id: o.order_id,
          order_ref: o.order_ref,
          cases: outcome === 'failed' ? 0 : Number(counts[o.order_id] ?? o.planned_cases) || 0,
        })),
      },
    )
    navigate(`/driver/records/${event.event_id}`)
  }

  return (
    <div className="flex flex-1 flex-col">
      <FieldHeader
        title={`Stop ${stop.seq} of ${trip.stops.length} · ${stop.outlet_code}`}
        subtitle={`Record delivery · ${refs}${chilled ? ' chilled' : ''}`}
        back={`/driver/stops/${stop.id}`}
      />
      <SyncBar
        events={events}
        onlineDetail="Saves on this phone first, then uploads"
        reviewTo={reviewLink}
      />
      <Caption>Outcome</Caption>
      <div className="flex w-full px-4">
        <div
          role="radiogroup"
          className="flex flex-1 overflow-hidden rounded-md border border-line-strong"
        >
          {OUTCOMES.map(([value, label], i) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={outcome === value}
              onClick={() => setOutcome(value)}
              className={`flex h-12 flex-1 items-center justify-center text-base font-semibold leading-5 ${i < 2 ? 'border-r border-line-strong' : ''} ${outcome === value ? 'bg-inverse text-on-inverse' : 'bg-surface text-primary'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <Caption>Quantity</Caption>
      {shortfall?.known_shortfall && (
        <div className="flex w-full items-start gap-3 bg-warning-bg px-4 py-3">
          <Icon name="lock" />
          <div className="flex min-w-0 flex-1 flex-col gap-0.5 text-warning-fg">
            <p className="text-sm font-semibold leading-[18px]">
              {shortfall.known_shortfall.qty} cases short at loading · already reported
            </p>
            <p className="text-xs leading-4">
              {followsOn ? `Follows on trip ${followsOn.trip_no} · ` : ''}no need to report again
            </p>
          </div>
        </div>
      )}
      {stop.orders.map((order) => {
        const short = order.known_shortfall?.qty ?? 0
        return (
          <label key={order.order_id} className="flex w-full flex-col gap-1.5 px-4 pt-3">
            <span className="text-sm font-semibold leading-[18px] text-primary">
              Cases handed over{stop.orders.length > 1 ? ` · ${order.order_ref}` : ''}
            </span>
            <input
              inputMode="numeric"
              disabled={outcome === 'failed'}
              value={
                outcome === 'failed' ? '0' : (counts[order.order_id] ?? String(order.planned_cases))
              }
              onChange={(e) =>
                setCounts({ ...counts, [order.order_id]: e.target.value.replace(/\D/g, '') })
              }
              className="h-12 w-full rounded-md border border-line-strong bg-surface px-3 text-base leading-6 text-primary"
            />
            <span className="text-xs leading-4 text-secondary">
              Loaded {order.planned_cases} · ordered {order.planned_cases + short}
            </span>
          </label>
        )
      })}
      <div className="flex w-full flex-col items-start px-2 py-1">
        <FieldButton kind="ghost" arrow={false} onClick={() => setExtra(!extra)}>
          + Add damaged or refused cases
        </FieldButton>
        {extra && (
          <div className="flex w-full gap-3 px-2 pb-2">
            <NumberField label="Damaged" value={damaged} onChange={setDamaged} />
            <NumberField label="Refused" value={refused} onChange={setRefused} />
          </div>
        )}
      </div>
      <Caption>Proof</Caption>
      <div className="flex w-full items-center gap-3 px-4">
        <label className="flex size-16 shrink-0 cursor-pointer items-center justify-center rounded-sm bg-sunken">
          <Icon name="camera" />
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            onChange={(e) => e.target.files?.length && setPhotoAt(fieldNow())}
          />
        </label>
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <p className="text-sm font-semibold leading-[18px] text-primary">
            {photoAt ? `Photo taken ${hhmm(photoAt)}` : 'Take a photo'}
          </p>
          <input
            aria-label="Received by"
            placeholder="Received by"
            value={receiver}
            onChange={(e) => setReceiver(e.target.value)}
            className="w-full bg-transparent text-xs leading-4 text-secondary outline-none"
          />
        </div>
        {photoAt && (
          <FieldButton kind="ghost" arrow={false} onClick={() => setPhotoAt(null)}>
            Retake
          </FieldButton>
        )}
      </div>
      <div className="flex-1" />
      <div className="flex w-full flex-col gap-1.5 px-4 py-3">
        <FieldButton className="w-full" disabled={saving} onClick={() => void save()}>
          Save delivery
        </FieldButton>
        <p className="w-full text-center text-xs leading-4 text-secondary">
          Saves on this phone even with no signal
        </p>
      </div>
    </div>
  )
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <label className="flex flex-1 flex-col gap-1.5">
      <span className="text-sm font-semibold leading-[18px] text-primary">{label}</span>
      <input
        inputMode="numeric"
        value={value}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, ''))}
        className="h-12 w-full rounded-md border border-line-strong bg-surface px-3 text-base leading-6 text-primary"
      />
    </label>
  )
}
