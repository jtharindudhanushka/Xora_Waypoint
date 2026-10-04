import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button } from '../../../ui/Button'
import { FigmaIcon } from '../../../ui/FigmaIcon'
import { useApplyRepair, useShortfall } from './api'

const clock = (value: string | null) => value?.slice(0, 5) ?? '—'
const caption =
  'text-[11px] leading-[14px] font-semibold uppercase tracking-[0.66px] text-secondary'

/** D6 / 156:283. BR-28/29 decisions and forecasts come entirely from the API. */
export function ShortfallWorkspace() {
  const { id = '' } = useParams()
  const query = useShortfall(id)
  const apply = useApplyRepair(id)
  const navigate = useNavigate()
  const [selected, setSelected] = useState<string | null>(null)
  const data = query.data
  if (!data)
    return (
      <p className="p-6" role={query.error ? 'alert' : undefined}>
        {query.error?.message ?? 'Loading shortfall…'}
      </p>
    )
  const choice =
    data.options.find((o) => o.id === selected) ?? data.options.find((o) => o.recommended)
  const waiting = `${Math.floor(data.waiting_seconds / 60)
    .toString()
    .padStart(2, '0')}:${(data.waiting_seconds % 60).toString().padStart(2, '0')}`
  const report = [
    ['Order', `${data.order_ref} · ${data.outlet_code} · ${data.district}`],
    [
      'Problem',
      `${data.kind.charAt(0).toUpperCase()}${data.kind.slice(1)} · ${data.missing_cases} of ${data.planned_cases} ${data.temp_requirement} cases`,
    ],
    ['Reason', data.reason],
    ['Reported by', `${data.reporter} · loader`],
  ]
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-surface">
      <div className="flex h-16 shrink-0 items-center gap-3 bg-warning-bg px-6 py-3 text-warning-fg">
        <FigmaIcon name="pause" />
        <div className="flex-1 leading-5">
          <p className="text-base font-semibold">
            {data.vehicle_code} · Trip {data.trip_no} is on hold at {data.dock ?? 'the dock'}
          </p>
          <p>
            Loader reported a shortfall at {clock(data.reported_at)}. The van can’t leave until you
            choose.
          </p>
        </div>
        <div className="text-right">
          <p className="font-mono text-xl leading-6 tracking-[-0.4px]">{waiting}</p>
          <p className="text-xs leading-4">Waiting</p>
        </div>
        <div className="ml-3 text-right">
          <p className="font-mono text-xl leading-6 tracking-[-0.4px]">
            {data.to_departure_minutes} min
          </p>
          <p className="text-xs leading-4">To planned departure {clock(data.planned_depart)}</p>
        </div>
      </div>
      <h1 className="shrink-0 px-6 pt-5 pb-2 text-[22px] leading-7 font-semibold tracking-[-0.11px]">
        Resolve shortfall before departure
      </h1>
      <div className="flex min-h-0 flex-1">
        <section className="w-[480px] shrink-0 border-r border-line">
          <div className="flex items-center gap-2 px-6 pt-4 pb-2">
            <h2 className={`${caption} flex-1`}>What the loader reported</h2>
            <span className="font-mono text-[11px] leading-[14px] tracking-[0.22px] text-secondary">
              {clock(data.reported_at)} · {data.dock ?? 'the dock'}
            </span>
          </div>
          {report.map(([label, value]) => (
            <div key={label} className="flex gap-3 border-b border-line px-6 py-[11px]">
              <span className="leading-5 text-secondary">{label}</span>
              <span
                className={`flex-1 text-right font-semibold leading-[18px] ${label === 'Problem' ? 'text-warning-fg' : ''}`}
              >
                {value}
              </span>
            </div>
          ))}
          <h2 className={`${caption} px-6 pt-4 pb-2`}>
            Trip as published (v{data.version_number})
          </h2>
          {data.stops.map((stop, i) => (
            <div
              key={`${stop.order_ref}-${i}`}
              className="flex items-center gap-3 border-b border-line px-6 py-2.5"
            >
              <span className="font-mono text-[13px] leading-[18px] text-secondary">{i + 1}</span>
              <div className="flex flex-1 flex-col gap-px">
                <span className="font-semibold leading-[18px]">
                  {stop.outlet_code} · {stop.order_ref}
                </span>
                <span className="text-xs leading-4 text-secondary">
                  Window {clock(stop.window_open)}–{clock(stop.window_close)}
                </span>
              </div>
              <span
                className={`font-mono text-[11px] leading-[14px] tracking-[0.22px] ${stop.cases !== stop.available_cases ? 'text-warning-fg' : ''}`}
              >
                {stop.cases !== stop.available_cases
                  ? `${stop.cases} → ${stop.available_cases}`
                  : stop.cases}{' '}
                cases
              </span>
            </div>
          ))}
        </section>
        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-start px-6 pt-4 pb-3">
            <h2 className={`${caption} flex-1`}>{data.options.length} ways to fix it · pick one</h2>
            <span className="font-mono text-[11px] leading-[14px] tracking-[0.22px] text-secondary">
              Engine repair · {(data.solve_ms / 1000).toFixed(1)} s
            </span>
          </div>
          <div className="flex items-center gap-2.5 bg-info-bg px-6 py-2.5">
            <FigmaIcon name="home" />
            <span className="font-semibold text-info-fg">
              {data.outlet_code}’s rule (set by the store):
            </span>
            <span>{data.split_rule_text}</span>
          </div>
          <div className="mx-6 flex" role="radiogroup" aria-label="Repair options">
            <div className="w-[130px] shrink-0 pt-24">
              {[`${data.outlet_code} gets`, 'Delay', 'Other stops', 'Loss'].map((label) => (
                <div
                  className="flex h-14 items-center border-b border-line text-secondary"
                  key={label}
                >
                  {label}
                </div>
              ))}
            </div>
            {data.options.map((option) => {
              const active = choice?.id === option.id
              const values = [option.gets, option.delay, option.other_stops, option.loss_label]
              return (
                <div
                  key={option.id}
                  className={`min-w-0 flex-1 ${active ? 'border-t-4 border-brand bg-brand-subtle' : ''}`}
                >
                  <button
                    type="button"
                    role="radio"
                    aria-checked={active}
                    aria-label={`Option ${option.label}`}
                    onClick={() => setSelected(option.id)}
                    className="flex h-24 w-full flex-col gap-1.5 border-b border-line px-4 py-3 text-left"
                  >
                    <span className="flex w-full items-center gap-2.5">
                      <span
                        className={`flex size-5 shrink-0 items-center justify-center rounded-full border-2 ${active ? 'border-brand' : 'border-line-strong'}`}
                      >
                        {active && <span className="size-2.5 rounded-full bg-brand" />}
                      </span>
                      <span className="flex-1 text-base leading-5 font-semibold">
                        Option {option.label}
                      </span>
                      {option.recommended && (
                        <span className="text-xs leading-4 font-semibold text-brand-text">
                          Recommended
                        </span>
                      )}
                    </span>
                    <span className="leading-5">{option.title}</span>
                    {option.breaks_store_rule && (
                      <span className="text-xs leading-4 font-semibold text-danger-fg">
                        Breaks {data.outlet_code}’s rule
                      </span>
                    )}
                  </button>
                  {values.map((value, i) => (
                    <div
                      key={i}
                      className={`flex min-h-14 items-center border-b border-line px-4 font-semibold leading-[18px] ${i === 0 && option.label === 'B' ? '' : (i === 0 && option.breaks_store_rule) || (i === 1 && option.delay !== 'None') || (i === 2 && option.other_stops !== 'Unchanged') || (i === 3 && option.loss_label !== 'Lowest') ? 'text-warning-fg' : 'text-success-fg'}`}
                    >
                      {value}
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
          {(apply.error || query.error) && (
            <p role="alert" className="mx-6 mt-4 text-danger-fg">
              {apply.error?.message ?? query.error?.message}
            </p>
          )}
          {!data.options.length && (
            <p className="mx-6 mt-4">
              No feasible repair is available. Review the hold with the dock.
            </p>
          )}
          <footer className="mt-auto flex items-center gap-3 border-t border-line px-6 py-4">
            <p className="flex-1 text-secondary">
              Publishes plan v{data.next_version_number} to the dock and the driver
            </p>
            <Button
              size="sm"
              variant="outline"
              disabled
              title="Dock contact number is not configured"
            >
              Call the dock
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={!choice || apply.isPending || !!query.error}
              onClick={() =>
                choice &&
                apply.mutate(choice.id, {
                  onSuccess: (plan) => navigate(`/dispatch/plan?date=${plan.operating_date}`),
                })
              }
            >
              Apply {choice?.label ?? '—'} · publish v{data.next_version_number}
              <FigmaIcon name="arrow" />
            </Button>
          </footer>
        </section>
      </div>
    </div>
  )
}
