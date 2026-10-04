"""Authentication use cases."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import DomainError
from app.core.security import create_access_token, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import TokenOut, UserOut


class InvalidCredentialsError(DomainError):
    status_code = 401
    title = "Invalid credentials"


def authenticate(session: Session, settings: Settings, email: str, password: str) -> TokenOut:
    user = session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    # Same error for unknown email and wrong password: don't reveal which accounts exist.
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("INVALID_CREDENTIALS", "Email or password is incorrect")
    token = create_access_token(
        str(user.id),
        {"role": user.role},
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        ttl_hours=settings.jwt_ttl_hours,
    )
    return TokenOut(
        access_token=token,
        expires_in=settings.jwt_ttl_hours * 3600,
        user=UserOut.model_validate(user),
    )
