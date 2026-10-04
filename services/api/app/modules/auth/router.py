from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbDep, SettingsDep
from app.modules.auth.schemas import LoginRequest, TokenOut, UserOut
from app.modules.auth.service import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut, summary="Sign in (X1)")
def login(body: LoginRequest, db: DbDep, settings: SettingsDep) -> TokenOut:
    return authenticate(db, settings, body.email, body.password)


@router.get("/me", response_model=UserOut, summary="Current user and scope")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
