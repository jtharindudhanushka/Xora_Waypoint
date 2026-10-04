"""Dock shortfalls, per-vehicle holds and engine repair options (BR-26 to BR-31)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

SHORTFALL_REASONS = ("short_from_chiller_pick", "not_on_dock", "damaged_in_pick", "other")


class Shortfall(Base):
    __tablename__ = "shortfalls"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id"), index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    kind: Mapped[str] = mapped_column(
        Enum("missing", "damaged", name="shortfall_kind", native_enum=False)
    )
    qty: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(
        Enum(*SHORTFALL_REASONS, name="shortfall_reason", native_enum=False)
    )
    photo_url: Mapped[str | None] = mapped_column(String(300))
    reported_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    event_time: Mapped[datetime]


class Hold(Base):
    """A held trip can't be released or depart until the loader acknowledges the fix (BR-27)."""

    __tablename__ = "holds"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id"), index=True)
    shortfall_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shortfalls.id"))
    status: Mapped[str] = mapped_column(
        Enum("active", "released", name="hold_status", native_enum=False), default="active"
    )
    created_at: Mapped[datetime]
    released_at: Mapped[datetime | None]
    released_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class RepairOption(Base):
    __tablename__ = "repair_options"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shortfall_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shortfalls.id"), index=True)
    label: Mapped[str] = mapped_column(String(4))  # A | B | C
    rank: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[dict[str, Any]] = mapped_column(default=dict)  # outlet gets, delay, effects
    breaks_store_rule: Mapped[bool] = mapped_column(default=False)  # BR-29
    loss: Mapped[float] = mapped_column(Numeric(9, 2), default=0)
    recommended: Mapped[bool] = mapped_column(default=False)
    applied_at: Mapped[datetime | None]
    applied_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
