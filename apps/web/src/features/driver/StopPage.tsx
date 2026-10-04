import { useNavigate, useParams } from 'react-router-dom'

import { enqueue, hhmm, useOutbox } from '../field/outbox'
import { Caption, FieldButton, FieldHeader, Icon, StatusPip, SyncBar } from '../field/ui'
import {
  localState,
  time,
  useVehicleToday,
  type StopView,
  type TripView,
  type VehicleToday,
} from './data'
import { Message, reviewLink } from './TripPage'

export function findStop(day: VehicleToday | undefined, id: string | undefined) {
  for (const trip of day?.trips ?? []) {
    const stop = trip.stops.find((s) => s.id === id)
    if (stop) return { trip, stop }
  }
  return null
}

export const stopSubtitle = (day: VehicleToday, trip: TripView) =>
  `${day.vehicle_code} · Trip ${trip.trip_no} · Plan v${day.version?.number ?? 1}`

/** R2 · Stop detail (Figma 143:73): store note first, two clocks, outlet-profile access (BR-33, BR-39). */
export function StopPage() {
  const { id } = useParams()
  const { data: day } = useVehicleToday()
  const events = useOutbox()
  const navigate = useNavigate()
  const found = findStop(day, id)
  if (!day || !found) return <Message text="Stop not found on this phone." />
  const { trip, stop } = found
  const { arrived, outcomes } = localState(events)
  const hasArrived = Boolean(stop.arrived_at || arrived.has(stop.id))
  const done = Boolean(stop.outcome || outcomes.has(stop.id))
  const status = done
    ? (['Delivered', 'success'] as const)
    : hasArrived
      ? (['Arrived', 'brand'] as const)
      : (['In transit', 'brand'] as const)

  const onArrived = async () => {
    if (!hasArrived) {
      await enqueue('arrived', { type: 'stop', id: stop.id }, day.version?.id ?? null)
    }
    navigate(`/driver/stops/${stop.id}/outcome`)
  }

  return (
    <div className="flex flex-1 flex-col">
      <FieldHeader
        title={`Stop ${stop.seq} of ${trip.stops.length}`}
        subtitle={stopSubtitle(day, trip)}
        back="/driver"
      />
      <SyncBar events={events} reviewTo={reviewLink} />
      {stop.store_note && (
        <div className="flex w-full items-start gap-3 bg-warning-bg px-4 py-3">
          <Icon name="alertTriangle" />
          <div className="flex min-w-0 flex-1 flex-col gap-0.5 font-semibold">
            <p className="text-[11px] uppercase leading-[14px] tracking-[0.66px] text-warning-fg">
              Today · note from the store, {hhmm(stop.store_note_at)}
            </p>
            <p className="text-base leading-5 text-primary">{stop.store_note}</p>
          </div>
        </div>
      )}
      <div className="flex w-full flex-col gap-1.5 border-b border-line bg-surface p-4">
        <p className="text-[28px] font-semibold leading-[34px] tracking-[-0.28px] text-primary">
          {stop.outlet_code}
        </p>
        <div className="flex w-full items-center gap-2.5">
          <p className="text-base font-semibold leading-5 text-primary">
            Window {time(stop.window_open)}–{time(stop.window_close)}
          </p>
          <StatusPip label={status[0]} tone={status[1]} />
        </div>
        <div className="flex w-full items-start gap-6 whitespace-nowrap pt-2">
          <Clock value={time(stop.plan_arrival)} label="Plan arrival" />
          <Clock
            value={`${time(stop.likely_from)}–${time(stop.likely_to)}`}
            label="Likely arrival"
          />
        </div>
      </div>
      <Caption
        meta={
          <button
            type="button"
            onClick={() => navigate(`/driver/stops/${stop.id}/outcome`)}
            className="font-sans text-sm font-semibold leading-[18px] tracking-normal text-brand-text underline"
          >
            Report a problem
          </button>
        }
      >
        Access · from outlet profile
      </Caption>
      <AccessRows stop={stop} />
      <Caption meta={`Plan v${day.version?.number ?? 1}`}>Hand over</Caption>
      {stop.orders.map((order) => (
        <div
          key={order.order_id}
          className="flex w-full items-center gap-3 border-b border-line bg-surface px-4 py-3"
        >
          {order.temp_requirement === 'chilled' ? (
            <Icon name="snowflake" />
          ) : (
            <span className="size-5" />
          )}
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <p className="text-base font-semibold leading-5 text-primary">
              {order.order_ref} · {order.temp_requirement === 'chilled' ? 'Chilled' : 'Ambient'}
            </p>
            <p className="text-xs leading-4 text-secondary">
              {order.weight_kg.toFixed(1)} kg · {order.volume_m3.toFixed(1)} m³
              {order.temp_requirement === 'chilled' ? ' · keep in reefer until handover' : ''}
            </p>
          </div>
          <p className="font-mono text-xl font-medium leading-6 tracking-[-0.4px] text-primary">
            {order.planned_cases}
          </p>
        </div>
      ))}
      <div className="flex-1" />
      <div className="flex w-full items-start gap-2 px-4 py-3">
        <FieldButton kind="secondary" arrow={false} onClick={() => (window.location.href = 'tel:')}>
          Call store
        </FieldButton>
        <FieldButton
          className="flex-1"
          disabled={done || trip.on_hold}
          onClick={() => void onArrived()}
        >
          {hasArrived ? 'Record delivery' : 'Arrived'}
        </FieldButton>
      </div>
    </div>
  )
}

function Clock({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <p className="font-mono text-xl font-medium leading-6 tracking-[-0.4px] text-primary">
        {value}
      </p>
      <p className="text-xs leading-4 text-secondary">{label}</p>
    </div>
  )
}

function AccessRows({ stop }: { stop: StopView }) {
  const rows: { icon: 'truck' | 'pin'; text: string }[] = []
  if (stop.parking_constraint === 'van_only')
    rows.push({ icon: 'truck', text: 'Van only · trucks can’t serve this outlet' })
  if (stop.parking_constraint === 'mall_dock' && stop.mall_window_open)
    rows.push({
      icon: 'pin',
      text: `Mall dock · ${time(stop.mall_window_open)}–${time(stop.mall_window_close)}`,
    })
  if (stop.dock_type === 'street')
    rows.push({ icon: 'pin', text: 'Street unloading · no dock at this outlet' })
  if (stop.access_note) rows.push({ icon: 'pin', text: stop.access_note })
  return (
    <>
      {rows.map((row) => (
        <div
          key={row.text}
          className="flex w-full items-center gap-3 border-b border-line bg-surface px-4 py-3"
        >
          <span className="flex size-5 items-center justify-center">
            <Icon name={row.icon} />
          </span>
          <p className="flex-1 text-base leading-6 text-primary">{row.text}</p>
        </div>
      ))}
    </>
  )
}
