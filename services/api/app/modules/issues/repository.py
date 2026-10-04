"""Read existing issue rows with depot isolation; never changes the field endpoints."""

import uuid

from sqlalchemy import select

from app.core.errors import NotFoundError
from app.modules.catalog.models import Outlet
from app.modules.orders.models import Order
from app.modules.planning.repository import Repository as PlanningRepository
from app.modules.receipts.models import Issue


class Repository(PlanningRepository):
    def list(self, status: str) -> list[Issue]:
        return list(
            self.db.scalars(
                select(Issue)
                .join(Order)
                .join(Outlet)
                .where(Outlet.depot == self.depot, Issue.status == status)
                .order_by(Issue.opened_at, Issue.id)
            )
        )

    def issue(self, identifier: uuid.UUID, *, lock: bool = False) -> Issue:
        stmt = (
            select(Issue)
            .join(Order)
            .join(Outlet)
            .where(Issue.id == identifier, Outlet.depot == self.depot)
        )
        row = self.db.scalar(stmt.with_for_update(of=Issue) if lock else stmt)
        if row is None:
            raise NotFoundError("ISSUE_NOT_FOUND", "Issue not found")
        return row
