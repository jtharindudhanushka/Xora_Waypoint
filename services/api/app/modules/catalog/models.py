"""Reference data loaded from the organisers' dataset pack, plus our own demo fixtures.

Natural business keys (OUT001, VEH036, district names) are primary keys: they are stable,
unique in the dataset and are what every screen and rule refers to (docs/04-data-model.md).
"""

from __future__ import annotations

from datetime import date, time

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

BRANDS = ("Fresh", "Style", "Tech")
DOCK_TYPES = ("rear_dock", "street", "mall_bay")
PARKING = ("normal", "van_only", "mall_dock")


def _enum(*values: str, name: str) -> Enum:
    return Enum(*values, name=name, native_enum=False, validate_strings=True)


class Depot(Base):
    __tablename__ = "depots"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)


class District(Base):
    __tablename__ = "districts"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    depot: Mapped[str] = mapped_column(ForeignKey("depots.name"))
    road_class: Mapped[str] = mapped_column(String(20))
    free_flow_kmh: Mapped[float] = mapped_column(Numeric(6, 2))
    depot_to_district_km: Mapped[float] = mapped_column(Numeric(7, 2))
    depot_to_district_min: Mapped[int] = mapped_column(Integer)
    inter_stop_km: Mapped[float] = mapped_column(Numeric(6, 2))
    inter_stop_min: Mapped[int] = mapped_column(Integer)
    is_dead_zone: Mapped[bool] = mapped_column(default=False)  # BR-50


class Outlet(Base):
    __tablename__ = "outlets"
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    brand: Mapped[str] = mapped_column(_enum(*BRANDS, name="brand"))
    district: Mapped[str] = mapped_column(ForeignKey("districts.name"))
    depot: Mapped[str] = mapped_column(ForeignKey("depots.name"))
    dock_type: Mapped[str] = mapped_column(_enum(*DOCK_TYPES, name="dock_type"))
    parking_constraint: Mapped[str] = mapped_column(_enum(*PARKING, name="parking_constraint"))
    mall_window_open: Mapped[time | None]
    mall_window_close: Mapped[time | None]
    window_open: Mapped[time]
    window_close: Mapped[time]


class OutletProfile(Base):
    """Our own demo fields (not in the dataset): store rules and preferences (BR-29, BR-44)."""

    __tablename__ = "outlet_profiles"
    outlet_code: Mapped[str] = mapped_column(ForeignKey("outlets.code"), primary_key=True)
    split_rule: Mapped[str] = mapped_column(
        _enum("same_morning_only", "any", "never", name="split_rule"), default="any"
    )
    language: Mapped[str] = mapped_column(_enum("si", "ta", "en", name="language"), default="en")
    contact_name: Mapped[str | None] = mapped_column(String(80))
    access_note: Mapped[str | None] = mapped_column(String(240))


class Vehicle(Base):
    __tablename__ = "vehicles"
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    type: Mapped[str] = mapped_column(_enum("truck", "van", name="vehicle_type"))
    temp: Mapped[str] = mapped_column(_enum("reefer", "ambient", name="vehicle_temp"))
    weight_cap_kg: Mapped[float] = mapped_column(Numeric(9, 2))
    volume_cap_m3: Mapped[float] = mapped_column(Numeric(7, 2))
    fuel_type: Mapped[str] = mapped_column(String(20))
    km_per_l: Mapped[float] = mapped_column(Numeric(5, 2))
    weekly_fuel_quota_l: Mapped[float] = mapped_column(Numeric(8, 2))
    depot: Mapped[str] = mapped_column(ForeignKey("depots.name"))


class ServiceAllowance(Base):
    __tablename__ = "service_allowances"
    brand: Mapped[str] = mapped_column(_enum(*BRANDS, name="brand"), primary_key=True)
    dock_type: Mapped[str] = mapped_column(_enum(*DOCK_TYPES, name="dock_type"), primary_key=True)
    minutes: Mapped[int] = mapped_column(Integer)


class CalendarDay(Base):
    __tablename__ = "calendar_days"
    date: Mapped[date] = mapped_column(primary_key=True)
    dow: Mapped[int] = mapped_column(Integer)
    iso_year: Mapped[int] = mapped_column(Integer)
    iso_week: Mapped[int] = mapped_column(Integer)
    is_payday: Mapped[bool]
    festival: Mapped[str | None] = mapped_column(String(40))
    festival_ramp: Mapped[float] = mapped_column(Numeric(4, 2))
    is_holiday: Mapped[bool]
    monsoon: Mapped[bool]
    is_operating: Mapped[bool]


class TravelRatio(Base):
    """Actual ÷ planned travel time by district and hour, computed at seed time (BR-18).

    Derived from the dataset, so it only ever lives in the database (ADR-0007).
    """

    __tablename__ = "travel_ratios"
    district: Mapped[str] = mapped_column(ForeignKey("districts.name"), primary_key=True)
    hour: Mapped[int] = mapped_column(Integer, primary_key=True)
    p50_ratio: Mapped[float] = mapped_column(Numeric(5, 3))
    p90_ratio: Mapped[float] = mapped_column(Numeric(5, 3))


class Product(Base):
    """Demo catalogue (the dataset has cases, kg and m³ per order, not items)."""

    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    brand: Mapped[str] = mapped_column(_enum(*BRANDS, name="brand"))
    is_chilled: Mapped[bool]


class UsualQuantity(Base):
    """An outlet's usual cases per product, used by the order sanity check (BR-42)."""

    __tablename__ = "usual_quantities"
    outlet_code: Mapped[str] = mapped_column(ForeignKey("outlets.code"), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)
    usual_cases: Mapped[int] = mapped_column(Integer)
