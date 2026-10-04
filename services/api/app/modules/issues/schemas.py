import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field


class IssueItemOut(BaseModel):
    product_id: str | None
    name: str
    driver_qty: int | None
    problem: str | None
    problem_qty: int
    photo_url: str | None = None


class IssueOut(BaseModel):
    id: uuid.UUID
    kind: str
    status: str
    order_ref: str
    outlet_code: str
    district: str
    temp_requirement: str
    vehicle_code: str | None
    driver_record_id: uuid.UUID | None
    driver_recorded_at: datetime | None
    driver_uploaded_at: datetime | None
    driver_name: str | None
    driver_photo_url: str | None
    store_recorded_at: datetime | None
    store_name: str | None
    store_photo_url: str | None
    opened_at: datetime
    driver_qty: int | None
    store_qty: int | None
    items: list[IssueItemOut]
    affected_cases: int
    next_run: date | None
    window_open: time
    window_close: time
    recount_due: datetime
    resolution: str | None
    note: str | None
    resolved_at: datetime | None


class ResolveIn(BaseModel):
    resolution: Literal["redeliver", "credit", "reject", "driver_stands", "store_stands", "recount"]
    note: str | None = Field(default=None, max_length=2000)
