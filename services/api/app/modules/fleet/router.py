"""Fleet switches are operational overrides; reference vehicles never change (BR-10)."""

from datetime import date

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import ClockDep, DbDep
from app.core.errors import DomainError, NotFoundError
from app.modules.catalog.models import Vehicle
from app.modules.fleet.models import VehicleDay
from app.modules.planning.router import Dispatcher
from app.modules.planning.schemas import FleetOut, FleetSwitchIn
from app.modules.planning.service import fleet_out, repository

router = APIRouter(tags=["fleet"])


@router.get("/fleet", response_model=list[FleetOut])
def get_fleet(date: date, db: DbDep, user: Dispatcher) -> list[FleetOut]:
    return fleet_out(repository(db, user), date)


@router.patch("/fleet/{vehicle}/{operating_date}", response_model=FleetOut)
def switch(
    vehicle: str,
    operating_date: date,
    body: FleetSwitchIn,
    db: DbDep,
    clock: ClockDep,
    user: Dispatcher,
) -> FleetOut:
    repo = repository(db, user)
    day = db.scalar(
        select(VehicleDay)
        .join(Vehicle)
        .where(
            Vehicle.code == vehicle, Vehicle.depot == repo.depot, VehicleDay.date == operating_date
        )
        .with_for_update()
    )
    if day is None:
        raise NotFoundError(
            "VEHICLE_NOT_FOUND", "Vehicle is not in your depot's fleet for this date"
        )
    if day.status == "in_workshop":
        raise DomainError("IN_WORKSHOP", "Workshop vehicles are locked off", rule_id="BR-10")
    if not body.switched_on and not (body.off_reason or "").strip():
        raise DomainError(
            "OFF_REASON_REQUIRED", "Write a reason to switch off this vehicle", rule_id="BR-10"
        )
    day.switched_on = body.switched_on
    day.off_reason = None if body.switched_on else (body.off_reason or "").strip()
    day.changed_by = user.id
    day.changed_at = clock.now()
    db.commit()
    return next(v for v in fleet_out(repo, operating_date) if v.vehicle_code == vehicle)
