"""Test fixtures: an in-memory SQLite database with synthetic fixtures (no competition data)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.db import get_db
from app.core.security import hash_password
from app.main import create_app
from app.models import Base, Depot, User

PASSWORD = "test-pass-123"
TEST_SETTINGS = Settings(jwt_secret="test-secret-that-is-at-least-32-bytes-long!")


@pytest.fixture
def session_maker() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as session:
        session.add(Depot(name="TestDepot"))
        session.flush()
        for role in ("dispatcher", "loader", "driver", "store_manager"):
            session.add(
                User(
                    email=f"{role}@test.local",
                    name=role.title(),
                    role=role,
                    password_hash=hash_password(PASSWORD),
                    depot="TestDepot",
                )
            )
        session.commit()
    return maker


@pytest.fixture
def client(session_maker: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app(TEST_SETTINGS)

    def _db() -> Iterator[Session]:
        with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as test_client:
        yield test_client


def token_for(client: TestClient, role: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"email": f"{role}@test.local", "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def auth_header(client: TestClient, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(client, role)}"}
