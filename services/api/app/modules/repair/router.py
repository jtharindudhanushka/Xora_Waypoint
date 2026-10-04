"""Dispatcher repair routes; reuse the established clock, DB and role dependencies."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import ClockDep, DbDep, require_roles
from app.modules.auth.models import User
from app.modules.planning.schemas import PlanOut
from app.modules.planning.service import plan_out, repository
from app.modules.repair import service
from app.modules.repair.repository import Repository
from app.modules.repair.schemas import RepairApplyIn, ShortfallOptionsOut

router = APIRouter(prefix="/shortfalls", tags=["Repair"])
Dispatcher = Annotated[User, Depends(require_roles("dispatcher"))]


@router.get("/{shortfall_id}/options", response_model=ShortfallOptionsOut)
def options(
    shortfall_id: uuid.UUID, db: DbDep, clock: ClockDep, user: Dispatcher
) -> ShortfallOptionsOut:
    scoped = repository(db, user)
    return service.get_options(Repository(db, scoped.depot), clock, shortfall_id)


@router.post("/{shortfall_id}/apply", response_model=PlanOut)
async def apply(
    shortfall_id: uuid.UUID, body: RepairApplyIn, db: DbDep, clock: ClockDep, user: Dispatcher
) -> PlanOut:
    scoped = repository(db, user)
    repo = Repository(db, scoped.depot)
    version = await service.apply(repo, user, clock, shortfall_id, body.option_id)
    return plan_out(repo, version)
