"""Dispatcher live operations; field ingestion stays in the sync track."""

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends

from app.core.deps import ClockDep, DbDep, require_roles
from app.modules.auth.models import User
from app.modules.ops import service
from app.modules.ops.repository import Repository
from app.modules.ops.schemas import ExceptionOut, FixOut, OpsOut
from app.modules.planning.service import repository

router = APIRouter(tags=["operations"])
Dispatcher = Annotated[User, Depends(require_roles("dispatcher"))]


def scoped(db: DbDep, user: User) -> Repository:
    return Repository(db, repository(db, user).depot)


@router.get("/ops/{operating_date}", response_model=OpsOut)
def get_ops(operating_date: date, db: DbDep, clock: ClockDep, user: Dispatcher) -> OpsOut:
    repo = scoped(db, user)
    repo.plan(operating_date, lock=True)
    return service.refresh(repo, clock, repo.published(operating_date))


@router.get("/exceptions", response_model=list[ExceptionOut])
def get_exceptions(
    db: DbDep, user: Dispatcher, status: Literal["open", "resolved"] = "open"
) -> list[ExceptionOut]:
    return [service.exception_out(row) for row in scoped(db, user).exceptions(status)]


@router.post("/exceptions/{identifier}/apply-fix", response_model=FixOut)
async def apply_fix(identifier: uuid.UUID, db: DbDep, clock: ClockDep, user: Dispatcher) -> FixOut:
    return await service.apply_fix(scoped(db, user), user, clock, identifier)
