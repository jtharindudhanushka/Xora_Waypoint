import { useEffect } from 'react'
import { Link, Outlet, useNavigate, useSearchParams } from 'react-router-dom'

import { enqueue, hhmm, isPending, startSyncLoop, useOutbox } from '../field/outbox'
import { Caption, FieldButton, FieldHeader, FieldTabBar, Icon, SyncBar } from '../field/ui'
import {
  accessLine,
  cases,
  currentTrip,
  localState,
  pad2,
  time,
  useVehicleToday,
  vehicleLabel,
  type TripView,
  type VehicleToday,
} from './data'

/** Driver frame (phone 390): screens own their header + sync bar; the tab bar is shared. */
export function DriverShell() {
  const events = useOutbox()
  useEffect(() => startSyncLoop(), [])
  return (
    <div className="mx-auto flex min-h-full w-full max-w-[480px] flex-col bg-canvas">
      <Outlet />
      <FieldTabBar
        pending={events.filter(isPending).length}
        home="/driver"
        uploads="/driver/uploads"
      />
    </div>
  )
}

export const reviewLink = (e: { event_id: string }) => `/driver/records/${e.event_id}`

const minutes = (t: string | null | undefined) =>
  t ? Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5)) : null

/** How much slower past runs were than plan, from the realistic windows (BR-18). */
function slowdown(trip: TripView): string | null {
  const depart = minutes(trip.planned_depart)
  const ratios = trip.stops
    .map((s) => {
      const plan = minutes(s.plan_arrival)
      const likely = minutes(s.likely_from)
      // A window clamped to the store opening says nothing about road speed: skip it.
      const clamped = likely !== null && likely <= (minutes(s.window_open) ?? -1)
      return depart !== null && plan !== null && likely !== null && plan > depart && !clamped
        ? (likely - depart) / (plan - depart)
        : null
    })
    .filter((r): r is number => r !== null)
  if (!ratios.length) return null
  return (ratios.reduce((a, b) => a + b, 0) / ratios.length).toFixed(1)
}

function changeNotes(day: VehicleToday, trip: TripView): string | null {
  const notes = trip.stops.flatMap((stop) =>
    stop.orders
      .filter((o) => o.known_shortfall)
      .map((o) => {
        const other = day.trips.find(
          (t) =>
            t.id !== trip.id &&
            t.stops.some((s) => s.orders.some((x) => x.top_up_of_order_ref === o.order_ref)),
        )
        const short = o.known_shortfall!.qty
        return `${stop.outlet_code}: ${o.planned_cases} of ${o.planned_cases + short} cases now${other ? `, ${short} on trip ${other.trip_no}` : ''}`
      }),
  )
  return notes.length ? notes.join(' · ') : null
}

/** R1 · Today's trip (Figma 142:2): acknowledge the current version before starting (BR-32). */
export function TripPage() {
  const { data: day, error, isPending: loading } = useVehicleToday()
  const events = useOutbox()
  const navigate = useNavigate()
  const [params] = useSearchParams()

  if (loading) return <Message text="Loading today’s trip…" />
  if (error || !day) return <Message text={error?.message ?? 'No trip today'} />
  const { acked, outcomes } = localState(events)
  const picked = Number(params.get('trip'))
  const trip = day.trips.find((t) => t.trip_no === picked) ?? currentTrip(day, outcomes)
  if (!day.version || !trip) return <Message text="No published trip for your vehicle today." />

  const version = day.version
  const isAcked = version.acknowledged || acked.has(version.id)
  const districts = new Set(trip.stops.map((s) => s.district))
  const next = trip.stops.find((s) => !s.outcome && !outcomes.has(s.id))
  const ratio = slowdown(trip)
  const changed = version.number > 1 ? changeNotes(day, trip) : null

  const acknowledge = async () => {
    await enqueue('trip_acknowledged', { type: 'trip', id: trip.id }, version.id)
  }

  return (
    <div className="flex flex-1 flex-col">
      <FieldHeader
        title={`Trip ${trip.trip_no} · ${trip.district}`}
        subtitle={`${day.vehicle_code} · ${vehicleLabel(day)} · Plan v${version.number}`}
      />
      <SyncBar
        events={events}
        onlineTitle={`Online · plan v${version.number} received ${hhmm(version.published_at)}`}
        reviewTo={reviewLink}
      />
      {version.number > 1 && (
        <div className="flex w-full items-start border-l-4 border-brand bg-brand-subtle px-4 py-3">
          <div className="flex flex-1 flex-col gap-1 leading-5">
            <p className="text-base font-semibold text-primary">
              Plan changed to v{version.number} at {hhmm(version.published_at)}
            </p>
            <p className="text-sm text-secondary">{changed ?? version.change_reason ?? ''}</p>
          </div>
        </div>
      )}
      {trip.on_hold && (
        <div className="flex w-full items-start border-l-4 border-[var(--danger-solid)] bg-danger-bg px-4 py-3">
          <p className="text-base font-semibold leading-5 text-danger-fg">
            Van on hold at the dock · wait for the revised plan
          </p>
        </div>
      )}
      <div className="flex w-full items-start gap-4 border-b border-line bg-surface px-4 py-3">
        <Stat
          value={`${trip.stops.length} stops`}
          label={districts.size === 1 ? `${trip.district} only` : `${districts.size} districts`}
        />
        <Stat
          value={`${trip.volume_m3.toFixed(1)} m³`}
          label={`${day.vehicle_temp === 'reefer' ? 'Chilled' : 'Ambient'} · ${Math.round(trip.weight_kg)} kg`}
        />
        <Stat value={`${trip.plan_minutes} min`} label="Plan trip time" />
      </div>
      <Caption meta="Plan · Likely" pad="pb-2 pt-4">
        Stops in delivery order
      </Caption>
      {trip.stops.map((stop) => {
        const c = cases(stop)
        const chilled = stop.orders.some((o) => o.temp_requirement === 'chilled')
        const current = isAcked && next?.id === stop.id
        return (
          <Link
            key={stop.id}
            to={`/driver/stops/${stop.id}`}
            className="flex w-full items-start border-b border-line bg-surface"
          >
            <div
              className={`flex w-12 shrink-0 flex-col items-center self-stretch py-4 ${current ? 'border-l-4 border-brand' : ''}`}
            >
              <p className="font-mono text-[13px] font-medium leading-[18px] text-secondary">
                {pad2(stop.seq)}
              </p>
            </div>
            <div className="flex min-w-0 flex-1 flex-col items-start gap-1 py-[14px]">
              <p className="text-base font-semibold leading-5 text-primary">
                {stop.outlet_code} · {stop.district}
              </p>
              <p className="text-xs leading-4 text-secondary">{accessLine(stop)}</p>
              <span className="inline-flex items-center gap-1 rounded-sm bg-info-bg px-1.5 py-0.5">
                {chilled && <Icon name="snowSmall" />}
                <span className="text-xs font-semibold leading-4 text-info-fg">
                  {chilled ? 'Chilled' : 'Ambient'} ·{' '}
                  {c.short ? `${c.planned} of ${c.ordered}` : c.planned} cases
                </span>
              </span>
            </div>
            <div className="flex w-28 shrink-0 flex-col items-end gap-0.5 py-[14px] pl-2 pr-4 text-right">
              <p className="w-full font-mono text-xl font-medium leading-6 tracking-[-0.4px] text-primary">
                {time(stop.plan_arrival)}
              </p>
              <p className="w-full text-xs leading-4 text-secondary">
                {time(stop.likely_from)}–{time(stop.likely_to)}
              </p>
            </div>
          </Link>
        )
      })}
      {ratio && (
        <div className="flex w-full items-start gap-2 px-4 py-3">
          <Icon name="info" />
          <p className="flex-1 text-xs leading-4 text-secondary">
            Likely = from past runs (roads run {ratio}× slower than plan)
          </p>
        </div>
      )}
      {day.trips
        .filter((t) => t.id !== trip.id)
        .map((t) => (
          <Link
            key={t.id}
            to={`/driver?trip=${t.trip_no}`}
            className="flex w-full items-center gap-2 px-4 py-3 text-sm font-semibold leading-[18px] text-brand-text underline"
          >
            Trip {t.trip_no} · {t.district} · departs {time(t.planned_depart)}
          </Link>
        ))}
      <div className="flex-1" />
      <div className="w-full px-4 py-3">
        {!isAcked ? (
          <FieldButton
            className="w-full"
            disabled={trip.on_hold}
            onClick={() => void acknowledge()}
          >
            Acknowledge v{version.number} and start
          </FieldButton>
        ) : next ? (
          <FieldButton className="w-full" onClick={() => navigate(`/driver/stops/${next.id}`)}>
            Go to stop {pad2(next.seq)} · {next.outlet_code}
          </FieldButton>
        ) : null}
      </div>
    </div>
  )
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-0.5 whitespace-nowrap">
      <p className="font-mono text-xl font-medium leading-6 tracking-[-0.4px] text-primary">
        {value}
      </p>
      <p className="text-xs leading-4 text-secondary">{label}</p>
    </div>
  )
}

export function Message({ text }: { text: string }) {
  return <p className="px-4 py-8 text-base leading-6 text-secondary">{text}</p>
}
