import { useEffect, useRef } from 'react'

import { Button } from '../../../ui/Button'
import { FigmaIcon } from '../../../ui/FigmaIcon'
import { usePlanningActions, usePublishCheck, type Plan } from './api'
import { dayLabel } from './format'

export function PublishDialog({
  plan,
  date,
  onClose,
}: {
  plan: Plan
  date: string
  onClose: () => void
}) {
  const gate = usePublishCheck(plan.id, true)
  const actions = usePlanningActions(date)
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    dialog.current?.showModal()
  }, [])
  const warnings = gate.data?.late_risk_order_refs.length ?? 0
  const checks: [string, boolean][] = [
    ['Every trip within weight, volume and reefer rules', gate.data?.violations.length === 0],
    [
      `Pre-dawn budget ≤ 270 min on all ${new Set(plan.trips.filter((t) => t.lane === 'predawn').map((t) => t.vehicle_code)).size} Fresh vehicles`,
      !gate.data?.violations.some((v) => v.rule_id === 'BR-08'),
    ],
    [
      `${plan.deferrals.filter((d) => d.confirmed).length} deferrals confirmed with reasons · stores will be notified`,
      gate.data?.unconfirmed_deferrals.length === 0,
    ],
  ]
  return (
    <dialog
      ref={dialog}
      onCancel={onClose}
      className="planning-dialog fixed top-[180px] m-0 mx-auto w-[560px] rounded-lg border-0 bg-surface p-0 text-primary"
      aria-labelledby="publish-title"
    >
      <div className="relative border-b border-line px-5 py-[18px]">
        <button
          className="absolute top-8 right-5"
          aria-label="Close publish dialog"
          onClick={onClose}
        >
          <FigmaIcon name="close" />
        </button>
        <h2 id="publish-title" className="text-[22px] leading-7 font-semibold">
          Publish plan v{plan.number}
        </h2>
        <p className="mt-0.5 text-secondary">
          {dayLabel(date)} · {plan.depot} · goes to 2 docks and{' '}
          {new Set(plan.trips.map((t) => t.vehicle_code)).size} drivers
        </p>
      </div>
      <div className="flex gap-6 border-b border-line px-5 py-4">
        {[
          [`${plan.kpis.orders_served} / ${plan.orders_total}`, 'Orders served'],
          [`${plan.kpis.chilled_served} / ${plan.chilled_total}`, 'Chilled served'],
          [
            `${Math.round((plan.kpis.reefer_m3_used / (plan.kpis.reefer_m3_total || 1)) * 100)}%`,
            'Reefer m³ used',
          ],
          [gate.data?.violations.length ?? '…', 'Hard-rule breaks'],
        ].map(([value, label]) => (
          <div key={String(label)} className="flex-1">
            <div
              className={`font-mono text-xl leading-6 ${label === 'Hard-rule breaks' && value === 0 ? 'text-success-fg' : ''}`}
            >
              {value}
            </div>
            <div className="text-xs text-secondary">{label}</div>
          </div>
        ))}
      </div>
      <div className="px-5 pt-4 pb-2 text-[11px] leading-[14px] font-semibold tracking-[0.66px] text-secondary">
        CHECKS
      </div>
      {checks.map(([text, ok]) => (
        <div key={text} className="flex items-center gap-2.5 px-5 py-2">
          <FigmaIcon name={ok ? 'check' : 'alert'} />
          <span>{text}</span>
        </div>
      ))}
      {warnings > 0 && (
        <div className="flex gap-2.5 px-5 py-2 text-warning-fg">
          <FigmaIcon name="alert" />
          <span>{warnings} stops likely late (realistic clock)</span>
        </div>
      )}
      {(gate.error ?? actions.publish.error) && (
        <p role="alert" className="px-5 py-2 text-danger-fg">
          {(gate.error ?? actions.publish.error)?.message}
        </p>
      )}
      {gate.data?.violations.map((v) => (
        <p key={`${v.rule_id}-${v.code}`} className="px-5 py-1 text-danger-fg">
          {v.message}
        </p>
      ))}
      <div className="flex items-center gap-2 border-t border-line px-5 py-4">
        <p className="mr-auto text-xs text-secondary">
          Warnings don’t block publishing; hard rules do.
        </p>
        <Button size="sm" variant="outline" onClick={onClose}>
          Back
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={!gate.data?.can_publish || actions.publish.isPending}
          onClick={() => actions.publish.mutate(plan.id, { onSuccess: onClose })}
        >
          Publish plan v{plan.number}
          <FigmaIcon name="arrow" />
        </Button>
      </div>
    </dialog>
  )
}
