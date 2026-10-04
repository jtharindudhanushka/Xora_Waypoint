"""Exception inbox (BR-48), store notifications (BR-44, BR-49) and the demo clock (BR-56)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ExceptionItem(Base):
    __tablename__ = "exceptions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(
        Enum(
            "shortfall",
            "late_risk",
            "pending_sync",
            "store_report",
            "conflict",
            "fuel",
            name="exception_kind",
            native_enum=False,
        )
    )
    impact: Mapped[float] = mapped_column(Numeric(9, 2), default=0)  # ranking key
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(String(64))
    suggested_fix: Mapped[dict[str, Any]] = mapped_column(default=dict)
    status: Mapped[str] = mapped_column(
        Enum("open", "resolved", name="exception_status", native_enum=False), default="open"
    )
    created_at: Mapped[datetime]


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    outlet_code: Mapped[str | None] = mapped_column(ForeignKey("outlets.code"), index=True)
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(
        Enum(
            "deferral",
            "eta_late",
            "decision",
            "plan_changed",
            name="notification_kind",
            native_enum=False,
        )
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))
    reason_code: Mapped[str | None] = mapped_column(String(40))
    lang: Mapped[str] = mapped_column(String(2), default="en")
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[datetime]
    acked_at: Mapped[datetime | None]


class ClockSetting(Base):
    """Singleton row. When `demo_now` is set, the whole system runs on demo time (ADR-0006)."""

    __tablename__ = "clock_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    demo_now: Mapped[datetime | None]
    set_at: Mapped[datetime | None]
    set_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
