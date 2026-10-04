import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '../../../ui/Button'
import { FigmaIcon } from '../../../ui/FigmaIcon'
import { useFleet, usePlan, usePlanningActions } from './api'
import { DeferredTab } from './DeferredTab'
import { FleetTab } from './FleetTab'
import { PublishDialog } from './PublishDialog'
import { Timeline } from './Timeline'
import { dayLabel } from './format'

export function PlanWorkspace() {
  const [search] = useSearchParams()
  const date = search.get('date') ?? '2026-04-07'
  const query = usePlan(date)
  const fleet = useFleet(date)
  const actions = usePlanningActions(date)
  const [tab, setTab] = useState('Timeline')
  const [lane, setLane] = useState('predawn')
  const [publish, setPublish] = useState(false)
  const [why, setWhy] = useState(false)
  const plan = query.data
  const error = query.error ?? actions.generate.error
  if (!plan)
    return (
      <div className="p-6">
        <h1 className="text-[22px] leading-7 font-semibold">Plan for {dayLabel(date)}</h1>
        <p className="my-4" role={error ? 'alert' : undefined}>
          {error?.message ??
            (query.isPending
              ? 'Loading plan…'
              : 'Orders closed at 16:00. Generate a draft to review trips and deferrals.')}
        </p>
        <Button
          variant="secondary"
          size="sm"
          disabled={query.isPending || actions.generate.isPending}
          onClick={() => actions.generate.mutate()}
        >
          Generate plan
        </Button>
      </div>
    )
  const used = plan.kpis.reefer_m3_used
  const capacity = plan.kpis.reefer_m3_total
  const trips = plan.trips.filter((t) => t.lane === lane)
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-surface">
      <div className="flex items-center gap-10 border-b border-line px-6 py-4">
        <div className="shrink-0">
          <h1 className="text-[22px] leading-7 font-semibold">Plan for {dayLabel(date)}</h1>
          <div className="mt-0.5 font-mono text-[11px] leading-[14px] tracking-[0.22px] text-secondary">
            <span>
              {plan.status === 'draft' ? 'Draft' : `Published v${plan.number}`} ·{' '}
              {plan.orders_total} orders · closed 16:00
            </span>
          </div>
        </div>
        <div className="flex items-end gap-2">
          <div className="font-mono text-xl leading-6">
            {plan.kpis.orders_served}/{plan.orders_total}
          </div>
          <div className="text-secondary">orders served</div>
        </div>
        <div className="flex items-end gap-2">
          <div className="font-mono text-xl leading-6">
            {plan.kpis.chilled_served}/{plan.chilled_total}
          </div>
          <div className="text-secondary">chilled served</div>
        </div>
        <div className="flex items-end gap-2">
          <div className="font-mono text-xl leading-6 text-warning-fg">
            {plan.kpis.stops_at_risk}
          </div>
          <div className="text-secondary">stops at risk</div>
        </div>
        <div className="ml-auto flex gap-10">
          <Button
            variant="outline"
            size="sm"
            disabled={actions.generate.isPending}
            onClick={() => actions.generate.mutate()}
          >
            Re-run
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={plan.status !== 'draft'}
            onClick={() => setPublish(true)}
          >
            Review &amp; publish <FigmaIcon name="arrow" />
          </Button>
        </div>
      </div>
      <div className="flex items-center gap-4 bg-brand-subtle px-6 py-2.5">
        <span className="text-[11px] font-semibold uppercase tracking-[0.66px] text-brand-text">
          Limit today
        </span>
        <span className="text-base font-semibold">Reefer space</span>
        <div className="h-2 w-[220px] overflow-hidden rounded-[1px] bg-surface">
          <div
            className="h-full bg-brand"
            style={{ width: `${capacity ? Math.min(100, (used / capacity) * 100) : 0}%` }}
          />
        </div>
        <span className="font-mono text-[13px] text-brand-text">
          {used.toFixed(1)} / {capacity.toFixed(1)} m³
        </span>
        <span className="text-secondary">
          · {plan.deferrals.filter((d) => d.temp_requirement === 'chilled').length} chilled orders
          deferred
        </span>
        <Button
          size="sm"
          variant="ghost"
          className="ml-auto"
          aria-expanded={why}
          onClick={() => setWhy(!why)}
        >
          Why?
        </Button>
      </div>
      {why && (
        <div className="border-b border-line bg-info-bg px-6 py-3 text-info-fg">
          {plan.bottleneck.explanation}
        </div>
      )}
      {error && (
        <p role="alert" className="bg-danger-bg px-6 py-2 text-danger-fg">
          {error.message}
        </p>
      )}
      <div className="flex h-[100px] shrink-0 items-center gap-6 border-b border-line px-6">
        {[
          ['Timeline', 'Timeline'],
          ['Deferred', `Deferred · ${plan.kpis.deferrals}`],
          [
            'Fleet',
            `Fleet · ${new Set(plan.trips.map((t) => t.vehicle_code)).size} of ${fleet.data?.length ?? '…'}`,
          ],
          ['Orders', `Orders · ${plan.orders_total}`],
        ].map(([key, label]) => (
          <button
            key={key}
            disabled={key === 'Orders'}
            className={`mt-0 border-b-2 py-3 font-semibold ${tab === key ? 'border-brand text-primary' : 'border-transparent text-secondary'}`}
            onClick={() => key && setTab(key)}
          >
            {label}
          </button>
        ))}
        {(tab === 'Timeline' || tab === 'Deferred') && (
          <div className="ml-auto flex overflow-hidden rounded-md border border-line-strong">
            {[
              [
                'predawn',
                `Pre-dawn 03:30–08:00 · Fresh · ${plan.trips.filter((t) => t.lane === 'predawn').length} trips`,
              ],
              [
                'daytime',
                `Daytime · Style & Tech · ${plan.trips.filter((t) => t.lane === 'daytime').length} trips`,
              ],
            ].map(([key, label]) => (
              <button
                key={key}
                onClick={() => key && setLane(key)}
                className={`h-8 px-3 text-xs font-semibold ${lane === key ? 'bg-inverse text-on-inverse' : 'bg-surface text-primary'}`}
              >
                {label}
              </button>
            ))}
          </div>
        )}
        <label
          className={`${tab === 'Fleet' ? 'ml-auto' : ''} flex items-center gap-2 text-sm font-semibold text-primary`}
        >
          <span className="relative h-5 w-9 rounded-full bg-line-strong">
            <span className="absolute top-0.5 left-0.5 size-4 rounded-full bg-surface" />
          </span>
          <input className="sr-only" type="checkbox" disabled />
          Edit trips
        </label>
      </div>
      {tab === 'Timeline' && (
        <Timeline
          key={`${plan.id}-${lane}`}
          plan={plan}
          trips={trips}
          fleet={fleet.data ?? []}
          lane={lane}
          date={date}
        />
      )}
      {tab === 'Deferred' && <DeferredTab key={plan.id} plan={plan} date={date} />}
      {tab === 'Fleet' && <FleetTab plan={plan} date={date} />}
      {publish && <PublishDialog plan={plan} date={date} onClose={() => setPublish(false)} />}
    </div>
  )
}
