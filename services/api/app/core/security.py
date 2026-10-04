"""Password hashing (bcrypt) and access tokens (JWT, HS256)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# ── Access tokens (JWT) ──────────────────────────────────────────────────────
class InvalidTokenError(Exception):
    pass


def create_access_token(
    subject: str, claims: dict[str, Any], *, secret: str, algorithm: str, ttl_hours: int
) -> str:
    issued = datetime.now(UTC)
    payload = {"sub": subject, "iat": issued, "exp": issued + timedelta(hours=ttl_hours), **claims}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, *, secret: str, algorithm: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    return payload
