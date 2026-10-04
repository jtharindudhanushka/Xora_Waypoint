"""Repair contract, generated into the shared TypeScript client."""

import uuid
from datetime import date, time

from pydantic import BaseModel


class RepairStopOut(BaseModel):
    outlet_code: str
    order_ref: str
    cases: int
    available_cases: int
    window_open: time
    window_close: time


class RepairOptionOut(BaseModel):
    id: uuid.UUID
    label: str
    rank: int
    title: str
    gets: str
    delay: str
    other_stops: str
    loss: float
    loss_label: str
    breaks_store_rule: bool
    recommended: bool


class ShortfallOptionsOut(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    next_version_number: int
    operating_date: date
    vehicle_code: str
    trip_no: int
    depot: str
    dock: str | None
    reported_at: time
    reporter: str
    kind: str
    reason: str
    order_ref: str
    outlet_code: str
    district: str
    temp_requirement: str
    planned_cases: int
    missing_cases: int
    waiting_seconds: int
    to_departure_minutes: int
    planned_depart: time | None
    split_rule: str
    split_rule_text: str
    held: bool
    solve_ms: int
    stops: list[RepairStopOut]
    options: list[RepairOptionOut]


class RepairApplyIn(BaseModel):
    option_id: uuid.UUID
