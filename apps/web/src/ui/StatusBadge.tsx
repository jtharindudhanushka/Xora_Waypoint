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

export function StatusBadge({
  status,
  label,
  variant,
}: {
  status: Status
  label?: string
  variant?: 'figma'
}) {
  const style = STYLES[status]
  return (
    <span
      className={`inline-flex items-center rounded-sm text-xs font-semibold ${variant === 'figma' ? `gap-1.5 py-[3px] pl-[7px] pr-2 leading-4 ${status === 'pending_sync' ? 'border border-dashed border-line-strong bg-surface text-secondary' : style.className}` : `gap-1 px-2 py-0.5 ${style.className}`}`}
    >
      {variant === 'figma' && <span className="size-1.5 shrink-0 rounded-[1px] bg-current" />}
      {label ?? style.label}
    </span>
  )
}
