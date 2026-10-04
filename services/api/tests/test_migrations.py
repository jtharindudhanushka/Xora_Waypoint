"""The migration chain must build the same schema as the models (no drift)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Config]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    get_settings.cache_clear()
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    yield cfg
    get_settings.cache_clear()


def test_upgrade_downgrade_and_no_model_drift(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.check(alembic_cfg)  # raises if models and migrations disagree
    command.downgrade(alembic_cfg, "base")
