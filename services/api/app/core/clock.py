"""The single source of "now" for domain code (BR-56, ADR-0006).

When a demo time is set, the clock runs forward from it in real time, so countdowns and timers
behave naturally while the walkthrough still happens on Mon 6 / Tue 7 Apr 2026.
All datetimes are stored in UTC; presentation converts to Asia/Colombo.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.modules.ops.models import ClockSetting

COLOMBO = ZoneInfo("Asia/Colombo")


def ensure_utc(value: datetime) -> datetime:
    """Normalise a datetime to aware UTC (SQLite returns naive values that were stored as UTC)."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Clock:
    def __init__(self, session: Session, real_now: Callable[[], datetime] | None = None) -> None:
        self._session = session
        self._real_now = real_now or (lambda: datetime.now(UTC))

    def _setting(self) -> ClockSetting | None:
        return self._session.get(ClockSetting, 1)

    @property
    def is_demo(self) -> bool:
        setting = self._setting()
        return setting is not None and setting.demo_now is not None

    def now(self) -> datetime:
        """Current time, aware, in UTC."""
        real = self._real_now()
        setting = self._setting()
        if setting is None or setting.demo_now is None or setting.set_at is None:
            return real
        return ensure_utc(setting.demo_now) + (real - ensure_utc(setting.set_at))

    def local_now(self) -> datetime:
        return self.now().astimezone(COLOMBO)

    def set_demo(self, demo_now: datetime | None, set_by: object | None = None) -> None:
        setting = self._setting() or ClockSetting(id=1)
        setting.demo_now = ensure_utc(demo_now) if demo_now else None
        setting.set_at = self._real_now()
        setting.set_by = set_by  # type: ignore[assignment]
        self._session.merge(setting)
