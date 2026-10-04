"""The append-only event log (ADR-0003, docs/07-offline-sync.md).

`event_id` is generated on the device, so a resend is recognised and never duplicated (BR-36).
`event_time` is the device time that counts; `received_at` is when the server got it (BR-37).
Rows are never updated or deleted: a database trigger enforces this on Postgres.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

EVENT_TYPES = (
    "trip_acknowledged",
    "load_checked",
    "trip_loaded",
    "shortfall_reported",
    "arrived",
    "outcome_recorded",
    "note_added",
)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_entity", "entity_type", "entity_id"),)
    event_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    device_id: Mapped[str | None] = mapped_column(String(80))
    plan_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plan_versions.id"))
    entity_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    event_time: Mapped[datetime]
    received_at: Mapped[datetime]
