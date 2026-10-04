import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Button } from '../../../ui/Button'
import { FigmaIcon } from '../../../ui/FigmaIcon'
import { dayLabel } from '../planning/format'
import { useIssue, useResolve, type Decision, type Issue } from './api'

const time = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleTimeString('en-GB', {
        timeZone: 'Asia/Colombo',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'
const clock = (value: string) => value.slice(0, 5)

function Photo({ url, label }: { url: string | null; label: string }) {
  return url ? (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      aria-label={label}
      className="flex h-[72px] w-24 shrink-0 items-center justify-center overflow-hidden rounded-sm bg-sunken"
    >
      <img src={url} alt={label} className="h-full w-full object-cover" />
    </a>
  ) : (
    <div
      aria-label={`${label}: no photo`}
      className="flex h-[72px] w-24 shrink-0 items-center justify-center rounded-sm bg-sunken"
    >
      <FigmaIcon name="camera" />
    </div>
  )
}

function StoreEvidence({ issue }: { issue: Issue }) {
  const affected = issue.items.filter((i) => i.problem)
  const confirmed = issue.items.filter((i) => !i.problem)
  const rows = [
    ...affected.map((i) => ({
      name: i.name,
      qty: i.driver_qty,
      report: `${i.problem_qty} ${i.problem?.replaceAll('_', ' ')}`,
      tone: i.problem === 'missing' ? 'bg-warning-bg' : 'bg-danger-bg',
      text: i.problem === 'missing' ? 'text-warning-fg' : 'text-danger-fg',
    })),
    ...(confirmed.length
      ? [
          {
            name: `Other ${confirmed.length} items`,
            qty: confirmed.every((i) => i.driver_qty !== null)
              ? confirmed.reduce((sum, i) => sum + (i.driver_qty ?? 0), 0)
              : null,
            report: 'Confirmed',
            tone: '',
            text: 'text-success-fg',
          },
        ]
      : []),
  ]
  return (
    <>
      <div className="flex border-b border-line px-6 py-3.5 text-[11px] leading-[14px] font-semibold tracking-[0.66px] text-secondary uppercase">
        <span className="w-[260px] shrink-0">Item</span>
        <span className="w-[200px] shrink-0">Driver handed over</span>
        <span>Store reports</span>
      </div>
      {rows.map((row, i) => (
        <div key={i} className={`flex items-center border-b border-line px-6 py-4 ${row.tone}`}>
          <p className="w-[260px] shrink-0 text-base leading-5 font-semibold">{row.name}</p>
          <p className="w-[200px] shrink-0 font-mono text-[13px] leading-[18px]">
            {row.qty ?? '—'} cases
          </p>
          <p className={`text-base leading-5 font-semibold ${row.text}`}>{row.report}</p>
        </div>
      ))}
      <div className="flex gap-6 px-6 py-5">
        <div className="flex flex-1 items-center gap-3">
          <Photo url={issue.driver_photo_url} label="Driver handover photo" />
          <div>
            <p className="text-sm leading-[18px] font-semibold">Driver handover photo</p>
            <p className="mt-0.5 text-xs leading-4 text-secondary">
              {time(issue.driver_recorded_at)} · {issue.driver_record_id?.slice(0, 8) ?? '—'}
            </p>
          </div>
        </div>
        <div className="flex flex-1 items-center gap-3">
          <Photo url={issue.store_photo_url} label="Store photo" />
          <div>
            <p className="text-sm leading-[18px] font-semibold">Store photo</p>
            <p className="mt-0.5 text-xs leading-4 text-secondary">
              {time(issue.opened_at)}
              {issue.note && ` · ${issue.note}`}
            </p>
          </div>
        </div>
      </div>
    </>
  )
}

function CountEvidence({ issue }: { issue: Issue }) {
  return (
    <>
      <div className="flex border-b border-line px-6 py-3.5 text-[11px] leading-[14px] font-semibold tracking-[0.66px] text-secondary uppercase">
        <span className="w-[200px] shrink-0" />
        <p className="flex-1">Driver’s phone · {issue.driver_record_id?.slice(0, 8) ?? '—'}</p>
        <p className="flex-1">Store counter</p>
      </div>
      <div className="flex items-center border-b border-line bg-warning-bg px-6 py-4">
        <p className="w-[200px] shrink-0 text-sm leading-5 text-secondary">Cases</p>
        <p className="flex-1 font-mono text-xl leading-6 tracking-[-0.4px]">
          {issue.driver_qty ?? '—'}
        </p>
        <p className="flex-1 font-mono text-xl leading-6 tracking-[-0.4px] text-warning-fg">
          {issue.store_qty ?? '—'}
        </p>
      </div>
      {[
        [
          'Recorded at',
          `${time(issue.driver_recorded_at)} (uploaded ${time(issue.driver_uploaded_at)})`,
          time(issue.store_recorded_at),
        ],
        ['By', `Driver · ${issue.vehicle_code ?? '—'}`, `${issue.store_name ?? '—'} · store`],
        ['Evidence', 'Photo at handover', 'Shelf count'],
      ].map(([label, driver, store]) => (
        <div key={label} className="flex items-center border-b border-line px-6 py-4">
          <p className="w-[200px] shrink-0 text-sm leading-5 text-secondary">{label}</p>
          <p className="flex-1 text-sm leading-[18px] font-semibold">{driver}</p>
          <p className="flex-1 text-sm leading-[18px] font-semibold">{store}</p>
        </div>
      ))}
      <div className="flex items-center gap-3 px-6 py-4">
        <Photo url={issue.driver_photo_url} label="Photo at handover" />
        <p className="text-sm leading-5 text-secondary">
          Both records are kept. Nothing is overwritten.
        </p>
      </div>
    </>
  )
}

export function IssueWorkspace() {
  const { id = '' } = useParams()
  const query = useIssue(id)
  if (!query.data)
    return (
      <p className="p-6" role={query.error ? 'alert' : undefined}>
        {query.error?.message ?? 'Loading issue…'}
      </p>
    )
  return <IssueDecision key={id} issue={query.data} />
}

function IssueDecision({ issue }: { issue: Issue }) {
  const count = issue.kind === 'count_conflict'
  const action = useResolve(issue.id)
  const [resolution, setResolution] = useState<Decision['resolution']>(
    count ? 'store_stands' : 'redeliver',
  )
  const [note, setNote] = useState(issue.note ?? '')
  const choices: [Decision['resolution'], string, string][] = count
    ? [
        [
          'driver_stands',
          'Driver’s count stands',
          `${issue.driver_qty ?? '—'} delivered · store checks stock room`,
        ],
        [
          'store_stands',
          'Store count stands',
          `${issue.store_qty ?? '—'} delivered · opens a ${Math.max(0, (issue.driver_qty ?? 0) - (issue.store_qty ?? 0))}-case short claim`,
        ],
        ['recount', 'Ask for a recount', `Store recounts by ${time(issue.recount_due)}`],
      ]
    : [
        [
          'redeliver',
          'Redeliver on the next run',
          `${issue.affected_cases} cases on ${issue.next_run ? dayLabel(issue.next_run) : 'the next operating run'} · ${clock(issue.window_open)}–${clock(issue.window_close)}`,
        ],
        [
          'credit',
          'Credit the store',
          `Value of ${issue.affected_cases} cases credited · no redelivery`,
        ],
        ['reject', 'Reject with a reason', 'Store is told why'],
      ]
  const resolved = issue.status === 'resolved'
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-surface">
      <div className="flex items-center gap-4 border-b border-line px-6 py-5">
        <div className="flex-1">
          <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.11px]">
            {count
              ? `Two counts for ${issue.outlet_code}`
              : `Store report · ${issue.outlet_code} ${issue.district}`}
          </h1>
          <p
            className={`mt-0.5 text-secondary ${count ? 'font-mono text-[11px] leading-[14px] tracking-[0.22px]' : 'text-sm leading-[18px] font-semibold'}`}
          >
            {issue.order_ref} · {issue.temp_requirement} ·{' '}
            {count
              ? `${issue.vehicle_code ?? '—'} · ${issue.district}`
              : `delivered ${time(issue.driver_recorded_at)} by ${issue.vehicle_code ?? '—'} · reported ${time(issue.opened_at)}`}
          </p>
        </div>
        <span className="rounded-sm bg-warning-bg px-1.5 py-[3px] font-mono text-[11px] leading-[14px] tracking-[0.22px] text-warning-fg uppercase">
          {resolved ? 'Decision recorded' : 'Needs decision'}
        </span>
      </div>
      <div className="flex min-h-0 flex-1">
        <section className="min-w-0 flex-1 overflow-auto">
          {count ? <CountEvidence issue={issue} /> : <StoreEvidence issue={issue} />}
        </section>
        <section className="flex w-[460px] shrink-0 flex-col border-l border-line">
          <h2 className="px-6 pt-4 pb-2 text-[11px] leading-[14px] font-semibold tracking-[0.66px] text-secondary uppercase">
            Your decision
          </h2>
          <div role="radiogroup" aria-label="Your decision">
            {choices.map(([value, label, detail]) => (
              <label
                key={value}
                className={`flex cursor-pointer items-center gap-3 border-b px-6 py-3.5 ${resolution === value ? 'border-brand border-l-4 bg-brand-subtle' : 'border-line'}`}
              >
                <input
                  type="radio"
                  name="decision"
                  value={value}
                  checked={resolution === value}
                  onChange={() => setResolution(value)}
                  disabled={resolved || (value === 'redeliver' && !issue.next_run)}
                  className="peer sr-only"
                />
                <span
                  className={`flex size-5 shrink-0 items-center justify-center rounded-full border-2 peer-focus-visible:outline-2 peer-focus-visible:outline-brand ${resolution === value ? 'border-brand' : 'border-line-strong'}`}
                >
                  {resolution === value && <span className="size-2.5 rounded-full bg-brand" />}
                </span>
                <span>
                  <span className="block text-base leading-5 font-semibold">{label}</span>
                  <span className="mt-0.5 block text-xs leading-4 text-secondary">{detail}</span>
                </span>
              </label>
            ))}
          </div>
          {!count && (
            <div className="flex items-start gap-2 px-6 py-4">
              <FigmaIcon name="issueInfo" />
              <p className="text-xs leading-4 text-secondary">
                The store and driver both get the decision. The loading team receives the
                damaged-stock note.
              </p>
            </div>
          )}
          {(count || resolution === 'reject') && (
            <label className="flex flex-col gap-1.5 px-6 py-4">
              <span className="text-sm leading-[18px] font-semibold">
                {count ? 'Note (sent to driver and store)' : 'Reason (sent to driver and store)'}
              </span>
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                disabled={resolved}
                maxLength={2000}
                className="h-12 rounded-md border border-line-strong bg-surface px-3 text-base leading-6 outline-brand"
              />
              <span className="text-xs leading-4 text-secondary">
                {count ? 'Optional' : 'Required'}
              </span>
            </label>
          )}
          {action.error && (
            <p role="alert" className="px-6 py-3 text-danger-fg">
              {action.error.message}
            </p>
          )}
          {resolved && (
            <p role="status" className="px-6 py-3 text-success-fg">
              Decision recorded · {issue.resolution?.replaceAll('_', ' ')}
              <br />
              <Link to="/dispatch/ops" className="underline">
                Back to live ops
              </Link>
            </p>
          )}
          <div className="mt-auto border-t border-line px-6 py-4">
            <Button
              variant="secondary"
              size="sm"
              className="w-full"
              disabled={
                resolved ||
                action.isPending ||
                (resolution === 'reject' && !note.trim()) ||
                (resolution === 'redeliver' && !issue.next_run)
              }
              onClick={() => action.mutate({ resolution, note: note || null })}
            >
              Record decision <FigmaIcon name="arrow" />
            </Button>
          </div>
        </section>
      </div>
    </div>
  )
}
