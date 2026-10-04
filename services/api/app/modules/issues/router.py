import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends

from app.core.deps import ClockDep, DbDep, require_roles
from app.modules.auth.models import User
from app.modules.issues import service
from app.modules.issues.repository import Repository
from app.modules.issues.schemas import IssueOut, ResolveIn
from app.modules.planning.service import repository

router = APIRouter(tags=["issues"])
Dispatcher = Annotated[User, Depends(require_roles("dispatcher"))]


@router.get("/issues", response_model=list[IssueOut])
def list_issues(
    db: DbDep, clock: ClockDep, user: Dispatcher, status: Literal["open", "resolved"] = "open"
) -> list[IssueOut]:
    repo = Repository(db, repository(db, user).depot)
    return [service.issue_out(repo, clock, row) for row in repo.list(status)]


@router.get("/issues/{identifier}", response_model=IssueOut)
def get_issue(identifier: uuid.UUID, db: DbDep, clock: ClockDep, user: Dispatcher) -> IssueOut:
    repo = Repository(db, repository(db, user).depot)
    return service.issue_out(repo, clock, repo.issue(identifier))


@router.post("/issues/{identifier}/resolve", response_model=IssueOut)
async def resolve(
    identifier: uuid.UUID, body: ResolveIn, db: DbDep, clock: ClockDep, user: Dispatcher
) -> IssueOut:
    repo = Repository(db, repository(db, user).depot)
    return await service.resolve(repo, user, clock, identifier, body)
