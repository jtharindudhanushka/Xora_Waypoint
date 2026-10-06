"""Production must never run with the placeholder JWT secret (anyone could mint tokens)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("secret", ["change-me-to-a-long-random-string", "short"])
def test_production_rejects_weak_jwt_secret(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, environment="production", jwt_secret=secret)


def test_production_accepts_real_secret_and_development_keeps_default():
    Settings(_env_file=None, environment="production", jwt_secret="x" * 40)
    assert Settings(_env_file=None, environment="development").jwt_secret.startswith("change-me")
