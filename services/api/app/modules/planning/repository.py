"""Planning persistence and scoped reference reads; services own transactions."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.modules.catalog.models import (
    CalendarDay,
    District,
    Outlet,
    ServiceAllowance,
    TravelRatio,
    Vehicle,
)
from app.modules.fleet.models import FuelLedger, VehicleDay
from app.modules.orders.models import Order
from app.modules.planning.models import Plan, PlanVersion


class Repository:
    def __init__(self, db: Session, depot: str) -> None:
        self.db = db
        self.depot = depot

    def plan(self, operating_date: date, *, lock: bool = False) -> Plan | None:
        stmt = select(Plan).where(Plan.depot == self.depot, Plan.operating_date == operating_date)
        if lock:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def latest(self, plan_id: uuid.UUID) -> PlanVersion | None:
        return self.db.scalar(
            select(PlanVersion)
            .where(PlanVersion.plan_id == plan_id)
            .order_by(PlanVersion.number.desc())
            .limit(1)
        )

    def version(self, version_id: uuid.UUID, *, lock: bool = False) -> PlanVersion:
        stmt = select(PlanVersion).where(PlanVersion.id == version_id)
        if lock:
            stmt = stmt.with_for_update()
        version = self.db.scalar(stmt)
        if version is None:
            raise NotFoundError("PLAN_NOT_FOUND", "Plan version not found")
        if version.plan.depot != self.depot:
            raise ForbiddenError(
                "DEPOT_FORBIDDEN", "This plan belongs to another depot", rule_id="BR-55"
            )
        return version

    def orders(self, operating_date: date) -> list[Order]:
        return list(
            self.db.scalars(
                select(Order)
                .join(Outlet, Order.outlet_code == Outlet.code)
                .where(
                    Outlet.depot == self.depot,
                    Order.delivery_date == operating_date,
                    Order.status.in_(("placed", "planned", "deferred")),
                )
            )
        )

    def outlets(self) -> list[Outlet]:
        return list(self.db.scalars(select(Outlet).where(Outlet.depot == self.depot)))

    def districts(self) -> list[District]:
        return list(self.db.scalars(select(District).where(District.depot == self.depot)))

    def allowances(self) -> list[ServiceAllowance]:
        return list(self.db.scalars(select(ServiceAllowance)))

    def ratios(self) -> list[TravelRatio]:
        return list(
            self.db.scalars(select(TravelRatio).join(District).where(District.depot == self.depot))
        )

    def fleet(self, operating_date: date) -> list[tuple[Vehicle, VehicleDay, float]]:
        year, week, _ = operating_date.isocalendar()
        vehicles = self.db.execute(
            select(Vehicle, VehicleDay)
            .join(VehicleDay)
            .where(Vehicle.depot == self.depot, VehicleDay.date == operating_date)
        ).all()
        ledger = {
            r.vehicle_code: float(r.litres_used)
            for r in self.db.scalars(
                select(FuelLedger).where(FuelLedger.iso_year == year, FuelLedger.iso_week == week)
            )
        }
        return [(v, day, ledger.get(v.code, 0)) for v, day in vehicles]

    def next_operating_date(self, current: date) -> date | None:
        return self.db.scalar(
            select(CalendarDay.date)
            .where(CalendarDay.date > current, CalendarDay.is_operating.is_(True))
            .order_by(CalendarDay.date)
            .limit(1)
        )
