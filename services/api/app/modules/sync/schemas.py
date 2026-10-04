"""Typed sync, bootstrap and driver-day contract (docs/05 › Sync, Driver; docs/07)."""

import uuid
from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "trip_acknowledged",
    "load_checked",
    "trip_loaded",
    "shortfall_reported",
    "arrived",
    "outcome_recorded",
    "note_added",
]
SyncStatus = Literal["accepted", "duplicate", "conflict", "rejected"]


class EntityRef(BaseModel):
    type: Literal["trip", "stop", "order"]
    id: str = Field(max_length=64)


class SyncEventIn(BaseModel):
    event_id: uuid.UUID  # generated on the device (BR-35, BR-36)
    type: EventType
    entity: EntityRef
    plan_version_id: uuid.UUID | None = None  # the version the user was looking at (BR-53)
    event_time: datetime  # device time; the time that counts (BR-37)
    seq: int | None = None  # client order within the device
    payload: dict[str, Any] = Field(default_factory=dict)


class SyncIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    events: list[SyncEventIn] = Field(max_length=50)


class SyncResultOut(BaseModel):
    event_id: uuid.UUID
    status: SyncStatus
    conflict_id: uuid.UUID | None = None
    code: str | None = None
    rule_id: str | None = None
    detail: str | None = None


class SyncOut(BaseModel):
    results: list[SyncResultOut]
    server_time: datetime


class OrderLineView(BaseModel):
    product_id: str
    name: str
    qty: int


class KnownShortfallOut(BaseModel):
    """A loading shortfall already reported for this order: pre-filled and locked (BR-34)."""

    shortfall_id: uuid.UUID
    kind: str
    qty: int
    reason: str


class StopOrderView(BaseModel):
    order_id: uuid.UUID
    order_ref: str
    temp_requirement: str
    planned_cases: int
    top_up_of_order_ref: str | None = None
    lines: list[OrderLineView]
    known_shortfall: KnownShortfallOut | None = None


class StopView(BaseModel):
    id: uuid.UUID
    seq: int
    outlet_code: str
    district: str
    status: str
    plan_arrival: time | None  # standard clock (BR-08)
    likely_from: time | None  # realistic window (BR-18)
    likely_to: time | None
    at_risk: bool
    window_open: time
    window_close: time
    dock_type: str
    parking_constraint: str
    mall_window_open: time | None
    mall_window_close: time | None
    access_note: str | None  # from the outlet profile, labelled as such (BR-39)
    contact_name: str | None
    store_note: str | None  # same-day note from the store, shown first (BR-39)
    arrived_at: datetime | None
    outcome: str | None
    orders: list[StopOrderView]


class TripView(BaseModel):
    id: uuid.UUID
    trip_no: int
    lane: str
    brand: str
    district: str
    planned_depart: time | None
    plan_minutes: int
    weight_kg: float
    volume_m3: float
    on_hold: bool  # BR-27
    hold_shortfall_id: uuid.UUID | None
    stops: list[StopView]


class VersionView(BaseModel):
    id: uuid.UUID
    number: int
    published_at: datetime | None
    change_reason: str | None
    acknowledged: bool  # by the signed-in user (BR-32)
    acked_at: datetime | None


class VehicleTodayOut(BaseModel):
    vehicle_code: str
    vehicle_type: str
    vehicle_temp: str
    operating_date: date
    server_time: datetime
    version: VersionView | None
    trips: list[TripView]


class BootstrapUserOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    depot: str | None
    dock: str | None
    vehicle_code: str | None


class BootstrapOut(BaseModel):
    server_time: datetime
    operating_date: date
    user: BootstrapUserOut
    vehicles: list[VehicleTodayOut]
