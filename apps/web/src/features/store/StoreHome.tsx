import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { setSession } from '../../auth/session'
import { StatusBadge } from '../../ui/StatusBadge'
import { dayLabel, hm, remaining, useNotices, useStoreHome, type Order, type Track } from './api'
import { StoreAction, StoreHeader, StoreIcon, StoreNav, StoreState } from './StoreShell'

function Delivery({ order }: { order: Order }) {
  const track = order.tracking[0]
  const status = track?.status ?? order.status
  const position = ['planned', 'loaded', 'in_transit', 'delivered'].indexOf(status)
  return (
    <section className="store-delivery">
      <div className="store-delivery-head">
        <span className="store-caption">
          Next delivery · {order.temp_requirement === 'chilled' ? 'chilled' : 'dry'}
        </span>
        <span className={`store-status ${status}`}>
          <StatusBadge status={status} />
        </span>
      </div>
      <h2>
        {status === 'delivered'
          ? `Delivered ${hm(track?.event_time)}`
          : track?.likely_from && track.likely_to
            ? `Arriving ${hm(track.likely_from)}–${hm(track.likely_to)}`
            : 'Awaiting delivery window'}
      </h2>
      <p className="details">
        {track?.planned_cases ?? order.units} cases
        {track
          ? ` · ${track.vehicle_code} · you are stop ${track.stop_seq} of ${track.stop_count}`
          : ` · ${order.ref}`}
      </p>
      <div className="store-progress">
        {['Planned', 'Loaded', 'On the way', 'Delivered'].map((label, i) => (
          <span key={label} className={i < position ? 'done' : i === position ? 'current' : ''}>
            {label}
          </span>
        ))}
      </div>
      <p className="store-basis">
        <StoreIcon name="info" />
        Based on past runs{track?.received_at ? ` · updated ${hm(track.received_at)}` : ''}
      </p>
      {(order.status === 'delivered' || track) && !order.receipt_confirmed && (
        <Link
          className="mt-3 inline-block font-semibold text-brand-text"
          to={`/store/orders/${order.ref}/receipt`}
        >
          Confirm what arrived
        </Link>
      )}
    </section>
  )
}
export function StoreHome() {
  const home = useStoreHome()
  const notices = useNotices()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  if (home.isPending)
    return (
      <>
        <StoreHeader title="Home" subtitle="Waypoint" back={false} />
        <StoreState loading />
        <StoreNav />
      </>
    )
  if (!home.data)
    return (
      <>
        <StoreHeader title="Home" subtitle="Waypoint" back={false} />
        <StoreState error={home.error} retry={() => void home.refetch()} />
        <StoreNav />
      </>
    )
  const data = home.data
  const today = data.now.slice(0, 10)
  const upcoming = data.orders.filter(
    (o) => o.delivery_date >= today && o.submission_status !== 'draft',
  )
  const primary = upcoming.find((o) => o.temp_requirement === 'chilled') ?? upcoming[0]
  const additional: { order: Order; track?: Track }[] = upcoming.flatMap((order) =>
    order === primary
      ? order.tracking.slice(1).map((track) => ({ order, track }))
      : order.tracking.length
        ? order.tracking.map((track) => ({ order, track }))
        : [{ order }],
  )
  const recent = data.orders.filter((o) => o.delivery_date < today)
  const recentGroups = Object.entries(
    recent.reduce<Record<string, Order[]>>((groups, order) => {
      ;(groups[order.delivery_date] ??= []).push(order)
      return groups
    }, {}),
  )
  const notice = notices.data?.find((n) => n.kind === 'deferral' && !n.acked_at)
  const view = params.get('view')
  return (
    <>
      <StoreHeader
        title={`${data.outlet_code} · ${data.district}`}
        subtitle={`Waypoint ${data.brand} · ${dayLabel(today)}`}
        back={false}
      />
      <main className="store-body">
        {view === 'account' ? (
          <section className="store-row">
            <h2>Account</h2>
            <p>
              {data.outlet_code} · {data.brand}
            </p>
            <StoreAction
              onClick={() => {
                setSession(null)
                navigate('/login')
              }}
            >
              Sign out
            </StoreAction>
          </section>
        ) : (
          <>
            {notice && (
              <Link className="store-cutoff" to={`/store/notices/${notice.id}`}>
                <StoreIcon name="alert" />
                <strong>
                  Delivery update · {notice.order_ref ?? 'Your order'}
                  <br />
                  {notice.title}
                </strong>
              </Link>
            )}
            {primary ? <Delivery order={primary} /> : <StoreState />}
            {additional.map(({ order: o, track }) => (
              <Link
                className="store-row store-dry"
                key={`${o.ref}-${track?.stop_id ?? 'unplanned'}`}
                to={
                  o.status === 'delivered' ? `/store/orders/${o.ref}/receipt` : '/store?view=orders'
                }
              >
                <StoreIcon name="package" />
                <div>
                  <h3>
                    {o.temp_requirement === 'chilled' ? 'Chilled' : 'Dry'} order · {o.ref}
                  </h3>
                  <p className="store-small">
                    {track?.planned_cases ?? o.units} cases
                    {track
                      ? ` · van ${track.vehicle_code} · ${hm(track.likely_from)}–${hm(track.likely_to)}`
                      : ' · awaiting plan'}
                  </p>
                </div>
                <span className={`store-status ${track?.status ?? o.status}`}>
                  <StatusBadge status={track?.status ?? o.status} />
                </span>
              </Link>
            ))}
            {data.driver_note && (
              <section className="store-note">
                <StoreIcon name="pin" />
                <div>
                  <span className="store-caption">Note for today’s driver</span>
                  <p>{data.driver_note.text}</p>
                  <span className="store-small">
                    Sent {hm(data.driver_note.sent_at)}
                    {primary?.tracking[0] ? ` · ${primary.tracking[0].vehicle_code} has it` : ''}
                  </span>
                </div>
              </section>
            )}
            <section className="store-cutoff">
              <StoreIcon name="clock" />
              <div>
                <strong>
                  {data.ordering.after_cutoff
                    ? `Orders closed · next delivery ${dayLabel(data.ordering.delivery_date)}`
                    : `Orders for ${dayLabel(data.ordering.delivery_date)} close at 16:00`}
                </strong>
                <p className="store-mono">{remaining(data.ordering.cutoff_seconds)}</p>
              </div>
            </section>
            <div className="store-section">
              <h2 className="store-caption">Recent</h2>
            </div>
            {recentGroups.length ? (
              recentGroups.map(([date, group]) => (
                <Link
                  className="store-row store-recent"
                  to={`/store/orders/${group![0]!.ref}/receipt`}
                  key={date}
                >
                  <div>
                    <strong>
                      {dayLabel(date)} · {group!.length} orders
                    </strong>
                    <p>
                      {group!.reduce((total, o) => total + o.units, 0)} cases ·{' '}
                      {group!.every((o) => o.receipt_confirmed)
                        ? `receipt confirmed${group![0]!.receipt_confirmed_at ? ` ${hm(group![0]!.receipt_confirmed_at)}` : ''}`
                        : 'receipt pending'}
                    </p>
                  </div>
                  <span className={`store-status ${group![0]!.status}`}>
                    <StatusBadge status={group![0]!.status} />
                  </span>
                </Link>
              ))
            ) : (
              <p className="store-row store-small">No recent deliveries</p>
            )}
            {view === 'orders' &&
              data.orders
                .filter((o) => o.submission_status === 'draft')
                .map((o) => (
                  <Link className="store-row" key={o.ref} to="/store/orders/new">
                    {o.ref} · Draft · {o.units} cases
                  </Link>
                ))}
            {view === 'issues' && (
              <p className="store-row store-small">
                Open a delivered order to report a problem. Dispatch decisions appear in delivery
                updates.
              </p>
            )}
          </>
        )}
        <footer className="store-footer">
          <StoreAction onClick={() => navigate('/store/orders/new')}>
            New order for {dayLabel(data.ordering.delivery_date)} <StoreIcon name="arrow" />
          </StoreAction>
        </footer>
      </main>
      <StoreNav />
    </>
  )
}
