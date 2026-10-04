"""Store orders, their item lines, and same-day driver notes (BR-39 to BR-43)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

ORDER_STATUS = ("draft", "placed", "planned", "deferred", "loaded", "in_transit", "delivered")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ref: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # e.g. S1-001
    outlet_code: Mapped[str] = mapped_column(ForeignKey("outlets.code"), index=True)
    brand: Mapped[str] = mapped_column(String(10))
    temp_requirement: Mapped[str] = mapped_column(
        Enum("chilled", "ambient", name="temp_requirement", native_enum=False)
    )
    delivery_date: Mapped[date] = mapped_column(index=True)
    units: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[float] = mapped_column(Numeric(10, 2))
    volume_m3: Mapped[float] = mapped_column(Numeric(8, 3))
    deferred_yesterday: Mapped[bool] = mapped_column(default=False)
    days_since_last_served: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        Enum(*ORDER_STATUS, name="order_status", native_enum=False), default="placed"
    )
    source: Mapped[str] = mapped_column(
        Enum("dataset", "app", name="order_source", native_enum=False), default="app"
    )
    placed_at: Mapped[datetime | None]
    placed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    lines: Mapped[list[OrderLine]] = relationship(back_populates="order", lazy="selectin")


class OrderLine(Base):
    __tablename__ = "order_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    qty_ordered: Mapped[int] = mapped_column(Integer)
    qty_loaded: Mapped[int | None] = mapped_column(Integer)
    qty_delivered: Mapped[int | None] = mapped_column(Integer)
    qty_received: Mapped[int | None] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="lines")


class DriverNote(Base):
    """A store's note for today's driver, shown at the top of R2 (BR-39)."""

    __tablename__ = "driver_notes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    outlet_code: Mapped[str] = mapped_column(ForeignKey("outlets.code"), index=True)
    for_date: Mapped[date]
    text: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(server_default=func.now())
    sent_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
