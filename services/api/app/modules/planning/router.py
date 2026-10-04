"""Dispatcher-only planning endpoints (BR-55)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import ClockDep, DbDep, require_roles
from app.modules.auth.models import User
from app.modules.planning import service
from app.modules.planning.schemas import (
    ConfirmIn,
    PlanOut,
    PublishCheckOut,
    PublishIn,
    ServeInsteadIn,
    ServeInsteadOut,
)

Dispatcher = Annotated[User, Depends(require_roles("dispatcher"))]
router = APIRouter(tags=["planning"])


@router.post("/plans/{operating_date}/generate", response_model=PlanOut)
def generate(operating_date: date, db: DbDep, clock: ClockDep, user: Dispatcher) -> PlanOut:
    repo = service.repository(db, user)
    return service.plan_out(repo, service.generate(repo, user, clock, operating_date))


@router.get("/plans/{operating_date}", response_model=PlanOut)
def get_plan(operating_date: date, db: DbDep, user: Dispatcher) -> PlanOut:
    repo = service.repository(db, user)
    return service.plan_out(repo, service.get_plan(repo, operating_date))


@router.post("/plan-versions/{version_id}/deferrals/confirm", response_model=PlanOut)
def confirm(
    version_id: uuid.UUID, body: ConfirmIn, db: DbDep, clock: ClockDep, user: Dispatcher
) -> PlanOut:
    repo = service.repository(db, user)
    return service.plan_out(repo, service.confirm(repo, user, clock, version_id, body))


@router.get("/plan-versions/{version_id}/publish-check", response_model=PublishCheckOut)
def publish_check(version_id: uuid.UUID, db: DbDep, user: Dispatcher) -> PublishCheckOut:
    repo = service.repository(db, user)
    return service.publish_check(repo, repo.version(version_id))


@router.post("/plan-versions/{version_id}/publish", response_model=PlanOut)
async def publish(
    version_id: uuid.UUID,
    db: DbDep,
    clock: ClockDep,
    user: Dispatcher,
    body: PublishIn | None = None,
) -> PlanOut:
    repo = service.repository(db, user)
    version = await service.publish(
        repo, user, clock, version_id, body.accept_late_risk if body else False
    )
    return service.plan_out(repo, version)


@router.post("/deferrals/{deferral_id}/serve-instead", response_model=ServeInsteadOut)
def serve_instead(
    deferral_id: uuid.UUID, body: ServeInsteadIn, db: DbDep, clock: ClockDep, user: Dispatcher
) -> ServeInsteadOut:
    return service.serve_instead(
        service.repository(db, user), user, clock, deferral_id, body.confirm
    )


@router.post("/trips/{trip_id}/lock", response_model=PlanOut)
def lock_trip(trip_id: uuid.UUID, db: DbDep, clock: ClockDep, user: Dispatcher) -> PlanOut:
    return service.lock_trip(service.repository(db, user), user, clock, trip_id, True)


@router.delete("/trips/{trip_id}/lock", response_model=PlanOut)
def unlock_trip(trip_id: uuid.UUID, db: DbDep, clock: ClockDep, user: Dispatcher) -> PlanOut:
    return service.lock_trip(service.repository(db, user), user, clock, trip_id, False)
