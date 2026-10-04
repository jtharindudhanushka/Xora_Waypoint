"""Sync and driver-day routes (docs/05 › Sync, Driver; docs/07)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import ClockDep, DbDep, require_roles
from app.core.errors import ForbiddenError
from app.modules.auth.models import User
from app.modules.catalog.models import Vehicle
from app.modules.stream.broker import broker
from app.modules.sync import service, views
from app.modules.sync.schemas import (
    BootstrapOut,
    BootstrapUserOut,
    SyncIn,
    SyncOut,
    VehicleTodayOut,
)

router = APIRouter(tags=["Sync"])
FieldUser = Annotated[User, Depends(require_roles("driver", "loader", "dispatcher"))]


@router.post("/sync", response_model=SyncOut)
async def sync(body: SyncIn, db: DbDep, clock: ClockDep, user: FieldUser) -> SyncOut:
    """Apply a device outbox in order; idempotent by `event_id` (BR-35 to BR-37, BR-52, BR-53)."""
    out = service.Outbound()
    result = service.process(db, clock, user, body, out)
    for event, data, audience in out.messages:
        await broker.publish(event, data, audience)
    accepted = [r for r in result.results if r.status in ("accepted", "conflict")]
    if accepted and user.depot:
        depot = user.depot
        await broker.publish(
            "sync.applied",
            {"user_id": str(user.id), "accepted": len(accepted)},
            lambda s: s.get("role") == "dispatcher" and s.get("depot") == depot,
        )
    return result


@router.get("/sync/bootstrap", response_model=BootstrapOut)
def bootstrap(
    db: DbDep, clock: ClockDep, user: FieldUser, date: date | None = None
) -> BootstrapOut:
    """Everything a field device needs to work offline today (docs/07 › Client side, BR-38)."""
    day = views.operating_date(clock, date)
    if user.role == "driver":
        codes = [user.vehicle_code] if user.vehicle_code else []
    else:
        version = views.published_version(db, user.depot or "", day)
        codes = sorted({t.vehicle_code for t in version.trips}) if version else []
    vehicles = [db.get(Vehicle, code) for code in codes]
    return BootstrapOut(
        server_time=clock.now(),
        operating_date=day,
        user=BootstrapUserOut(
            id=user.id,
            name=user.name,
            role=user.role,
            depot=user.depot,
            dock=user.dock,
            vehicle_code=user.vehicle_code,
        ),
        vehicles=[views.vehicle_today(db, clock, user, v, day) for v in vehicles if v],
    )


@router.get("/vehicles/{code}/today", response_model=VehicleTodayOut, tags=["Driver"])
def vehicle_today(
    code: str, db: DbDep, clock: ClockDep, user: FieldUser, date: date | None = None
) -> VehicleTodayOut:
    """Published trips, stops, two clocks, notes and known shortfalls (BR-32 to BR-34, BR-39)."""
    vehicle = views.require_vehicle(db, code)
    if user.role == "driver" and user.vehicle_code != code:
        raise ForbiddenError("OUT_OF_SCOPE", f"{code} is not your vehicle", rule_id="BR-55")
    if user.role != "driver" and user.depot != vehicle.depot:
        raise ForbiddenError("OUT_OF_SCOPE", f"{code} is not in your depot", rule_id="BR-55")
    return views.vehicle_today(db, clock, user, vehicle, views.operating_date(clock, date))
