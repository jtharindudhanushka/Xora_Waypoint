import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { Button } from '../../../ui/Button'
import { FigmaIcon } from '../../../ui/FigmaIcon'
import { serveInstead, usePlanningActions, type Deferral, type Plan } from './api'
import { dayLabel } from './format'

export function DeferredTab({ plan, date }: { plan: Plan; date: string }) {
  const [selected, setSelected] = useState<string[]>(
    plan.deferrals.filter((d) => !d.confirmed && !d.repeat_skip).map((d) => d.id),
  )
  const [reasons, setReasons] = useState<Record<string, string>>({})
  const [preview, setPreview] = useState<Deferral | null>(plan.deferrals[0] ?? null)
  const [counterfactual, setCounterfactual] = useState<{ id: string; displaces: string[] } | null>(
    null,
  )
  const [error, setError] = useState('')
  const [activeChoice, setActiveChoice] = useState(
    plan.deferrals.find((d) => d.group === 'choice')?.id,
  )
  const [busy, setBusy] = useState(false)
  const actions = usePlanningActions(date)
  const client = useQueryClient()
  const chilled = plan.deferrals.filter((d) => d.temp_requirement === 'chilled')
  async function instead(d: Deferral, confirm = false) {
    setBusy(true)
    setError('')
    try {
      const result = await serveInstead(d.id, confirm)
      if (confirm) {
        setCounterfactual(null)
        await client.invalidateQueries({ queryKey: ['plan', date] })
      } else setCounterfactual({ id: d.id, displaces: result.displaces })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not serve this order')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="overflow-auto">
      <div className="flex items-center border-b border-line px-5 py-4">
        <h2 className="text-lg font-semibold">
          {chilled.length} chilled orders deferred ·{' '}
          {chilled.reduce((s, d) => s + d.volume_m3, 0).toFixed(1)} m³
        </h2>
        <Button
          className="ml-auto"
          size="sm"
          variant="secondary"
          disabled={!selected.length || actions.confirm.isPending || plan.status !== 'draft'}
          onClick={() =>
            actions.confirm.mutate(
              {
                id: plan.id,
                items: selected.map((id) => ({
                  deferral_id: id,
                  reason: reasons[id] || undefined,
                })),
              },
              { onSuccess: () => setSelected([]) },
            )
          }
        >
          Confirm {selected.length} deferrals
        </Button>
      </div>
      <div className="flex items-center gap-2.5 bg-info-bg px-5 text-primary">
        <FigmaIcon name="info" />
        Priority = expected loss if not delivered today. It rises with chilled goods, days since
        last served, a deferral yesterday, festival week and mall windows.
      </div>
      {(error || actions.confirm.error) && (
        <p role="alert" className="bg-danger-bg px-5 py-2 text-danger-fg">
          {error || actions.confirm.error?.message}
        </p>
      )}
      {['unavoidable', 'choice'].map((group) => {
        const rows = plan.deferrals.filter((d) => d.group === group)
        return (
          <section key={group}>
            <div className="flex px-5 pt-4 pb-2 text-[11px] font-semibold tracking-[0.66px] uppercase text-secondary">
              <span>
                {group === 'unavoidable'
                  ? `No space anywhere · ${rows.length}`
                  : `Bumped by a higher priority · ${rows.length}`}
              </span>
              <span className="ml-auto font-mono">
                {group === 'unavoidable'
                  ? 'No reefer trip left can take it'
                  : 'You can serve one instead'}
              </span>
            </div>
            {rows.map((d) => (
              <div
                key={d.id}
                onClick={() => {
                  if (group === 'choice') setActiveChoice(d.id)
                  setPreview(d)
                }}
                onFocus={() => {
                  if (group === 'choice') setActiveChoice(d.id)
                }}
                className="flex items-start gap-4 border-b border-line px-5 py-3"
              >
                <input
                  type="checkbox"
                  aria-label={`Confirm ${d.order_ref}`}
                  checked={selected.includes(d.id)}
                  disabled={d.confirmed || plan.status !== 'draft'}
                  onChange={(e) =>
                    setSelected(
                      e.target.checked ? [...selected, d.id] : selected.filter((id) => id !== d.id),
                    )
                  }
                  className="mt-1 h-[22px] w-[22px] shrink-0 accent-[var(--bg-inverse)]"
                />
                <div className="w-[170px] shrink-0">
                  <div className="text-sm font-semibold">
                    {d.outlet_code} · {d.district}
                  </div>
                  <div className="mt-0.5 whitespace-nowrap font-mono text-[11px] leading-[14px] text-secondary">
                    {d.order_ref} · {d.temp_requirement} {d.volume_m3.toFixed(1)} m³
                  </div>
                  <div className="mt-0.5 font-mono text-[11px] leading-[14px] text-brand-text">
                    Priority {Math.round(d.priority)}
                  </div>
                  {d.repeat_skip && (
                    <span className="text-xs text-warning-fg">
                      Moved yesterday · needs a reason
                    </span>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <span
                    className={`mb-1.5 inline-block rounded-sm px-1.5 py-[3px] font-mono text-[11px] leading-[14px] ${group === 'unavoidable' ? 'bg-danger-bg text-danger-fg' : 'bg-warning-bg text-warning-fg'}`}
                  >
                    {d.reason_code.replaceAll('_', ' ')}
                  </span>
                  <div>{d.explanation ?? d.reason_code}</div>
                  {d.repeat_skip && !d.confirmed && (
                    <label className="mt-2 block text-xs">
                      Reason for another deferral
                      <input
                        className="mt-1 block w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm"
                        value={reasons[d.id] ?? ''}
                        onChange={(e) => setReasons({ ...reasons, [d.id]: e.target.value })}
                      />
                    </label>
                  )}
                  {group === 'choice' && d.id === activeChoice && (
                    <div className="mt-1.5 flex gap-4 text-xs font-semibold">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy || plan.status !== 'draft'}
                        onClick={() => void instead(d)}
                      >
                        Serve instead
                      </Button>
                    </div>
                  )}
                  {counterfactual?.id === d.id && (
                    <div className="mt-2 rounded-md border border-line p-3">
                      <p>
                        Serve {d.outlet_code}. This displaces{' '}
                        {counterfactual.displaces.join(', ') || 'no other orders'}.
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy}
                        onClick={() => void instead(d, true)}
                      >
                        Apply replacement
                      </Button>
                    </div>
                  )}
                </div>
                <div className="w-[130px] shrink-0 text-right text-xs text-secondary">
                  Next run
                  <div className="mt-1 font-mono text-[11px] text-primary">
                    {d.next_run ? `${dayLabel(d.next_run)} · 03:30` : 'To be confirmed'}
                  </div>
                  {d.confirmed && (
                    <span className="mt-1 inline-flex items-center gap-1 text-success-fg">
                      <FigmaIcon name="check" />
                      Confirmed
                    </span>
                  )}
                </div>
              </div>
            ))}
          </section>
        )
      })}
      {preview && (
        <div className="mx-5 my-4 rounded-md border border-line px-3.5 py-3">
          <div className="flex text-[11px] font-semibold tracking-[0.66px] uppercase text-secondary">
            Store notice · preview
            <button
              className="ml-auto"
              onClick={() => setPreview(null)}
              aria-label="Close store notice"
            >
              <FigmaIcon name="close" />
            </button>
          </div>
          <p className="mt-2">
            {preview.notice_body || preview.explanation || preview.reason_code}
          </p>
          <p className="mt-2 font-mono text-[11px] text-secondary">
            Auto-written from the plan · English
          </p>
        </div>
      )}
    </div>
  )
}
