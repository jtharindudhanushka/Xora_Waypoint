"""GET/PUT /clock — read the operating time; the dispatcher sets the demo time (BR-56)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.clock import COLOMBO
from app.core.deps import ClockDep, DbDep, require_roles
from app.modules.auth.models import User
from app.modules.stream.broker import broker

router = APIRouter(prefix="/clock", tags=["clock"])


class ClockOut(BaseModel):
    now: datetime  # Asia/Colombo, with offset
    is_demo: bool


class ClockSet(BaseModel):
    demo_now: datetime | None  # null returns to real time


@router.get("", response_model=ClockOut, summary="Current operating time")
def read_clock(clock: ClockDep) -> ClockOut:
    return ClockOut(now=clock.local_now(), is_demo=clock.is_demo)


@router.put("", response_model=ClockOut, summary="Set or clear the demo time (dispatcher)")
async def set_clock(
    body: ClockSet,
    clock: ClockDep,
    db: DbDep,
    user: Annotated[User, Depends(require_roles("dispatcher"))],
) -> ClockOut:
    demo = body.demo_now
    if demo is not None and demo.tzinfo is None:
        demo = demo.replace(tzinfo=COLOMBO)  # bare times are read as Sri Lanka time
    clock.set_demo(demo, set_by=user.id)
    db.commit()
    out = ClockOut(now=clock.local_now(), is_demo=clock.is_demo)
    await broker.publish("clock.changed", out.model_dump(mode="json"))
    return out
