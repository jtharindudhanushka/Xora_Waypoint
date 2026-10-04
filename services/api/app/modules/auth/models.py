"""Users and role scopes (BR-55)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

ROLES = ("dispatcher", "loader", "driver", "store_manager")


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(Enum(*ROLES, name="role", native_enum=False))
    # Scope: which slice of the network this user may see and act on.
    depot: Mapped[str | None] = mapped_column(ForeignKey("depots.name"))
    dock: Mapped[str | None] = mapped_column(String(20))
    vehicle_code: Mapped[str | None] = mapped_column(ForeignKey("vehicles.code"))
    outlet_code: Mapped[str | None] = mapped_column(ForeignKey("outlets.code"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
