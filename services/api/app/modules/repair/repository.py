"""Scoped reads and immutable option snapshots."""

import uuid

from sqlalchemy import select

from app.core.errors import NotFoundError
from app.modules.loading.models import Hold, RepairOption, Shortfall
from app.modules.planning.models import Trip
from app.modules.planning.repository import Repository as PlanningRepository


class Repository(PlanningRepository):
    def shortfall(self, shortfall_id: uuid.UUID, *, lock: bool = False) -> tuple[Shortfall, Trip]:
        stmt = select(Shortfall).where(Shortfall.id == shortfall_id)
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        row = self.db.scalar(stmt)
        # Other unresolved holds survive a revision; their reports retain v1 provenance.
        active_hold = self.hold(row.id, lock=lock) if row else None
        trip = (
            self.db.get(Trip, active_hold.trip_id if active_hold else row.trip_id) if row else None
        )
        if row is None or trip is None:
            raise NotFoundError("SHORTFALL_NOT_FOUND", "Shortfall not found")
        self.version(
            trip.version_id, lock=lock
        )  # BR-55: enforce depot scope before revealing data.
        return row, trip

    def hold(self, shortfall_id: uuid.UUID, *, lock: bool = True) -> Hold | None:
        stmt = select(Hold).where(Hold.shortfall_id == shortfall_id, Hold.status == "active")
        return self.db.scalar(
            stmt.with_for_update().execution_options(populate_existing=True) if lock else stmt
        )

    def applied(self, shortfall_id: uuid.UUID) -> RepairOption | None:
        return self.db.scalar(
            select(RepairOption).where(
                RepairOption.shortfall_id == shortfall_id, RepairOption.applied_at.is_not(None)
            )
        )

    def active_holds(self, version_id: uuid.UUID) -> list[Hold]:
        return list(
            self.db.scalars(
                select(Hold)
                .join(Trip, Hold.trip_id == Trip.id)
                .where(Trip.version_id == version_id, Hold.status == "active")
                .with_for_update()
            )
        )
