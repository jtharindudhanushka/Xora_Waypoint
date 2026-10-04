"""Store receipts and issues: store reports (D10), count and stale-plan conflicts (D13)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

ISSUE_KINDS = ("store_report", "count_conflict", "stale_plan")
RESOLUTIONS = ("redeliver", "credit", "reject", "driver_stands", "store_stands", "recount")
LINE_PROBLEMS = ("missing", "damaged", "wrong_item", "warm")


class Receipt(Base):
    """Store acceptance, a separate event from the driver's record (BR-46)."""

    __tablename__ = "receipts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), unique=True)
    confirmed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime]
    total_cases: Mapped[int] = mapped_column(Integer)

    lines: Mapped[list[ReceiptLine]] = relationship(lazy="selectin")


class ReceiptLine(Base):
    __tablename__ = "receipt_lines"
    receipt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("receipts.id"), primary_key=True)
    order_line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("order_lines.id"), primary_key=True)
    driver_qty: Mapped[int] = mapped_column(Integer)
    store_qty: Mapped[int] = mapped_column(Integer)


class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    kind: Mapped[str] = mapped_column(Enum(*ISSUE_KINDS, name="issue_kind", native_enum=False))
    status: Mapped[str] = mapped_column(
        Enum("open", "resolved", name="issue_status", native_enum=False), default="open"
    )
    driver_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.event_id"))
    driver_qty: Mapped[int | None] = mapped_column(Integer)
    store_qty: Mapped[int | None] = mapped_column(Integer)
    store_photo_url: Mapped[str | None] = mapped_column(String(300))
    opened_at: Mapped[datetime]
    resolution: Mapped[str | None] = mapped_column(
        Enum(*RESOLUTIONS, name="issue_resolution", native_enum=False)
    )
    note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None]

    lines: Mapped[list[IssueLine]] = relationship(lazy="selectin")


class IssueLine(Base):
    """One problem on one item line; good lines are still confirmed (BR-47)."""

    __tablename__ = "issue_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("issues.id"), index=True)
    order_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("order_lines.id"))
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"))
    problem: Mapped[str] = mapped_column(
        Enum(*LINE_PROBLEMS, name="line_problem", native_enum=False)
    )
    qty: Mapped[int] = mapped_column(Integer)
    photo_url: Mapped[str | None] = mapped_column(String(300))
