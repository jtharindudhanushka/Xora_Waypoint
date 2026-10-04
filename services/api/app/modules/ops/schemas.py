"""Dispatcher live projections and server-validated fixes (BR-48–50)."""

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel


class ExceptionOut(BaseModel):
    id: uuid.UUID
    kind: str
    impact: float
    title: str
    detail: str | None
    entity_type: str
    entity_id: str
    suggested_fix: dict[str, Any]
    status: str
    created_at: datetime


class OpsStopOut(BaseModel):
    id: uuid.UUID
    seq: int
    outlet_code: str
    status: str
    likely_from: time | None
    likely_to: time | None
    actual_at: datetime | None
    top_up_cases: int


class OpsTripOut(BaseModel):
    id: uuid.UUID
    vehicle_code: str
    trip_no: int
    district: str
    brand: str
    stops: list[OpsStopOut]


class OpsOut(BaseModel):
    operating_date: date
    depot: str
    version_id: uuid.UUID
    number: int
    delivered: int
    stops_total: int
    on_time: int
    pending_sync: int
    exceptions: list[ExceptionOut]
    trips: list[OpsTripOut]


class FixOut(BaseModel):
    exception_id: uuid.UUID
    status: str
    version_id: uuid.UUID | None = None
