import { Button } from '../../../ui/Button'
import { useState } from 'react'
import { dayLabel } from './format'
import { FigmaIcon } from '../../../ui/FigmaIcon'
import { StatusBadge } from '../../../ui/StatusBadge'
import { useFleet, usePlanningActions, type Plan } from './api'

export function FleetTab({ plan, date }: { plan: Plan; date: string }) {
  const fleet = useFleet(date)
  const actions = usePlanningActions(date)
  const [expanded, setExpanded] = useState(false)
  const all = fleet.data ?? []
  const featured = [
    ...all.filter((v) => v.status === 'available' && v.temp === 'reefer' && v.type === 'van'),
    ...all.filter((v) => v.status === 'available' && v.temp === 'reefer' && v.type !== 'van'),
    ...all.filter((v) => v.status === 'workshop' && v.type !== 'van').slice(0, 1),
    ...all.filter((v) => v.status === 'workshop' && v.type === 'van').slice(0, 1),
    ...all.filter((v) => v.status !== 'workshop' && v.temp !== 'reefer' && v.type === 'van'),
  ]
  const shown = expanded ? all : featured
  return (
    <div className="overflow-auto">
      <div className="flex items-center border-b border-line px-6 py-4">
        <div>
          <h2 className="text-base font-semibold">Vehicles for {dayLabel(date)}</h2>
          <p className="mt-1 text-xs text-secondary">
            The engine only plans with switched-on vehicles
          </p>
        </div>
        <Button
          className="ml-auto"
          size="sm"
          variant="outline"
          disabled={actions.generate.isPending}
          onClick={() => actions.generate.mutate()}
        >
          Re-run with changes
        </Button>
      </div>
      {(fleet.error ?? actions.switchFleet.error ?? actions.generate.error) && (
        <p role="alert" className="bg-danger-bg px-6 py-2 text-danger-fg">
          {(fleet.error ?? actions.switchFleet.error ?? actions.generate.error)?.message}
        </p>
      )}
      <div className="grid grid-cols-[56px_150px_200px_220px_160px_1fr] gap-4 border-b border-line bg-canvas px-6 py-2 text-[11px] leading-[14px] font-semibold tracking-[0.66px] text-secondary uppercase">
        {['', 'Vehicle', 'Capacity', 'Fuel this week', 'Status', 'Planned'].map((s) => (
          <span key={s}>{s}</span>
        ))}
      </div>
      {shown.map((v) => (
        <div
          key={v.vehicle_code}
          className="grid min-h-[60px] grid-cols-[56px_150px_200px_220px_160px_1fr] items-center gap-4 border-b border-line px-6 py-3"
        >
          <button
            role="switch"
            aria-label={`Include ${v.vehicle_code}`}
            aria-checked={v.switched_on}
            disabled={v.status !== 'available' || actions.switchFleet.isPending}
            onClick={() =>
              actions.switchFleet.mutate({
                vehicle: v.vehicle_code,
                switched_on: !v.switched_on,
                off_reason: v.switched_on ? 'dispatcher_off' : undefined,
              })
            }
            className={`relative h-5 w-9 rounded-full disabled:opacity-50 ${v.switched_on ? 'bg-inverse' : 'bg-disabled'}`}
          >
            <span
              className={`absolute top-0.5 size-4 rounded-full bg-surface ${v.switched_on ? 'right-0.5' : 'left-0.5'}`}
            />
          </button>
          <div>
            <div className="font-mono text-[13px]">{v.vehicle_code}</div>
            <div className="flex items-center gap-1 text-xs text-secondary">
              {v.temp === 'reefer' && <FigmaIcon name="snowflake" />}
              {v.temp === 'reefer' ? 'Reefer' : 'Dry'} {v.type === 'van' ? 'van' : 'truck'}
            </div>
          </div>
          <div
            className={`font-mono text-[11px] leading-[14px] tracking-[0.22px] ${v.status === 'workshop' ? 'text-tertiary' : ''}`}
          >
            {v.volume_cap_m3.toFixed(1)} m³ · {v.weight_cap_kg.toLocaleString('en-GB')} kg
          </div>
          <div>
            <div
              className={`font-mono text-[11px] leading-[14px] tracking-[0.22px] ${v.status === 'workshop' ? 'text-tertiary' : ''}`}
            >
              {v.status === 'workshop'
                ? '—'
                : `${v.fuel_used_l.toFixed(0)} / ${(v.fuel_used_l + v.fuel_remaining_l).toFixed(0)} L`}
            </div>
            {v.status !== 'workshop' && (
              <div className="mt-1 h-1 w-[180px] bg-line">
                <div
                  className="h-full bg-inverse"
                  style={{
                    width: `${(v.fuel_used_l / (v.fuel_used_l + v.fuel_remaining_l || 1)) * 100}%`,
                  }}
                />
              </div>
            )}
          </div>
          <div>
            <StatusBadge
              variant="text"
              status={
                v.status === 'workshop' ? 'workshop' : v.switched_on ? 'available' : 'switched_off'
              }
              label={
                v.status === 'workshop'
                  ? 'Workshop'
                  : v.switched_on
                    ? 'Available'
                    : `Switched off · ${v.off_reason?.replaceAll('_', ' ') ?? 'dispatcher'}`
              }
            />
          </div>
          <div className="font-mono text-[11px] leading-[14px] tracking-[0.22px]">
            {plan.trips
              .filter((t) => t.vehicle_code === v.vehicle_code)
              .map((t) => `T${t.trip_no}`)
              .join(' · ') || '—'}
          </div>
        </div>
      ))}
      <button
        className="px-6 py-3.5 text-sm font-semibold text-secondary"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded
          ? 'Show fewer vehicles'
          : `+ ${all.filter((v) => v.type !== 'van' && v.temp !== 'reefer' && v.status === 'available' && v.switched_on).length} dry trucks available · ${all.filter((v) => v.status === 'workshop').length} in workshop`}
      </button>
    </div>
  )
}
