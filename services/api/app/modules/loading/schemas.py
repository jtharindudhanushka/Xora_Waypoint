"""Dock read contracts (BR-24, BR-25, BR-31, BR-54)."""

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel


class DockVersion(BaseModel):
    id: uuid.UUID
    number: int
    published_at: datetime | None
    acknowledged: bool
    needs_acknowledgement: bool
    change_reason: str | None


class DockLine(BaseModel):
    order_id: uuid.UUID
    order_ref: str
    outlet_code: str
    stop_seq: int
    cases: int
    temperature: str
    weight_kg: float
    top_up: bool


class DockChange(BaseModel):
    vehicle: str
    trip_no: int
    departure: time | None
    order_id: uuid.UUID
    order_ref: str
    outlet_code: str
    before: int
    after: int
    top_up: bool


class DockHold(BaseModel):
    id: uuid.UUID
    shortfall_id: uuid.UUID
    order_id: uuid.UUID
    order_ref: str
    outlet_code: str
    kind: str
    qty: int
    planned_cases: int
    reason: str
    reported_at: datetime
    waiting_seconds: int
    to_departure_minutes: int | None


class DockTrip(BaseModel):
    id: uuid.UUID
    vehicle: str
    vehicle_type: str
    temperature: str
    trip_no: int
    district: str
    departure: time | None
    stops: int
    cases: int
    volume_m3: float
    weight_kg: float
    volume_cap_m3: float
    weight_cap_kg: float
    load_status: Literal["planned", "loaded", "on_hold"]
    on_hold: bool
    version: DockVersion


class DockDay(BaseModel):
    date: date
    depot: str
    dock: str | None
    version: DockVersion | None
    trips: list[DockTrip]
    server_time: datetime


class DockDetail(DockTrip):
    load_list: list[DockLine]
    hold: DockHold | None
    previous_version: int | None
    previous_departure: time | None
    changes: list[DockChange]
    shortfall_reasons: list[str]
    server_time: datetime
