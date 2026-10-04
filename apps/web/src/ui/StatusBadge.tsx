/** One status vocabulary everywhere (BR-54). Colour is never the only signal: text is always shown. */
export type Status =
  | 'planned'
  | 'loaded'
  | 'in_transit'
  | 'delivered'
  | 'at_risk'
  | 'late'
  | 'deferred'
  | 'pending_sync'
  | 'on_hold'
  | 'available'
  | 'workshop'
  | 'switched_off'

const STYLES: Record<Status, { label: string; className: string }> = {
  planned: { label: 'Planned', className: 'bg-neutral-bg text-neutral-fg' },
  loaded: { label: 'Loaded', className: 'bg-info-bg text-info-fg' },
  in_transit: { label: 'In transit', className: 'bg-brand-subtle text-brand-text' },
  delivered: { label: 'Delivered', className: 'bg-success-bg text-success-fg' },
  at_risk: { label: 'At risk', className: 'bg-warning-bg text-warning-fg' },
  late: { label: 'Late', className: 'bg-danger-bg text-danger-fg' },
  deferred: { label: 'Deferred', className: 'bg-inverse text-on-inverse' },
  pending_sync: { label: 'Pending sync', className: 'bg-neutral-bg text-neutral-fg' },
  on_hold: { label: 'On hold', className: 'bg-danger-bg text-danger-fg' },
  available: { label: 'Available', className: 'bg-success-bg text-success-fg' },
  workshop: { label: 'Workshop', className: 'bg-warning-bg text-warning-fg' },
  switched_off: { label: 'Switched off', className: 'bg-neutral-bg text-neutral-fg' },
}

export function StatusBadge({ status, label }: { status: Status; label?: string }) {
  const style = STYLES[status]
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-semibold ${style.className}`}
    >
      {label ?? style.label}
    </span>
  )
}
