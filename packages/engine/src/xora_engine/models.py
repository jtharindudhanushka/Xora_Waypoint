"""Immutable domain inputs; all reference data and time are supplied by the caller."""

from collections.abc import Mapping
from dataclasses import dataclass, field

EPSILON = 1e-6
type ContextValue = str | int | float | bool | tuple[str, ...]


@dataclass(frozen=True)
class Order:
    ref: str
    outlet: str
    brand: str
    district: str
    depot: str
    temp: str
    dock_type: str
    parking: str
    units: int
    weight_kg: float
    volume_m3: float
    window_open: int = 0
    window_close: int = 1440
    mall_open: int | None = None
    mall_close: int | None = None
    deferred_yesterday: bool = False
    days_since_last_served: int = 0


@dataclass(frozen=True)
class Vehicle:
    code: str
    type: str
    temp: str
    weight_cap_kg: float
    volume_cap_m3: float
    depot: str
    km_per_l: float
    fuel_remaining_l: float
    switched_on: bool = True
    status: str = "available"


@dataclass(frozen=True)
class District:
    name: str
    depot_to_district_min: int
    inter_stop_min: int
    depot_to_district_km: float
    inter_stop_km: float


@dataclass(frozen=True)
class Problem:
    orders: Mapping[str, Order]
    vehicles: Mapping[str, Vehicle]
    districts: Mapping[str, District]
    service_allowance: Mapping[tuple[str, str], int]
    festival_ramp: float = 0.0
    travel_ratio: Mapping[tuple[str, int], tuple[float, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class Stop:
    order_ref: str
    cases: int
    plan_arrival: int | None = None


@dataclass(frozen=True)
class Trip:
    vehicle: str
    trip_no: int
    stops: tuple[Stop, ...]
    planned_depart: int
    plan_minutes: int
    locked: bool = False


@dataclass(frozen=True)
class Assignment:
    trips: tuple[Trip, ...] = ()


@dataclass(frozen=True)
class Violation:
    rule_id: str
    code: str
    message: str
    context: Mapping[str, ContextValue] = field(default_factory=dict)
