"""Loader-only, depot-scoped dock reads (BR-55). Mutations use the existing /sync."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import ClockDep, DbDep, require_roles
from app.modules.auth.models import User
from app.modules.loading import service
from app.modules.loading.schemas import DockDay, DockDetail

router = APIRouter(prefix="/dock", tags=["loading"])
Loader = Annotated[User, Depends(require_roles("loader"))]


@router.get("/trips", response_model=DockDay)
def trips(
    db: DbDep,
    clock: ClockDep,
    user: Loader,
    operating_date: Annotated[date | None, Query(alias="date")] = None,
) -> DockDay:
    return service.day(db, clock, user, operating_date)


@router.get("/trips/{identifier}", response_model=DockDetail)
def trip(identifier: uuid.UUID, db: DbDep, clock: ClockDep, user: Loader) -> DockDetail:
    return service.detail(db, clock, user, identifier)
