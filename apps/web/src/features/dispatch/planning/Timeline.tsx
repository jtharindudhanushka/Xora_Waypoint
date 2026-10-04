import { useState } from 'react'

import { Button } from '../../../ui/Button'
import { FigmaIcon } from '../../../ui/FigmaIcon'
import { usePlanningActions, type FleetVehicle, type Plan, type Trip } from './api'

const minute = (time: string | null) =>
  time ? Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5)) : 0
const timeLabel = (value: number) =>
  `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(Math.round(value) % 60).padStart(2, '0')}`
const vehicleLabel = (v: FleetVehicle | undefined) =>
  v ? `${v.temp === 'reefer' ? 'Reefer' : 'Dry'} ${v.type === 'van' ? 'van' : 'truck'}` : ''

export function Timeline({
  plan,
  trips,
  fleet,
  lane,
  date,
}: {
  plan: Plan
  trips: Trip[]
  fleet: FleetVehicle[]
  lane: string
  date: string
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [closed, setClosed] = useState(false)
  const selected = closed ? undefined : (trips.find((t) => t.id === selectedId) ?? trips[0])
  const vehicle = fleet.find((v) => v.vehicle_code === selected?.vehicle_code)
  const vehicles = [...new Set(trips.map((t) => t.vehicle_code))]
  const start = lane === 'predawn' ? 210 : 480
  const duration = lane === 'predawn' ? 270 : 480
  const actions = usePlanningActions(date)
  return (
    <div className="flex min-h-0 flex-1">
      <div className="min-w-0 flex-1 overflow-auto">
        <div className="relative h-9 border-b border-line bg-surface">
          <div className="absolute inset-y-0 right-[22px] left-[174px]">
            {Array.from({ length: 10 }, (_, i) => (
              <span
                key={i}
                className="absolute top-2.5 -translate-x-1/2 font-mono text-[11px] text-secondary"
                style={{ left: `${(i / 9) * 100}%` }}
              >
                {timeLabel(start + (i * duration) / 9)}
              </span>
            ))}
          </div>
        </div>
        {vehicles.slice(0, expanded ? undefined : 7).map((code) => (
          <div key={code} className="relative h-16 border-b border-line">
            <div className="absolute top-3.5 left-6">
              <div className="flex items-center gap-1.5 font-mono text-[13px] font-medium">
                {fleet.find((v) => v.vehicle_code === code)?.temp === 'reefer' && (
                  <FigmaIcon name="snowflake" />
                )}
                {code}
              </div>
              <div className="text-[11px] text-secondary">
                {vehicleLabel(fleet.find((v) => v.vehicle_code === code))}
              </div>
            </div>
            <div className="absolute inset-y-0 right-[22px] left-[174px]">
              {trips
                .filter((t) => t.vehicle_code === code)
                .map((t) => {
                  const v = fleet.find((v) => v.vehicle_code === code)
                  const risk = t.stops.some((s) => s.at_risk)
                  return (
                    <button
                      key={t.id}
                      aria-label={`${code} trip ${t.trip_no}`}
                      aria-pressed={selected?.id === t.id}
                      onClick={() => {
                        setSelectedId(t.id)
                        setClosed(false)
                      }}
                      className={`absolute top-3 h-10 overflow-hidden rounded-sm border px-2 pt-1.5 text-left ${selected?.id === t.id ? 'border-brand bg-brand-subtle text-primary' : risk ? 'border-warning-fg bg-warning-bg text-warning-fg' : 'border-line-strong bg-sunken text-primary'}`}
                      style={{
                        left: `${((minute(t.planned_depart) - start) / duration) * 100}%`,
                        width: `${(t.plan_minutes / duration) * 100}%`,
                      }}
                    >
                      <span className="flex items-center gap-1.5 truncate text-xs font-semibold">
                        {risk && <FigmaIcon name="alertSmall" />}
                        {t.locked && <FigmaIcon name="lock" />}
                        {t.district} ·{' '}
                        {t.protected_outlets?.length
                          ? `${t.protected_outlets.join(', ')} · protected`
                          : t.stops.length}
                      </span>
                      <span className="absolute right-2 bottom-1.5 left-2 h-1 bg-line">
                        <span
                          className={`block h-1 ${selected?.id === t.id ? 'bg-brand' : 'bg-inverse'}`}
                          style={{
                            width: `${v ? Math.min(100, Math.max(t.weight_kg / v.weight_cap_kg, t.volume_m3 / v.volume_cap_m3) * 100) : 0}%`,
                          }}
                        />
                      </span>
                    </button>
                  )
                })}
            </div>
          </div>
        ))}
        <div className="flex items-center gap-5 border-b border-line px-6 py-3 text-xs text-secondary">
          <span className="mr-auto" />
          <span className="flex items-center gap-2">
            <i className="h-2 w-4 rounded-sm bg-sunken" />
            Trip · bar = plan time
          </span>
          <span className="flex items-center gap-2">
            <i className="h-1 w-4 bg-inverse" />
            Load %
          </span>
          <span className="flex items-center gap-2">
            <i className="h-2 w-4 rounded-sm bg-warning-bg" />
            Likely late
          </span>
          <span className="flex items-center gap-2">
            <i className="h-2 w-4 rounded-sm border border-brand bg-brand-subtle" />
            Selected
          </span>
          {vehicles.length > 7 && (
            <button
              className="ml-auto font-semibold text-primary"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? 'Show fewer' : `+ ${vehicles.length - 7} more vehicles`}{' '}
              <span aria-hidden>↓</span>
            </button>
          )}
        </div>
      </div>
      {selected && (
        <aside
          className="flex w-[380px] shrink-0 flex-col border-l border-line"
          aria-label="Trip panel"
        >
          <div className="flex items-start border-b border-line px-5 py-4">
            <div>
              <h2 className="text-lg leading-6 font-semibold">
                {selected.vehicle_code} · Trip {selected.trip_no}
              </h2>
              <p className="mt-1 font-mono text-[11px] text-secondary">
                {vehicleLabel(vehicle)} · {selected.district} ·{' '}
                {selected.planned_depart?.slice(0, 5)}
              </p>
            </div>
            <button
              className="ml-auto"
              aria-label="Close trip panel"
              onClick={() => setClosed(true)}
            >
              <FigmaIcon name="close" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-5 border-b border-line px-5 py-4">
            {[
              ['Volume', selected.volume_m3, vehicle?.volume_cap_m3, 'm³'],
              ['Weight', selected.weight_kg, vehicle?.weight_cap_kg, 'kg'],
            ].map(([label, used, cap, unit]) => (
              <div key={String(label)}>
                <div className="flex items-center justify-between text-xs font-semibold text-secondary">
                  <span>{label}</span>
                  <span className="font-mono text-[11px] font-medium">
                    {Number(used).toLocaleString('en-GB', {
                      maximumFractionDigits: unit === 'kg' ? 0 : 1,
                    })}{' '}
                    /{' '}
                    {Number(cap ?? 0).toLocaleString('en-GB', {
                      minimumFractionDigits: unit === 'm³' ? 1 : 0,
                    })}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 rounded-[1px] bg-sunken">
                  <div
                    className="h-full rounded-[1px] bg-line-strong"
                    style={{
                      width: `${cap ? Math.min(100, (Number(used) / Number(cap)) * 100) : 0}%`,
                    }}
                  />
                </div>
                <p className="mt-1.5 text-xs text-tertiary">{unit}</p>
              </div>
            ))}
          </div>
          <div className="flex px-5 pt-3.5 pb-1.5 text-[11px] font-semibold text-secondary">
            <span className="uppercase tracking-[0.66px]">Stops</span>
            <span className="ml-auto font-mono font-medium">Plan · Likely</span>
          </div>
          <div className="overflow-auto">
            {selected.stops.map((s) => (
              <div key={s.id} className="flex items-center gap-3 border-b border-line px-5 py-3">
                <span className="font-mono text-[13px] text-secondary">{s.seq}</span>
                <div className="flex-1 text-base font-semibold">{s.outlet_code}</div>
                <div className="font-mono text-[11px]">
                  {s.plan_arrival?.slice(0, 5)} · {s.likely_from?.slice(0, 5)}–
                  {s.likely_to?.slice(0, 5)}
                </div>
              </div>
            ))}
          </div>
          {(selected.rule_messages ?? []).map((v, i) => (
            <div key={i} className="border-b border-line bg-danger-bg px-5 py-3 text-danger-fg">
              <div className="flex gap-2">
                <FigmaIcon name="lock" />
                <span>{v.message}</span>
              </div>
            </div>
          ))}
          {(selected.protected_outlets ?? []).length > 0 && (
            <div className="px-5 py-3 text-xs text-secondary">
              {(selected.protected_outlets ?? []).join(', ')} · protected from another deferral
            </div>
          )}
          {actions.lock.error && (
            <p role="alert" className="px-5 py-2 text-danger-fg">
              {actions.lock.error.message}
            </p>
          )}
          <div className="mt-auto flex gap-2 border-t border-line px-5 py-3">
            <Button
              size="sm"
              variant="outline"
              className="flex-1"
              disabled={plan.status !== 'draft' || actions.lock.isPending}
              onClick={() => actions.lock.mutate({ trip: selected.id, locked: !selected.locked })}
            >
              {selected.locked ? 'Release on re-run' : 'Keep on re-run'}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="flex-1"
              disabled
              title="Available after the core track is merged"
            >
              Edit this trip
            </Button>
          </div>
        </aside>
      )}
    </div>
  )
}
