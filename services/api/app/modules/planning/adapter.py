"""DB ↔ engine boundary; the engine never imports API or persistence code."""

from datetime import date, time

from xora_engine import Assignment, District, Order, Problem, Stop, Trip, Vehicle

from app.modules.planning.models import PlanVersion
from app.modules.planning.repository import Repository


def minute(value: time | None) -> int:
    return value.hour * 60 + value.minute if value else 0


def as_time(value: int) -> time:
    return time((value // 60) % 24, value % 60)


def load_problem(
    repo: Repository, version: PlanVersion | None = None, *, operating_date: date | None = None
) -> Problem:
    if version is not None:
        operating_date = version.plan.operating_date
    assert operating_date is not None
    outlets = {o.code: o for o in repo.outlets()}
    orders: dict[str, Order] = {}
    for row in repo.orders(operating_date):
        outlet = outlets[row.outlet_code]
        orders[row.ref] = Order(
            row.ref,
            row.outlet_code,
            row.brand,
            outlet.district,
            outlet.depot,
            row.temp_requirement,
            outlet.dock_type,
            outlet.parking_constraint,
            row.units,
            float(row.weight_kg),
            float(row.volume_m3),
            minute(outlet.window_open),
            minute(outlet.window_close),
            minute(outlet.mall_window_open) if outlet.mall_window_open else None,
            minute(outlet.mall_window_close) if outlet.mall_window_close else None,
            row.deferred_yesterday,
            row.days_since_last_served,
        )
    vehicles = {
        v.code: Vehicle(
            v.code,
            v.type,
            v.temp,
            float(v.weight_cap_kg),
            float(v.volume_cap_m3),
            v.depot,
            float(v.km_per_l),
            max(0, float(v.weekly_fuel_quota_l) - used),
            day.switched_on,
            day.status,
        )
        for v, day, used in repo.fleet(operating_date)
    }
    districts = {
        d.name: District(
            d.name,
            d.depot_to_district_min,
            d.inter_stop_min,
            float(d.depot_to_district_km),
            float(d.inter_stop_km),
        )
        for d in repo.districts()
    }
    from app.modules.catalog.models import CalendarDay

    calendar = repo.db.get(CalendarDay, operating_date)
    return Problem(
        orders,
        vehicles,
        districts,
        {(a.brand, a.dock_type): a.minutes for a in repo.allowances()},
        float(calendar.festival_ramp) if calendar else 0,
        {(r.district, r.hour): (float(r.p50_ratio), float(r.p90_ratio)) for r in repo.ratios()},
    )


def load_assignment(version: PlanVersion, repo: Repository) -> Assignment:
    by_id = {o.id: o.ref for o in repo.orders(version.plan.operating_date)}
    return Assignment(
        tuple(
            Trip(
                t.vehicle_code,
                t.trip_no,
                tuple(
                    Stop(by_id[so.order_id], so.planned_cases, minute(s.plan_arrival))
                    for s in t.stops
                    for so in s.orders
                ),
                minute(t.planned_depart),
                t.plan_minutes,
                t.locked,
            )
            for t in version.trips
        )
    )
