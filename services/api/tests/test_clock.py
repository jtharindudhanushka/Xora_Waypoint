from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.clock import COLOMBO, Clock
from app.models import Base


def _session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_real_time_when_no_demo_set() -> None:
    fixed = datetime(2026, 10, 4, 8, 0, tzinfo=UTC)
    clock = Clock(_session(), real_now=lambda: fixed)
    assert clock.now() == fixed
    assert not clock.is_demo


def test_demo_clock_runs_forward_from_the_set_point() -> None:
    session = _session()
    real = [datetime(2026, 10, 4, 8, 0, tzinfo=UTC)]
    clock = Clock(session, real_now=lambda: real[0])
    demo = datetime(2026, 4, 6, 14, 50, tzinfo=COLOMBO)
    clock.set_demo(demo)
    session.commit()
    assert clock.now() == demo.astimezone(UTC)
    real[0] += timedelta(minutes=15)
    assert clock.local_now().strftime("%a %H:%M") == "Mon 15:05"
