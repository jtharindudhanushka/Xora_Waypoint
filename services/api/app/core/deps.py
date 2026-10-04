"""Shared FastAPI dependencies: settings, DB session, clock, current user and role guards."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import DomainError, ForbiddenError
from app.core.security import InvalidTokenError, decode_access_token
from app.modules.auth.models import User

_bearer = HTTPBearer(auto_error=False)


class UnauthenticatedError(DomainError):
    status_code = 401
    title = "Not signed in"


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
DbDep = Annotated[Session, Depends(get_db)]


def get_clock(db: DbDep) -> Clock:
    return Clock(db)


ClockDep = Annotated[Clock, Depends(get_clock)]


def get_current_user(
    db: DbDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthenticatedError("UNAUTHENTICATED", "Sign in to continue")
    try:
        payload = decode_access_token(
            credentials.credentials, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise UnauthenticatedError("INVALID_TOKEN", "Your session has expired") from exc
    if user is None:
        raise UnauthenticatedError("INVALID_TOKEN", "Your session has expired")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str) -> Callable[[User], User]:
    """Route guard: `user: Annotated[User, Depends(require_roles("dispatcher"))]` (BR-55)."""

    def guard(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError(
                "ROLE_FORBIDDEN", f"This action needs role: {', '.join(roles)}", rule_id="BR-55"
            )
        return user

    return guard
