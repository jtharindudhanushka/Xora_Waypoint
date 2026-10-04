"""Synthetic live operations tests; field endpoints and event records stay untouched."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models import ClockSetting, District, Order
from app.modules.ops.models import ExceptionItem, Notification
from app.modules.planning.models import PlanVersion, Stop
from tests.conftest import auth_header
from tests.test_planning import DAY, generate, planning_data  # noqa: F401

pytestmark = pytest.mark.usefixtures("planning_data")


def published(client):
    plan = generate(client)
    headers = auth_header(client, "dispatcher")
    client.post(
        f"/api/v1/plan-versions/{plan['id']}/deferrals/confirm",
        headers=headers,
        json={
            "items": [{"deferral_id": d["id"], "reason": "No capacity"} for d in plan["deferrals"]]
        },
    )
    result = client.post(
        f"/api/v1/plan-versions/{plan['id']}/publish",
        headers=headers,
        json={"accept_late_risk": True},
    )
    assert result.status_code == 200, result.text
    return plan, headers


def test_br50_dead_zone_is_pending_and_seen_stays_seen(client, session_maker):
    _plan, headers = published(client)
    with session_maker() as db:
        district = db.get(District, "TestDistrict")
        district.is_dead_zone = True
        setting = db.get(ClockSetting, 1)
        setting.demo_now = datetime(2026, 4, 7, 0, 45, tzinfo=UTC)
        setting.set_at = datetime.now(UTC)
        db.commit()
    result = client.get(f"/api/v1/ops/{DAY}", headers=headers)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["pending_sync"] == 1
    assert body["trips"][0]["stops"][0]["status"] == "pending_sync"
    assert body["exceptions"][0]["impact"] == 0
    identifier = body["exceptions"][0]["id"]
    assert (
        client.post(f"/api/v1/exceptions/{identifier}/apply-fix", headers=headers).status_code
        == 200
    )
    again = client.get(f"/api/v1/ops/{DAY}", headers=headers).json()
    assert not again["exceptions"]
    with session_maker() as db:
        assert len(list(db.scalars(select(ExceptionItem)))) == 1


def test_br48_ranking_and_br49_notice_is_not_duplicated(client, session_maker):
    plan, headers = published(client)
    with session_maker() as db:
        stop = db.get(Stop, uuid.UUID(plan["trips"][0]["stops"][0]["id"]))
        stop.at_risk = True
        db.commit()
    first = client.get(f"/api/v1/ops/{DAY}", headers=headers).json()
    assert first["exceptions"][0]["kind"] == "late_risk"
    assert first["exceptions"][0]["impact"] > 0
    client.get(f"/api/v1/ops/{DAY}", headers=headers)
    with session_maker() as db:
        assert (
            len(list(db.scalars(select(Notification).where(Notification.kind == "eta_late")))) == 1
        )


def test_br55_ops_needs_dispatcher_and_published_plan(client):
    assert (
        client.get(f"/api/v1/ops/{DAY}", headers=auth_header(client, "driver")).status_code == 403
    )
    assert (
        client.get(f"/api/v1/ops/{DAY}", headers=auth_header(client, "dispatcher")).status_code
        == 404
    )


def test_br23_br48_swap_publishes_new_version_and_keeps_original(client, session_maker):
    with session_maker() as db:
        db.add(
            Order(
                ref="TEST-SECOND",
                outlet_code="TEST1",
                brand="Fresh",
                temp_requirement="chilled",
                delivery_date=DAY,
                units=10,
                weight_kg=100,
                volume_m3=1,
                status="placed",
                days_since_last_served=1,
            )
        )
        db.commit()
    plan, headers = published(client)
    trip = plan["trips"][0]
    assert len(trip["stops"]) == 2
    identifier = uuid.uuid4()
    with session_maker() as db:
        db.add(
            ExceptionItem(
                id=identifier,
                kind="late_risk",
                impact=10,
                title="Test swap",
                entity_type="stop",
                entity_id=trip["stops"][1]["id"],
                suggested_fix={"action": "swap_stops", "left": 1, "right": 2},
                status="open",
                created_at=datetime(2026, 4, 7, tzinfo=UTC),
            )
        )
        db.commit()
    result = client.post(f"/api/v1/exceptions/{identifier}/apply-fix", headers=headers)
    assert result.status_code == 200, result.text
    with session_maker() as db:
        old = db.get(PlanVersion, uuid.UUID(plan["id"]))
        new = db.get(PlanVersion, uuid.UUID(result.json()["version_id"]))
        assert new.number == old.number + 1
        assert new.status == old.status == "published"
        assert [so.order_id for s in new.trips[0].stops for so in s.orders] == list(
            reversed([so.order_id for s in old.trips[0].stops for so in s.orders])
        )
    assert (
        client.post(f"/api/v1/exceptions/{identifier}/apply-fix", headers=headers).status_code
        == 409
    )


def test_superseded_version_stop_exceptions_are_closed(client, session_maker):
    """QA B4: /exceptions must not keep listing stops a newer version replaced."""
    with session_maker() as db:
        db.add(
            Order(
                ref="TEST-SECOND",
                outlet_code="TEST1",
                brand="Fresh",
                temp_requirement="chilled",
                delivery_date=DAY,
                units=10,
                weight_kg=100,
                volume_m3=1,
                status="placed",
                days_since_last_served=1,
            )
        )
        db.commit()
    plan, headers = published(client)
    trip = plan["trips"][0]
    swap, stale = uuid.uuid4(), uuid.uuid4()
    with session_maker() as db:
        for identifier, stop, fix in (
            (swap, trip["stops"][1], {"action": "swap_stops", "left": 1, "right": 2}),
            (stale, trip["stops"][0], {}),
        ):
            db.add(
                ExceptionItem(
                    id=identifier,
                    kind="late_risk",
                    impact=10,
                    title="Superseded",
                    entity_type="stop",
                    entity_id=stop["id"],
                    suggested_fix=fix,
                    status="open",
                    created_at=datetime(2026, 4, 7, tzinfo=UTC),
                )
            )
        db.commit()
    assert client.post(f"/api/v1/exceptions/{swap}/apply-fix", headers=headers).status_code == 200
    assert client.get(f"/api/v1/ops/{DAY}", headers=headers).status_code == 200
    listed = {e["id"] for e in client.get("/api/v1/exceptions", headers=headers).json()}
    assert str(stale) not in listed
    with session_maker() as db:
        assert db.get(ExceptionItem, stale).status == "resolved"
