"""Daily vehicle availability, dispatcher switch-offs (BR-10) and the weekly fuel ledger (BR-11)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class VehicleDay(Base):
    __tablename__ = "vehicle_days"
    vehicle_code: Mapped[str] = mapped_column(ForeignKey("vehicles.code"), primary_key=True)
    date: Mapped[date] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(
        Enum("available", "in_workshop", name="vehicle_status", native_enum=False)
    )
    # An available vehicle can be switched off for a reason the data doesn't know (e.g. no driver).
    switched_on: Mapped[bool] = mapped_column(default=True)
    off_reason: Mapped[str | None] = mapped_column(String(120))
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime | None]


class FuelLedger(Base):
    __tablename__ = "fuel_ledger"
    vehicle_code: Mapped[str] = mapped_column(ForeignKey("vehicles.code"), primary_key=True)
    iso_year: Mapped[int] = mapped_column(Integer, primary_key=True)
    iso_week: Mapped[int] = mapped_column(Integer, primary_key=True)
    litres_used: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
