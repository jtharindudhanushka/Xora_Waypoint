"""Receipt counts and item problems are separate from driver records (BR-46/47)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReceiptCountIn(BaseModel):
    order_line_id: UUID
    store_qty: int = Field(ge=0, le=100000)


class ReceiptIn(BaseModel):
    lines: list[ReceiptCountIn] | None = None


class ProblemLineIn(BaseModel):
    order_line_id: UUID | None = None
    product_id: str | None = None
    problem: Literal["missing", "damaged", "wrong_item", "warm"]
    qty: int = Field(gt=0, le=100000)
    photo_url: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def has_item(self) -> "ProblemLineIn":
        if self.order_line_id is None and self.product_id is None:
            raise ValueError("Select an order line or an additional catalogue item")
        return self


class IssueIn(BaseModel):
    request_id: UUID
    lines: list[ProblemLineIn] = Field(min_length=1, max_length=100)


class ReceiptDraftLine(BaseModel):
    order_line_id: UUID
    product_id: str
    name: str
    ordered_qty: int
    driver_qty: int | None
    store_qty: int | None


class ReceiptDraftOut(BaseModel):
    order_ref: str
    outlet_code: str
    vehicle_code: str | None
    delivered_at: datetime | None
    receiver: str | None
    photo_url: str | None
    driver_event_id: UUID | None
    can_confirm: bool
    confirmed: bool
    total_cases: int
    lines: list[ReceiptDraftLine]


class ReceiptOut(BaseModel):
    id: UUID
    order_ref: str
    total_cases: int
    confirmed_at: datetime
    issue_id: UUID | None = None


class IssueOut(BaseModel):
    id: UUID
    order_ref: str
    kind: str = "store_report"
    status: str
    receipt_id: UUID
