import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useSession } from '../../auth/useSession'
import { enqueue, hhmm, isPending, type OutboxEvent, useOutbox } from '../field/outbox'
import { Caption, FieldButton, FieldHeader, Icon, KeyValue, SyncBar } from '../field/ui'
import { recordRef, useVehicleToday } from './data'
import { findStop, stopSubtitle } from './StopPage'
import { Message, reviewLink } from './TripPage'

type OrderLine = { order_ref?: string; cases?: number }

function summary(event: OutboxEvent) {
  const p = event.payload as {
    outcome?: string
    receiver_name?: string | null
    orders?: OrderLine[]
  }
  const total = (p.orders ?? []).reduce((sum, o) => sum + (o.cases ?? 0), 0)
  const outcome = p.outcome ? p.outcome[0]!.toUpperCase() + p.outcome.slice(1) : event.type
  return { total, outcome, receiver: p.receiver_name ?? '—' }
}

/**
 * R4 Saved on this device · R5 Record uploaded · R7 Needs review (Figma 145:172, 145:259, 145:348).
 * The device time is kept as the time that counts (BR-37); conflicts never overwrite (BR-52).
 */
export function RecordPage() {
  const { eventId } = useParams()
  const events = useOutbox()
  const { data: day } = useVehicleToday()
  const event = events.find((e) => e.event_id === eventId)
  if (!event) return <Message text="Record not found on this phone." />
  const found = findStop(day, event.entity.id)
  const title = found
    ? `Stop ${found.stop.seq} of ${found.trip.stops.length} · ${found.stop.outlet_code}`
    : recordRef(event.event_id)
  const subtitle = found && day ? stopSubtitle(day, found.trip) : ''
  return (
    <div className="flex flex-1 flex-col">
      <FieldHeader title={title} subtitle={subtitle} back="/driver" />
      <SyncBar events={events} reviewTo={reviewLink} />
      {event.status === 'conflict' || event.status === 'rejected' ? (
        <NeedsReview event={event} />
      ) : (
        <Saved event={event} />
      )}
    </div>
  )
}

function Saved({ event }: { event: OutboxEvent }) {
  const navigate = useNavigate()
  const pending = isPending(event)
  const s = summary(event)
  return (
    <>
      <Hero
        eyebrow={pending ? 'Saved on this phone' : 'Uploaded'}
        eyebrowTone="text-brand-text"
        title="Delivery recorded"
        body={
          pending
            ? 'Safe on this phone. It uploads by itself when there’s signal.'
            : 'Dispatch and the store can see it now.'
        }
      />
      <Caption>Where your record is</Caption>
      <div className="flex w-full flex-col border-y border-line bg-surface py-1">
        <Step
          done
          title="Saved on this phone"
          detail={`${hhmm(event.event_time)} · this time is kept`}
        />
        <Step
          done={!pending}
          current={pending}
          title="Upload"
          detail={pending ? 'Waiting for signal' : `Uploaded ${hhmm(event.uploaded_at)}`}
        />
        <Step
          done={!pending}
          title="Dispatch and store see it"
          detail={pending ? 'After upload' : 'Done'}
        />
      </div>
      <Caption meta={recordRef(event.event_id)}>Record</Caption>
      <KeyValue label="Outcome" value={`${s.outcome} · ${s.total} cases`} />
      <KeyValue label="Received by" value={s.receiver} />
      <div className="flex-1" />
      <div className="w-full px-4 py-3">
        <FieldButton className="w-full" onClick={() => navigate('/driver')}>
          Back to trip
        </FieldButton>
      </div>
    </>
  )
}

function Step({
  done,
  current,
  title,
  detail,
}: {
  done?: boolean
  current?: boolean
  title: string
  detail: string
}) {
  return (
    <div className="flex w-full items-center gap-3 px-4 py-[10px]">
      {done ? (
        <span className="flex size-6 items-center justify-center rounded-xl bg-success-fg">
          <Icon name="checkWhite" />
        </span>
      ) : current ? (
        <span className="size-6 rounded-xl border-2 border-brand" />
      ) : (
        <span className="size-6 rounded-xl border-2 border-dashed border-line-strong" />
      )}
      <div className={`flex min-w-0 flex-1 flex-col ${done || current ? '' : 'text-secondary'}`}>
        <p
          className={`text-sm font-semibold leading-[18px] ${done || current ? 'text-primary' : ''}`}
        >
          {title}
        </p>
        <p className="font-mono text-[11px] font-medium leading-[14px] tracking-[0.22px] text-secondary">
          {detail}
        </p>
      </div>
    </div>
  )
}

function Hero({
  eyebrow,
  eyebrowTone,
  title,
  body,
}: {
  eyebrow: string
  eyebrowTone: string
  title: string
  body: string
}) {
  return (
    <div className="flex w-full flex-col gap-1.5 border-b border-line bg-surface px-4 pb-4 pt-5">
      <p
        className={`text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] ${eyebrowTone}`}
      >
        {eyebrow}
      </p>
      <p className="text-[28px] font-semibold leading-[34px] tracking-[-0.28px] text-primary">
        {title}
      </p>
      <p className="text-base leading-6 text-secondary">{body}</p>
    </div>
  )
}

function NeedsReview({ event }: { event: OutboxEvent }) {
  const session = useSession()
  const [note, setNote] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const s = summary(event)
  const r = event.result
  const rows: [string, string, string][] =
    event.status === 'conflict'
      ? [
          [
            'Cases',
            String(r?.driver_qty ?? s.total),
            r?.store_qty != null ? String(r.store_qty) : '—',
          ],
          ['Time', hhmm(event.event_time), hhmm(r?.store_time)],
          [
            'Evidence',
            (event.payload as { photo_taken_at?: string | null }).photo_taken_at
              ? `Photo ${recordRef(event.event_id)}`
              : `Record ${recordRef(event.event_id)}`,
            'Shelf count',
          ],
        ]
      : [['Reason', r?.detail ?? '', r?.rule_id ?? '']]
  return (
    <>
      {event.status === 'conflict' ? (
        <Hero
          eyebrow="Nothing is lost"
          eyebrowTone="text-warning-fg"
          title="Your record is kept"
          body="Your count and the store’s differ. Nothing is overwritten; dispatch decides."
        />
      ) : (
        <Hero
          eyebrow="Not uploaded"
          eyebrowTone="text-warning-fg"
          title="This record needs attention"
          body={r?.detail ?? 'The server could not accept this record.'}
        />
      )}
      <Caption>What doesn’t match</Caption>
      <div className="flex w-full flex-col border-y border-line bg-surface">
        <div className="flex w-full items-start border-b border-line px-4 py-[10px]">
          <span className="w-24 shrink-0" />
          <p className="flex-1 text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] text-secondary">
            Your phone
          </p>
          <p className="flex-1 text-[11px] font-semibold uppercase leading-[14px] tracking-[0.66px] text-secondary">
            Store counter
          </p>
        </div>
        {rows.map(([label, mine, theirs], i) => (
          <div key={label} className="flex w-full items-start border-b border-line px-4 py-[10px]">
            <p className="w-24 shrink-0 text-sm leading-5 text-secondary">{label}</p>
            <p className="flex-1 text-sm font-semibold leading-[18px] text-primary">{mine}</p>
            <p
              className={`flex-1 text-sm font-semibold leading-[18px] ${i === 0 ? 'text-warning-fg' : 'text-primary'}`}
            >
              {theirs}
            </p>
          </div>
        ))}
      </div>
      <KeyValue label="Decided by" value={`Dispatcher · ${session?.user?.depot ?? ''}`} />
      {note !== null && !sent && (
        <div className="w-full px-4 pt-3">
          <textarea
            aria-label="Note for dispatch"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="h-24 w-full rounded-md border border-line-strong bg-surface p-3 text-base leading-6 text-primary"
          />
        </div>
      )}
      {sent && (
        <p className="px-4 pt-3 text-sm leading-5 text-secondary">Note saved for dispatch.</p>
      )}
      <div className="flex-1" />
      <div className="w-full px-4 py-3">
        {note === null ? (
          <FieldButton className="w-full" onClick={() => setNote('')}>
            Add a note for dispatch
          </FieldButton>
        ) : (
          <FieldButton
            className="w-full"
            disabled={!note.trim() || sent}
            onClick={() =>
              void enqueue('note_added', event.entity, event.plan_version_id ?? null, {
                note,
                about_event_id: event.event_id,
              }).then(() => setSent(true))
            }
          >
            Send note
          </FieldButton>
        )}
      </div>
    </>
  )
}

/** Uploads tab: every record on this phone and where it is. */
export function UploadsPage() {
  const events = useOutbox()
  const records = events.filter(
    (e) => e.type === 'outcome_recorded' || e.status === 'conflict' || e.status === 'rejected',
  )
  const label = (e: OutboxEvent) =>
    isPending(e)
      ? 'Saved on this phone'
      : e.status === 'conflict' || e.status === 'rejected'
        ? 'Needs review'
        : 'Uploaded'
  return (
    <div className="flex flex-1 flex-col">
      <FieldHeader
        title="Uploads"
        subtitle={`${events.filter(isPending).length} waiting · ${events.length} on this phone`}
      />
      <SyncBar events={events} reviewTo={reviewLink} />
      <Caption>Records</Caption>
      {records.length === 0 && <Message text="Nothing recorded yet." />}
      {[...records].reverse().map((e) => {
        const s = summary(e)
        return (
          <Link
            key={e.event_id}
            to={reviewLink(e)}
            className="flex w-full items-center gap-3 border-b border-line bg-surface px-4 py-3"
          >
            <div className="flex min-w-0 flex-1 flex-col">
              <p className="text-sm font-semibold leading-[18px] text-primary">
                {recordRef(e.event_id)} · {s.outcome} · {s.total} cases
              </p>
              <p className="font-mono text-[11px] font-medium leading-[14px] tracking-[0.22px] text-secondary">
                {hhmm(e.event_time)} · {label(e)}
              </p>
            </div>
          </Link>
        )
      })}
    </div>
  )
}
