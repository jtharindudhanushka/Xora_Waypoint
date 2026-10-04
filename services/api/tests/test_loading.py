# ruff: noqa: F811
"""Synthetic dock regressions, BR-24/25/27/31/54/55; no organiser data."""

import uuid
from datetime import time

from sqlalchemy import select

from app.models import Hold, Order, Plan, PlanAck, Stop, StopOrder, User
from tests.conftest import auth_header
from tests.test_planning import planning_data  # noqa: F401
from tests.test_repair import options, shortfall_data  # noqa: F401
from tests.test_sync import DAY, _version, event, field, sync  # noqa: F401


def read(client, identifier):
    response = client.get(f"/api/v1/dock/trips/{identifier}", headers=auth_header(client, "loader"))
    assert response.status_code == 200, response.text
    return response.json()


def test_br24_reverse_load_order_br25_departures(client, session_maker, field):
    with session_maker() as db:
        stop = Stop(
            trip_id=uuid.UUID(field["trip"]), seq=2, outlet_code="TEST1", plan_arrival=time(6)
        )
        db.add(stop)
        db.flush()
        order = Order(
            ref="TEST-002",
            outlet_code="TEST1",
            brand="Fresh",
            temp_requirement="ambient",
            delivery_date=DAY,
            units=7,
            weight_kg=14,
            volume_m3=0.2,
        )
        db.add(order)
        db.flush()
        db.add(StopOrder(stop_id=stop.id, order_id=order.id, planned_cases=7))
        db.commit()
    detail = read(client, field["trip"])
    assert [line["stop_seq"] for line in detail["load_list"]] == [2, 1]
    assert [line["cases"] for line in detail["load_list"]] == [7, 205]
    assert detail["load_list"][0]["temperature"] == "ambient"
    response = client.get(
        "/api/v1/dock/trips?date=2026-04-07", headers=auth_header(client, "loader")
    )
    assert response.status_code == 200
    assert response.json()["trips"][0]["cases"] == 212


def test_br55_depot_and_role_scope(client, session_maker, field):
    assert (
        client.get("/api/v1/dock/trips", headers=auth_header(client, "driver")).status_code == 403
    )
    with session_maker() as db:
        plan = db.get(Plan, uuid.UUID(field["plan_id"].hex))
        plan.depot = "OtherDepot"
        db.commit()
    response = client.get(
        f"/api/v1/dock/trips/{field['trip']}", headers=auth_header(client, "loader")
    )
    assert response.status_code == 403
    assert response.json()["rule_id"] == "BR-55"
    assert (
        client.get(
            "/api/v1/dock/trips?date=2026-04-07", headers=auth_header(client, "loader")
        ).json()["trips"]
        == []
    )


def test_br27_hold_shown_br54_loaded_projection(client, field):
    results = sync(
        client,
        "loader",
        event(
            "shortfall_reported",
            "trip",
            field["trip"],
            field["version"],
            order_id=field["order"],
            kind="missing",
            qty=2,
            reason="short_from_chiller_pick",
        ),
    )
    assert results[0]["status"] == "accepted"
    detail = read(client, field["trip"])
    assert detail["on_hold"] and detail["load_status"] == "on_hold"
    assert detail["hold"]["qty"] == 2
    assert detail["hold"]["planned_cases"] == 205
    result = sync(client, "loader", event("trip_loaded", "trip", field["trip"], field["version"]))
    assert result[0]["code"] == "TRIP_ON_HOLD"


def test_br31_newer_version_requires_ack_and_old_link_resolves(client, session_maker, field):
    with session_maker() as db:
        plan = db.get(Plan, field["plan_id"])
        parent = plan.versions[0]
        version, trip, _ = _version(db, plan, 2, 203, parent)
        db.commit()
        new_id = str(trip.id)
        version_id = version.id
    detail = read(client, field["trip"])
    assert detail["id"] == new_id
    assert detail["version"]["needs_acknowledgement"]
    assert [(c["before"], c["after"]) for c in detail["changes"]] == [(205, 203)]
    with session_maker() as db:
        user = db.scalar(select(User).where(User.role == "loader"))
        from datetime import UTC, datetime

        db.add(
            PlanAck(
                version_id=version_id, user_id=user.id, acked_at=datetime(2026, 4, 7, tzinfo=UTC)
            )
        )
        db.commit()
    assert not read(client, field["trip"])["version"]["needs_acknowledgement"]


def test_br30_br31_real_repair_ack_releases_then_loaded(client, session_maker, shortfall_data):
    body = options(client, shortfall_data)
    option = next(o for o in body["options"] if o["label"] == "A")
    repaired = client.post(
        f"/api/v1/shortfalls/{shortfall_data[0]}/apply",
        headers=auth_header(client, "dispatcher"),
        json={"option_id": option["id"]},
    )
    assert repaired.status_code == 200, repaired.text
    detail = read(client, shortfall_data[1])
    assert detail["on_hold"] and detail["version"]["needs_acknowledgement"]
    assert any(c["before"] == 10 and c["after"] == 8 for c in detail["changes"])
    assert any(c["before"] == 0 and c["after"] == 2 for c in detail["changes"])
    result = sync(
        client, "loader", event("trip_acknowledged", "trip", detail["id"], detail["version"]["id"])
    )
    assert result[0]["status"] == "accepted"
    assert not read(client, shortfall_data[1])["on_hold"]
    result = sync(
        client, "loader", event("trip_loaded", "trip", detail["id"], detail["version"]["id"])
    )
    assert result[0]["status"] == "accepted"
    assert read(client, shortfall_data[1])["load_status"] == "loaded"
    with session_maker() as db:
        assert db.scalar(select(Hold)).status == "released"
