"""Depot-scoped operational projections; the lead owns field event ingestion."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select

from app.core.errors import NotFoundError
from app.modules.catalog.models import Outlet
from app.modules.loading.models import Shortfall
from app.modules.ops.models import ExceptionItem
from app.modules.orders.models import Order
from app.modules.planning.models import Plan, PlanVersion, Stop, Trip
from app.modules.planning.repository import Repository as PlanningRepository
from app.modules.receipts.models import Issue
from app.modules.sync.models import Event


class Repository(PlanningRepository):
    def published(self, day: date) -> PlanVersion:
        row = self.db.scalar(
            select(PlanVersion)
            .join(Plan)
            .where(
                Plan.depot == self.depot,
                Plan.operating_date == day,
                PlanVersion.status == "published",
            )
            .order_by(PlanVersion.number.desc())
            .limit(1)
        )
        if row is None:
            raise NotFoundError("PUBLISHED_PLAN_REQUIRED", "Publish a plan for this date first")
        return row

    def owns(self, row: ExceptionItem) -> bool:
        if row.entity_type in {"stop", "trip", "plan_version"}:
            entity: Any = self.db.get(
                {"stop": Stop, "trip": Trip, "plan_version": PlanVersion}[row.entity_type],
                uuid.UUID(row.entity_id),
            )
            if entity is None:
                return False
            version = (
                entity.trip.version
                if isinstance(entity, Stop)
                else (entity.version if isinstance(entity, Trip) else entity)
            )
            return version.plan.depot == self.depot
        if row.entity_type in {"issue", "shortfall", "order"}:
            entity = self.db.get(
                {"issue": Issue, "shortfall": Shortfall, "order": Order}[row.entity_type],
                uuid.UUID(row.entity_id),
            )
            order = (
                entity
                if isinstance(entity, Order)
                else (self.db.get(Order, entity.order_id) if entity else None)
            )
            outlet = self.db.get(Outlet, order.outlet_code) if order else None
            return outlet is not None and outlet.depot == self.depot
        return False

    def exceptions(self, status: str = "open") -> list[ExceptionItem]:
        return [
            row
            for row in self.db.scalars(
                select(ExceptionItem)
                .where(ExceptionItem.status == status)
                .order_by(ExceptionItem.impact.desc(), ExceptionItem.created_at, ExceptionItem.id)
            )
            if self.owns(row)
        ]

    def exception(self, identifier: uuid.UUID, *, lock: bool = False) -> ExceptionItem:
        stmt = select(ExceptionItem).where(ExceptionItem.id == identifier)
        row = self.db.scalar(stmt.with_for_update() if lock else stmt)
        if row is None or not self.owns(row):
            raise NotFoundError("EXCEPTION_NOT_FOUND", "Exception not found")
        return row

    def events(self, version: PlanVersion) -> list[Event]:
        # Old IDs retain provenance across immutable revisions; ancestors remain readable.
        versions = [version.id]
        parent = version.parent_version_id
        while parent:
            versions.append(parent)
            previous = self.db.get(PlanVersion, parent)
            parent = previous.parent_version_id if previous else None
        return list(
            self.db.scalars(
                select(Event).where(Event.plan_version_id.in_(versions)).order_by(Event.event_time)
            )
        )
