"""Store contract: server rules and read-only tracking (BR-39–47, BR-54)."""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

StoreStatus = Literal[
    "planned",
    "loaded",
    "in_transit",
    "delivered",
    "at_risk",
    "late",
    "deferred",
    "pending_sync",
    "on_hold",
]


class ItemIn(BaseModel):
    product_id: str
    qty: int = Field(ge=0, le=100000)


class OrderCheckIn(BaseModel):
    lines: list[ItemIn] = Field(min_length=1, max_length=100)


class OrderSubmitIn(OrderCheckIn):
    draft_ref: str | None = None
    confirm_unusual: bool = False
    request_id: UUID


class QuantityWarning(BaseModel):
    product_id: str
    qty: int
    usual_qty: int
    message: str
    rule_id: str = "BR-42"


class OrderCheckOut(BaseModel):
    warnings: list[QuantityWarning]
    delivery_date: date
    cutoff_at: datetime
    cutoff_seconds: int
    after_cutoff: bool


class UsualItemOut(BaseModel):
    product_id: str
    name: str
    is_chilled: bool
    usual_qty: int | None


class OrderLineOut(BaseModel):
    id: UUID
    product_id: str
    name: str
    qty_ordered: int
    qty_delivered: int | None
    qty_received: int | None


class TrackingOut(BaseModel):
    stop_id: UUID
    stop_seq: int
    stop_count: int
    vehicle_code: str
    trip_no: int
    version: int
    planned_cases: int
    plan_arrival: time | None
    likely_from: time | None
    likely_to: time | None
    status: StoreStatus
    basis: str = "based on past runs"
    event_time: datetime | None = None
    received_at: datetime | None = None


class OrderOut(BaseModel):
    ref: str
    outlet_code: str
    brand: str
    district: str
    temp_requirement: str
    delivery_date: date
    units: int
    status: StoreStatus
    submission_status: str
    placed_at: datetime | None
    receipt_confirmed: bool
    receipt_confirmed_at: datetime | None
    lines: list[OrderLineOut]
    tracking: list[TrackingOut]


class DriverNoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=240)


class DriverNoteOut(BaseModel):
    text: str
    sent_at: datetime


class StoreHomeOut(BaseModel):
    outlet_code: str
    district: str
    brand: str
    now: datetime
    ordering: OrderCheckOut
    window_open: time
    window_close: time
    orders: list[OrderOut]
    driver_note: DriverNoteOut | None


class NotificationOut(BaseModel):
    id: UUID
    kind: str
    order_ref: str | None
    reason_code: str | None
    lang: str
    title: str
    body: str
    next_run: str | None
    created_at: datetime
    acked_at: datetime | None
    source: str = "Written from the plan"
    protection: str = "First in line (moved once)"
