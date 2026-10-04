"""Synthetic sync, bootstrap and driver-day tests (docs/07 › Testing offline)."""

import uuid
from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import func, select

from app.models import (
    ClockSetting,
    District,
    DriverNote,
    Event,
    Hold,
    Issue,
    Order,
    OrderLine,
    Outlet,
    OutletProfile,
    Plan,
    PlanVersion,
    Product,
    Receipt,
    Shortfall,
    Stop,
    StopOrder,
    Trip,
    User,
    Vehicle,
)
from tests.conftest import auth_header

DAY = date(2026, 4, 7)
EVENT_TIME = "2026-04-07T06:52:00+05:30"


def _version(db, plan, number, cases, parent=None):
    version = PlanVersion(
        plan_id=plan.id,
        number=number,
        status="published",
        parent_version_id=parent.id if parent else None,
        published_at=datetime(2026, 4, 6, 11, tzinfo=UTC),
    )
    db.add(version)
    db.flush()
    trip = Trip(
        version_id=version.id,
        vehicle_code="TESTV",
        trip_no=1,
        brand="Fresh",
        district="TestDistrict",
        lane="predawn",
        planned_depart=time(4, 40),
        plan_minutes=120,
    )
    db.add(trip)
    db.flush()
    stop = Stop(
        trip_id=trip.id,
        seq=1,
        outlet_code="TEST1",
        plan_arrival=time(5, 30),
        likely_from=time(5, 35),
        likely_to=time(5, 55),
    )
    db.add(stop)
    db.flush()
    order = db.scalar(select(Order).where(Order.ref == "TEST-001"))
    db.add(StopOrder(stop_id=stop.id, order_id=order.id, planned_cases=cases))
    db.flush()
    return version, trip, stop


@pytest.fixture
def field(session_maker):
    with session_maker() as db:
        db.add(
            District(
                name="TestDistrict",
                depot="TestDepot",
                road_class="urban",
                free_flow_kmh=30,
                depot_to_district_km=12,
                depot_to_district_min=24,
                inter_stop_km=4,
                inter_stop_min=8,
            )
        )
        db.add(
            Outlet(
                code="TEST1",
                brand="Fresh",
                district="TestDistrict",
                depot="TestDepot",
                dock_type="street",
                parking_constraint="normal",
                window_open=time(5),
                window_close=time(8),
            )
        )
        db.add(
            Vehicle(
                code="TESTV",
                type="van",
                temp="reefer",
                weight_cap_kg=1000,
                volume_cap_m3=10,
                fuel_type="diesel",
                km_per_l=10,
                weekly_fuel_quota_l=100,
                depot="TestDepot",
            )
        )
        db.add(Product(id="test-milk", name="Test milk", brand="Fresh", is_chilled=True))
        db.flush()
        db.add(OutletProfile(outlet_code="TEST1", split_rule="any", access_note="Side lane"))
        db.add(DriverNote(outlet_code="TEST1", for_date=DAY, text="Shutter shut till 07:00"))
        order = Order(
            ref="TEST-001",
            outlet_code="TEST1",
            brand="Fresh",
            temp_requirement="chilled",
            delivery_date=DAY,
            units=205,
            weight_kg=100,
            volume_m3=1,
            status="planned",
        )
        db.add(order)
        db.flush()
        db.add(OrderLine(order_id=order.id, product_id="test-milk", qty_ordered=205))
        plan = Plan(depot="TestDepot", operating_date=DAY)
        db.add(plan)
        db.flush()
        version, trip, stop = _version(db, plan, 1, 205)
        for user in db.scalars(select(User)):
            if user.role == "driver":
                user.vehicle_code = "TESTV"
        db.add(
            ClockSetting(
                id=1, demo_now=datetime(2026, 4, 7, 1, 22, tzinfo=UTC), set_at=datetime.now(UTC)
            )
        )
        db.commit()
        return {
            "plan_id": plan.id,
            "version": str(version.id),
            "trip": str(trip.id),
            "stop": str(stop.id),
            "order": str(order.id),
        }


def event(event_type, entity_type, entity_id, version, **payload):
    return {
        "event_id": str(uuid.uuid4()),
        "type": event_type,
        "entity": {"type": entity_type, "id": entity_id},
        "plan_version_id": version,
        "event_time": EVENT_TIME,
        "payload": payload,
    }


def sync(client, role, *events):
    response = client.post(
        "/api/v1/sync",
        headers=auth_header(client, role),
        json={"device_id": f"{role}-phone", "events": list(events)},
    )
    assert response.status_code == 200, response.text
    return response.json()["results"]


def ack(field, version=None):
    version = version or field["version"]
    return event("trip_acknowledged", "trip", field["trip"], version)


def outcome(field, cases, version=None):
    return event(
        "outcome_recorded",
        "stop",
        field["stop"],
        version or field["version"],
        outcome="delivered",
        receiver_name="S. Jayasinghe",
        orders=[{"order_id": field["order"], "cases": cases}],
    )


def test_br36_same_batch_twice_is_duplicate_and_applied_once(client, field, session_maker):
    batch = [ack(field), event("arrived", "stop", field["stop"], field["version"])]
    first = sync(client, "driver", *batch)
    assert [r["status"] for r in first] == ["accepted", "accepted"]
    second = sync(client, "driver", *batch)
    assert [r["status"] for r in second] == ["duplicate", "duplicate"]
    with session_maker() as db:
        assert db.scalar(select(func.count()).select_from(Event)) == 2
        stored = db.scalar(select(Event).where(Event.type == "arrived"))
        assert stored.event_time == datetime(2026, 4, 7, 1, 22)  # device time kept (BR-37)
        assert db.get(Stop, uuid.UUID(field["stop"])).status == "in_transit"


def test_br32_arrival_before_acknowledgement_is_rejected(client, field, session_maker):
    result = sync(client, "driver", event("arrived", "stop", field["stop"], field["version"]))
    assert result[0]["status"] == "rejected"
    assert result[0]["rule_id"] == "BR-32"
    with session_maker() as db:
        assert db.scalar(select(func.count()).select_from(Event)) == 0


def test_br52_count_conflict_keeps_both_records(client, field, session_maker):
    with session_maker() as db:
        store = db.scalar(select(User).where(User.role == "store_manager"))
        db.add(
            Receipt(
                order_id=uuid.UUID(field["order"]),
                confirmed_by=store.id,
                confirmed_at=datetime(2026, 4, 7, 1, 40, tzinfo=UTC),
                total_cases=200,
            )
        )
        db.commit()
    results = sync(client, "driver", ack(field), outcome(field, 205))
    assert results[1]["status"] == "conflict"
    with session_maker() as db:
        issue = db.get(Issue, uuid.UUID(results[1]["conflict_id"]))
        assert (issue.kind, issue.driver_qty, issue.store_qty) == ("count_conflict", 205, 200)
        assert (results[1]["driver_qty"], results[1]["store_qty"]) == (205, 200)
        assert str(issue.driver_event_id) == results[1]["event_id"]
        assert db.scalar(select(Receipt)).total_cases == 200  # nothing overwritten


def test_matching_count_is_accepted(client, field, session_maker):
    results = sync(client, "driver", ack(field), outcome(field, 205))
    assert [r["status"] for r in results] == ["accepted", "accepted"]
    with session_maker() as db:
        assert db.get(Stop, uuid.UUID(field["stop"])).status == "delivered"
        assert db.scalar(select(Order)).status == "delivered"


def test_br26_br27_shortfall_creates_hold_and_blocks_loading(client, field, session_maker):
    report = event(
        "shortfall_reported",
        "trip",
        field["trip"],
        field["version"],
        order_id=field["order"],
        kind="missing",
        qty=2,
        reason="short_from_chiller_pick",
    )
    assert sync(client, "loader", report)[0]["status"] == "accepted"
    loaded = sync(client, "loader", event("trip_loaded", "trip", field["trip"], field["version"]))
    assert loaded[0]["rule_id"] == "BR-27"
    with session_maker() as db:
        shortfall = db.scalar(select(Shortfall))
        assert (shortfall.qty, shortfall.reason) == (2, "short_from_chiller_pick")
        assert db.scalar(select(Hold)).status == "active"
    today = client.get("/api/v1/vehicles/TESTV/today", headers=auth_header(client, "driver")).json()
    trip = today["trips"][0]
    assert trip["on_hold"]
    assert trip["stops"][0]["orders"][0]["known_shortfall"]["qty"] == 2  # BR-34 pre-fill


def test_br26_invalid_quantity_is_rejected(client, field):
    report = event(
        "shortfall_reported",
        "trip",
        field["trip"],
        field["version"],
        order_id=field["order"],
        kind="missing",
        qty=999,
        reason="other",
    )
    assert sync(client, "loader", report)[0]["rule_id"] == "BR-26"


def test_br31_loader_ack_of_repaired_version_releases_hold(client, field, session_maker):
    report = event(
        "shortfall_reported",
        "trip",
        field["trip"],
        field["version"],
        order_id=field["order"],
        kind="missing",
        qty=2,
        reason="not_on_dock",
    )
    sync(client, "loader", report)
    assert sync(client, "loader", ack(field))[0]["status"] == "accepted"
    with session_maker() as db:
        assert db.scalar(select(Hold)).status == "active"  # acking v1 resolves nothing
        v1 = db.get(PlanVersion, uuid.UUID(field["version"]))
        v1.status = "superseded"
        plan = db.get(Plan, field["plan_id"])
        v2, trip2, _ = _version(db, plan, 2, 203, parent=v1)
        db.scalar(select(Hold)).trip_id = trip2.id  # repair moves the hold (dev2-handover §5)
        db.commit()
        v2_id, trip2_id = str(v2.id), str(trip2.id)
    released = sync(client, "loader", event("trip_acknowledged", "trip", trip2_id, v2_id))
    assert released[0]["status"] == "accepted"
    with session_maker() as db:
        hold = db.scalar(select(Hold))
        assert hold.status == "released"
        assert hold.released_by is not None


def test_br53_stale_plan_event_is_stored_and_raises_conflict(client, field, session_maker):
    sync(client, "driver", ack(field))
    with session_maker() as db:
        v1 = db.get(PlanVersion, uuid.UUID(field["version"]))
        v1.status = "superseded"
        _version(db, db.get(Plan, field["plan_id"]), 2, 203, parent=v1)
        db.commit()
    result = sync(client, "driver", outcome(field, 205))
    assert result[0]["status"] == "conflict"
    with session_maker() as db:
        assert db.get(Issue, uuid.UUID(result[0]["conflict_id"])).kind == "stale_plan"
        assert db.get(Event, uuid.UUID(result[0]["event_id"])) is not None


def test_vehicle_today_has_two_clocks_notes_and_ack_state(client, field):
    headers = auth_header(client, "driver")
    today = client.get("/api/v1/vehicles/TESTV/today", headers=headers).json()
    assert today["operating_date"] == "2026-04-07"
    assert today["version"]["number"] == 1
    assert not today["version"]["acknowledged"]
    stop = today["trips"][0]["stops"][0]
    assert (stop["plan_arrival"], stop["likely_from"], stop["likely_to"]) == (
        "05:30:00",
        "05:35:00",
        "05:55:00",
    )
    assert stop["store_note"] == "Shutter shut till 07:00"
    assert stop["access_note"] == "Side lane"
    assert stop["orders"][0]["lines"][0]["name"] == "Test milk"
    sync(client, "driver", ack(field))
    after = client.get("/api/v1/vehicles/TESTV/today", headers=headers).json()
    assert after["version"]["acknowledged"]


def test_br55_driver_sees_only_own_vehicle(client, field, session_maker):
    with session_maker() as db:
        db.scalar(select(User).where(User.role == "driver")).vehicle_code = None
        db.commit()
    response = client.get("/api/v1/vehicles/TESTV/today", headers=auth_header(client, "driver"))
    assert response.status_code == 403
    store = client.post(
        "/api/v1/sync",
        headers=auth_header(client, "store_manager"),
        json={"device_id": "x", "events": []},
    )
    assert store.status_code == 403


def test_bootstrap_caches_the_day_for_driver_and_loader(client, field):
    driver = client.get("/api/v1/sync/bootstrap", headers=auth_header(client, "driver")).json()
    assert [v["vehicle_code"] for v in driver["vehicles"]] == ["TESTV"]
    assert driver["user"]["role"] == "driver"
    loader = client.get("/api/v1/sync/bootstrap", headers=auth_header(client, "loader")).json()
    assert [v["vehicle_code"] for v in loader["vehicles"]] == ["TESTV"]
