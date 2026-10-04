"""Plans, immutable published versions, trips, stops, deferrals and acknowledgements.

Once a version is published it never changes (ADR-0003). A change creates version n+1,
which affected loaders and drivers must acknowledge (BR-23, BR-31, BR-32).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

REASON_CODES = (
    "NO_REEFER_CAPACITY",
    "NO_VAN_AVAILABLE",
    "VOLUME_CAP",
    "WEIGHT_CAP",
    "FRESH_TIME_BUDGET",
    "DAY_TIME_BUDGET",
    "TRIP_LIMIT",
    "FUEL_QUOTA",
    "VEHICLE_UNAVAILABLE",
    "LOWER_PRIORITY",
)  # BR-15


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("depot", "operating_date"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    depot: Mapped[str] = mapped_column(ForeignKey("depots.name"))
    operating_date: Mapped[date]

    versions: Mapped[list[PlanVersion]] = relationship(
        back_populates="plan", order_by="PlanVersion.number"
    )


class PlanVersion(Base):
    __tablename__ = "plan_versions"
    __table_args__ = (UniqueConstraint("plan_id", "number"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        Enum("draft", "published", "superseded", name="version_status", native_enum=False),
        default="draft",
    )
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plan_versions.id"))
    change_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    published_at: Mapped[datetime | None]
    solver_status: Mapped[str | None] = mapped_column(String(20))  # OPTIMAL | FEASIBLE | GREEDY
    solve_ms: Mapped[int | None] = mapped_column(Integer)
    kpis: Mapped[dict[str, Any]] = mapped_column(default=dict)
    bottleneck: Mapped[dict[str, Any]] = mapped_column(default=dict)

    plan: Mapped[Plan] = relationship(back_populates="versions")
    trips: Mapped[list[Trip]] = relationship(back_populates="version", lazy="selectin")
    deferrals: Mapped[list[Deferral]] = relationship(back_populates="version", lazy="selectin")


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        UniqueConstraint("version_id", "vehicle_code", "trip_no"),
        CheckConstraint("trip_no IN (1, 2)", name="trip_no"),  # BR-07
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_versions.id"), index=True)
    vehicle_code: Mapped[str] = mapped_column(ForeignKey("vehicles.code"))
    trip_no: Mapped[int] = mapped_column(Integer)
    brand: Mapped[str] = mapped_column(String(10))
    district: Mapped[str] = mapped_column(ForeignKey("districts.name"))
    lane: Mapped[str] = mapped_column(
        Enum("predawn", "daytime", name="trip_lane", native_enum=False)
    )  # BR-09
    planned_depart: Mapped[time | None]
    plan_minutes: Mapped[int] = mapped_column(Integer)  # BR-08 standard
    litres: Mapped[float] = mapped_column(Numeric(7, 2), default=0)
    weight_kg: Mapped[float] = mapped_column(Numeric(9, 2), default=0)
    volume_m3: Mapped[float] = mapped_column(Numeric(7, 3), default=0)
    locked: Mapped[bool] = mapped_column(default=False)  # BR-20

    version: Mapped[PlanVersion] = relationship(back_populates="trips")
    stops: Mapped[list[Stop]] = relationship(
        back_populates="trip", order_by="Stop.seq", lazy="selectin"
    )


class Stop(Base):
    __tablename__ = "stops"
    __table_args__ = (UniqueConstraint("trip_id", "seq"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    outlet_code: Mapped[str] = mapped_column(ForeignKey("outlets.code"))
    plan_arrival: Mapped[time | None]  # standard clock (BR-08)
    likely_from: Mapped[time | None]  # realistic window (BR-18)
    likely_to: Mapped[time | None]
    at_risk: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(20), default="planned")  # BR-54 vocabulary

    trip: Mapped[Trip] = relationship(back_populates="stops")
    orders: Mapped[list[StopOrder]] = relationship(lazy="selectin")


class StopOrder(Base):
    __tablename__ = "stop_orders"
    stop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stops.id"), primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    planned_cases: Mapped[int] = mapped_column(Integer)
    # Operational top-up of an order already partly carried on another trip (BR-30).
    top_up_of_order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))


class Deferral(Base):
    __tablename__ = "deferrals"
    __table_args__ = (UniqueConstraint("version_id", "order_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_versions.id"), index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    reason_code: Mapped[str] = mapped_column(Enum(*REASON_CODES, name="reason_code", native_enum=False))
    group: Mapped[str] = mapped_column(
        Enum("unavoidable", "choice", name="deferral_group", native_enum=False)
    )  # BR-16
    priority: Mapped[float] = mapped_column(Numeric(7, 2))
    displaces: Mapped[list[Any]] = mapped_column(default=list)
    explanation: Mapped[str | None] = mapped_column(Text)
    next_run: Mapped[datetime | None]
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None]
    confirm_reason: Mapped[str | None] = mapped_column(Text)  # required for repeat skips (BR-21)

    version: Mapped[PlanVersion] = relationship(back_populates="deferrals")


class PlanAck(Base):
    __tablename__ = "plan_acks"
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_versions.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    acked_at: Mapped[datetime]
