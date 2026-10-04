import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { Button } from '../../../ui/Button'
import { FigmaIcon } from '../../../ui/FigmaIcon'
import { StatusBadge, type Status } from '../../../ui/StatusBadge'
import { dayLabel } from '../planning/format'
import { useFix, useOps } from './api'

const clock = (value: string | null) => value?.slice(0, 5) ?? '—'

export function LiveOpsWorkspace() {
  const [search] = useSearchParams()
  const date = search.get('date') ?? '2026-04-07'
  const query = useOps(date)
  const fix = useFix()
  const [expanded, setExpanded] = useState(false)
  const ops = query.data
  if (!ops)
    return (
      <div className="p-6" role={query.error ? 'alert' : undefined}>
        {query.error?.message ?? 'Loading live operations…'}
        {query.error && (
          <Link to={`/dispatch/plan?date=${date}`} className="ml-4 underline">
            Open plan
          </Link>
        )}
      </div>
    )
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-start gap-12 border-b border-line bg-surface px-6 py-4">
        <div className="flex-1">
          <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.11px]">
            Today · {dayLabel(date)}
          </h1>
          <p className="mt-0.5 text-sm leading-5 text-secondary">
            Plan v{ops.number} · {ops.trips.length} trips on the road · {ops.depot}
          </p>
        </div>
        {[
          [`${ops.delivered} / ${ops.stops_total}`, 'Delivered', 'text-primary'],
          [`${ops.on_time} / ${ops.delivered}`, 'On time so far', 'text-success-fg'],
          [String(ops.pending_sync), 'Driver pending sync', 'text-secondary'],
          [String(ops.exceptions.length), 'Exceptions', 'text-warning-fg'],
        ].map(([value, label, tone]) => (
          <div key={label} className="text-right">
            <p className={`font-mono text-xl leading-6 tracking-[-0.4px] ${tone}`}>{value}</p>
            <p className="mt-0.5 text-xs leading-4 text-secondary">{label}</p>
          </div>
        ))}
      </div>
      {fix.error && (
        <p role="alert" className="bg-danger-bg px-6 py-3 text-danger-fg">
          {fix.error.message}
        </p>
      )}
      <div className="flex min-h-0 flex-1">
        <section className="w-[520px] shrink-0 overflow-auto border-r border-line bg-surface">
          <div className="flex items-center gap-2 px-6 pt-4 pb-2 text-[11px] leading-[14px] text-secondary">
            <h2 className="flex-1 font-semibold tracking-[0.66px] uppercase">
              Exceptions · ranked by impact
            </h2>
            <span className="font-mono tracking-[0.22px]">Suggested fix</span>
          </div>
          {ops.exceptions.map((item, index) => {
            const highlighted = index === 0 && item.kind === 'late_risk'
            const action = item.suggested_fix.action
            return (
              <article
                key={item.id}
                className={`flex flex-col gap-2 border-b px-6 py-3.5 ${highlighted ? 'border-brand border-l-4 bg-brand-subtle' : 'border-line'}`}
              >
                <div className="flex items-center gap-2.5">
                  {item.kind === 'late_risk' || item.kind === 'pending_sync' ? (
                    <StatusBadge
                      status={item.kind === 'late_risk' ? 'at_risk' : 'pending_sync'}
                      variant="figma"
                    />
                  ) : (
                    <span className="shrink-0 rounded-sm bg-warning-bg px-1.5 py-[3px] font-mono text-[11px] leading-[14px] tracking-[0.22px] text-warning-fg uppercase">
                      {item.kind.replaceAll('_', ' ')}
                    </span>
                  )}
                  <h3 className="text-sm leading-[18px] font-semibold">{item.title}</h3>
                </div>
                <p className="text-sm leading-5">{item.detail}</p>
                {typeof item.suggested_fix.effect === 'string' && (
                  <p className="text-xs leading-4 text-success-fg">{item.suggested_fix.effect}</p>
                )}
                <div>
                  {item.entity_type === 'issue' ? (
                    <Link to={`/dispatch/issues/${item.entity_id}`}>
                      <Button variant="outline" size="sm">
                        Review report
                      </Button>
                    </Link>
                  ) : item.entity_type === 'shortfall' ? (
                    <Link to={`/dispatch/shortfalls/${item.entity_id}`}>
                      <Button variant="outline" size="sm">
                        Resolve shortfall
                      </Button>
                    </Link>
                  ) : (
                    (action === 'swap_stops' || action === 'mark_seen') && (
                      <Button
                        variant={highlighted ? 'secondary' : 'outline'}
                        size="sm"
                        disabled={fix.isPending}
                        onClick={() => fix.mutate(item.id)}
                      >
                        {String(item.suggested_fix.label ?? 'Mark as seen')}
                        {highlighted && <FigmaIcon name="arrow" />}
                      </Button>
                    )
                  )}
                </div>
              </article>
            )
          })}
          {!ops.exceptions.length && <p className="px-6 py-4 text-secondary">No open exceptions</p>}
        </section>
        <section className="min-w-0 flex-1 overflow-auto">
          <div className="flex gap-2 px-6 pt-4 pb-2 text-[11px] leading-[14px] text-secondary">
            <h2 className="flex-1 font-semibold tracking-[0.66px] uppercase">Trips on the road</h2>
            <span className="font-mono tracking-[0.22px]">Stop status · likely arrival</span>
          </div>
          {ops.trips.slice(0, expanded ? undefined : 5).map((trip) => (
            <div
              key={trip.id}
              className="flex items-center gap-4 border-b border-line bg-surface px-6 py-3"
            >
              <div className="w-[130px] shrink-0">
                <p className="font-mono text-[13px] leading-[18px]">
                  {trip.vehicle_code} · T{trip.trip_no}
                </p>
                <p className="mt-px text-xs leading-4 text-secondary">
                  {trip.district}
                  {trip.brand !== 'Fresh' && ' · dry'}
                </p>
              </div>
              <div className="flex min-w-0 items-center overflow-auto">
                {trip.stops.map((stop, index) => (
                  <div key={stop.id} className="flex items-center">
                    {index > 0 && <span className="h-px w-4 shrink-0 bg-line-strong" />}
                    <div className="flex shrink-0 flex-col items-start gap-1 rounded-sm border border-line px-2 py-1.5">
                      <p className="text-xs leading-4 font-semibold">
                        {stop.outlet_code}
                        {stop.top_up_cases > 0 && ` +${stop.top_up_cases}`}
                      </p>
                      <StatusBadge status={stop.status as Status} variant="figma" />
                      <p
                        className={`font-mono text-[11px] leading-[14px] tracking-[0.22px] ${stop.status === 'at_risk' ? 'text-warning-fg' : 'text-secondary'}`}
                      >
                        {stop.actual_at
                          ? new Date(stop.actual_at).toLocaleTimeString('en-GB', {
                              timeZone: 'Asia/Colombo',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : stop.likely_from === stop.likely_to
                            ? clock(stop.likely_from)
                            : `${clock(stop.likely_from)}–${clock(stop.likely_to)}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {ops.trips.length > 5 && !expanded && (
            <button
              type="button"
              className="px-6 py-3 text-sm leading-5 text-secondary"
              onClick={() => setExpanded(true)}
            >
              + {ops.trips.length - 5} more trips ·{' '}
              {ops.trips.slice(5).every((t) => t.stops.every((s) => s.status !== 'at_risk'))
                ? 'all on time'
                : 'view stop status'}
            </button>
          )}
        </section>
      </div>
    </div>
  )
}
