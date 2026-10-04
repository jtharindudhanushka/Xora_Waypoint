"""Typed planning and fleet contract; generated into the web client."""

import uuid
from datetime import date, time

from pydantic import BaseModel, Field


class ViolationOut(BaseModel):
    rule_id: str
    code: str
    message: str
    context: dict[str, str | int | float | bool | tuple[str, ...]]


class KpisOut(BaseModel):
    orders_served: int
    chilled_served: int
    stops_at_risk: int
    deferrals: int
    value_served: float
    reefer_m3_used: float
    reefer_m3_total: float


class BottleneckOut(BaseModel):
    resource: str
    used: float
    capacity: float
    explanation: str


class StopOrderOut(BaseModel):
    order_ref: str
    cases: int
    top_up_of_order_ref: str | None = None


class StopOut(BaseModel):
    id: uuid.UUID
    seq: int
    outlet_code: str
    plan_arrival: time | None
    likely_from: time | None
    likely_to: time | None
    at_risk: bool
    status: str
    orders: list[StopOrderOut]


class TripOut(BaseModel):
    id: uuid.UUID
    vehicle_code: str
    trip_no: int
    brand: str
    district: str
    lane: str
    planned_depart: time | None
    plan_minutes: int
    litres: float
    weight_kg: float
    volume_m3: float
    locked: bool
    stops: list[StopOut]
    rule_messages: list[ViolationOut] = Field(default_factory=list)
    protected_outlets: list[str] = Field(default_factory=list)


class DeferralOut(BaseModel):
    id: uuid.UUID
    order_ref: str
    outlet_code: str
    reason_code: str
    group: str
    priority: float
    explanation: str | None
    displaces: list[str]
    next_run: date | None
    repeat_skip: bool
    confirmed: bool
    confirm_reason: str | None
    district: str
    temp_requirement: str
    volume_m3: float
    weight_kg: float
    notice_body: str = ""
    notice_language: str = "en"


class PlanOut(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    number: int
    operating_date: date
    depot: str
    status: str
    solver_status: str | None
    solve_ms: int | None
    kpis: KpisOut
    bottleneck: BottleneckOut
    trips: list[TripOut]
    deferrals: list[DeferralOut]
    orders_total: int
    chilled_total: int


class ConfirmItem(BaseModel):
    deferral_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=2000)


class ConfirmIn(BaseModel):
    items: list[ConfirmItem] = Field(min_length=1)


class PublishIn(BaseModel):
    accept_late_risk: bool = False


class PublishCheckOut(BaseModel):
    can_publish: bool
    violations: list[ViolationOut]
    unconfirmed_deferrals: list[uuid.UUID]
    late_risk_order_refs: list[str]


class FleetSwitchIn(BaseModel):
    switched_on: bool
    off_reason: str | None = Field(default=None, max_length=120)


class FleetOut(BaseModel):
    vehicle_code: str
    date: date
    type: str
    temp: str
    status: str
    switched_on: bool
    off_reason: str | None
    weight_cap_kg: float
    volume_cap_m3: float
    fuel_used_l: float
    fuel_remaining_l: float


class ServeInsteadIn(BaseModel):
    confirm: bool = False


class ServeInsteadOut(BaseModel):
    order_ref: str
    displaces: list[str]
    version: PlanOut | None = None
