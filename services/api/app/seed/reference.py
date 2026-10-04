"""Load reference tables from the dataset pack. Idempotent: rows are merged on natural keys."""

from __future__ import annotations

from datetime import date, time

import pandas as pd
from sqlalchemy.orm import Session

from app.modules.catalog.models import (
    CalendarDay,
    Depot,
    District,
    Outlet,
    ServiceAllowance,
    TravelRatio,
    Vehicle,
)
from app.seed.dataset import Dataset

# Where coverage drops (brief: hill country, the Kandy corridor, rural districts). Used by BR-50.
DEAD_ZONE_DISTRICTS = {"Puttalam", "Kurunegala", "Kegalle", "Nuwara Eliya", "Badulla"}
FALLBACK_RATIO = (1.5, 2.0)  # p50, p90 when training legs are not available


def _t(value: str) -> time | None:
    return time.fromisoformat(value) if value else None


def _b(value: str) -> bool:
    return value.strip() in {"1", "1.0", "true", "True"}


def load_reference(session: Session, ds: Dataset) -> dict[str, int]:
    outlets = ds.read("General Data/outlets.csv")
    vehicles = ds.read("General Data/vehicles.csv")
    districts = ds.read("General Data/district_travel.csv")

    for name in sorted(set(outlets.depot) | set(vehicles.depot) | set(districts.depot)):
        session.merge(Depot(name=name))

    for r in districts.itertuples():
        session.merge(
            District(
                name=r.district,
                depot=r.depot,
                road_class=r.road_class,
                free_flow_kmh=float(r.free_flow_kmh),
                depot_to_district_km=float(r.depot_to_district_km),
                depot_to_district_min=int(float(r.depot_to_district_freeflow_min)),
                inter_stop_km=float(r.inter_stop_km),
                inter_stop_min=int(float(r.inter_stop_freeflow_min)),
                is_dead_zone=r.road_class == "hill" or r.district in DEAD_ZONE_DISTRICTS,
            )
        )
    session.flush()

    for r in outlets.itertuples():
        mall_open, mall_close = [*r.mall_window.split("-"), ""][:2] if r.mall_window else ("", "")
        session.merge(
            Outlet(
                code=r.outlet_id,
                brand=r.brand,
                district=r.district,
                depot=r.depot,
                dock_type=r.dock_type,
                parking_constraint=r.parking_constraint,
                mall_window_open=_t(mall_open),
                mall_window_close=_t(mall_close),
                window_open=time.fromisoformat(r.window_open_time),
                window_close=time.fromisoformat(r.window_close_time),
            )
        )

    for r in vehicles.itertuples():
        session.merge(
            Vehicle(
                code=r.vehicle_id,
                type=r.type,
                temp=r.temp,
                weight_cap_kg=float(r.weight_cap_kg),
                volume_cap_m3=float(r.volume_cap_m3),
                fuel_type=r.fuel_type,
                km_per_l=float(r.km_per_l),
                weekly_fuel_quota_l=float(r.weekly_fuel_quota_l),
                depot=r.depot,
            )
        )

    for r in ds.read("General Data/service_allowance.csv").itertuples():
        session.merge(
            ServiceAllowance(
                brand=r.brand, dock_type=r.dock_type, minutes=int(float(r.service_allowance_min))
            )
        )

    calendar = ds.read("General Data/calendar.csv")
    for r in calendar.itertuples():
        session.merge(
            CalendarDay(
                date=date.fromisoformat(r.date),
                dow=int(r.dow),
                iso_year=int(r.iso_year),
                iso_week=int(r.iso_week),
                is_payday=_b(r.is_payday),
                festival=r.festival or None,
                festival_ramp=float(r.festival_ramp or 0),
                is_holiday=_b(r.is_holiday),
                monsoon=_b(r.monsoon),
                is_operating=_b(r.is_operating),
            )
        )
    session.flush()
    return {
        "districts": len(districts),
        "outlets": len(outlets),
        "vehicles": len(vehicles),
        "calendar_days": len(calendar),
    }


def load_travel_ratios(session: Session, ds: Dataset) -> int:
    """Actual ÷ planned travel time per district and planned-departure hour (BR-18).

    Computed from training legs at seed time and stored only in the database (ADR-0007).
    """
    districts = [d.name for d in session.query(District).all()]
    rows: list[TravelRatio] = []
    if ds.has("Training Data/route_legs_train.csv"):
        legs = pd.read_csv(
            ds.path("Training Data/route_legs_train.csv"),
            usecols=[
                "district",
                "planned_depart_time",
                "planned_travel_duration_min",
                "actual_travel_duration_min",
            ],
        )
        legs = legs[legs.planned_travel_duration_min > 0]
        legs["hour"] = legs.planned_depart_time.str.slice(0, 2).astype(int)
        legs["ratio"] = legs.actual_travel_duration_min / legs.planned_travel_duration_min
        grouped = legs.groupby(["district", "hour"]).ratio.quantile([0.5, 0.9]).unstack()
        for (district, hour), q in grouped.iterrows():
            rows.append(
                TravelRatio(
                    district=district,
                    hour=int(hour),
                    p50_ratio=round(float(q[0.5]), 3),
                    p90_ratio=round(float(q[0.9]), 3),
                )
            )
    else:
        for district in districts:
            for hour in range(24):
                rows.append(
                    TravelRatio(
                        district=district,
                        hour=hour,
                        p50_ratio=FALLBACK_RATIO[0],
                        p90_ratio=FALLBACK_RATIO[1],
                    )
                )
    for row in rows:
        session.merge(row)
    session.flush()
    return len(rows)
