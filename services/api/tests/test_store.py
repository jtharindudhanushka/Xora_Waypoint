"""Synthetic Store fixtures; no competition rows or derivatives (BR-40–47/54/55)."""

import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select

from app.core.clock import Clock
from app.core.deps import get_clock
from app.models import CalendarDay, District, Order, OrderLine, Outlet, Product, User
from app.modules.catalog.models import UsualQuantity
from app.modules.ops.models import Notification
from app.modules.receipts.models import Issue, Receipt, ReceiptLine
from app.modules.sync.models import Event
from tests.conftest import auth_header

DAY = date(2026, 4, 7)
NOW = datetime(2026, 4, 6, 9, 20, tzinfo=UTC)


@pytest.fixture
def store_data(client, session_maker):
    with session_maker() as db:
        db.add(
            District(
                name="StoreDistrict",
                depot="TestDepot",
                road_class="urban",
                free_flow_kmh=30,
                depot_to_district_km=12,
                depot_to_district_min=24,
                inter_stop_km=4,
                inter_stop_min=8,
            )
        )
        for code in ("STORE1", "OTHER"):
            db.add(
                Outlet(
                    code=code,
                    brand="Fresh",
                    district="StoreDistrict",
                    depot="TestDepot",
                    dock_type="street",
                    parking_constraint="normal",
                    window_open=time(5),
                    window_close=time(8),
                )
            )
        db.add_all(
            [
                Product(id="test-milk", name="Test milk", brand="Fresh", is_chilled=True),
                Product(id="test-fish", name="Test fish", brand="Fresh", is_chilled=True),
                Product(id="test-rice", name="Test rice", brand="Fresh", is_chilled=False),
            ]
        )
        db.flush()
        user = db.scalar(select(User).where(User.role == "store_manager"))
        user.outlet_code = "STORE1"
        db.add(UsualQuantity(outlet_code="STORE1", product_id="test-milk", usual_cases=20))
        for delta in range(5):
            day = DAY + timedelta(days=delta)
            year, week, _ = day.isocalendar()
            db.add(
                CalendarDay(
                    date=day,
                    dow=day.weekday(),
                    iso_year=year,
                    iso_week=week,
                    is_payday=False,
                    festival_ramp=0,
                    is_holiday=delta == 1,
                    monsoon=False,
                    is_operating=delta != 1,
                )
            )
        order = Order(
            ref="SYN-DRAFT",
            outlet_code="STORE1",
            brand="Fresh",
            temp_requirement="chilled",
            delivery_date=DAY,
            units=28,
            weight_kg=280,
            volume_m3=2.8,
            status="draft",
            source="app",
        )
        db.add(order)
        db.flush()
        db.add_all(
            [
                OrderLine(order_id=order.id, product_id="test-milk", qty_ordered=20),
                OrderLine(order_id=order.id, product_id="test-fish", qty_ordered=8),
            ]
        )
        db.commit()

    def fixed_clock():
        with session_maker() as db:
            return Clock(db, real_now=lambda: NOW)

    client.app.dependency_overrides[get_clock] = fixed_clock
    yield
    client.app.dependency_overrides.pop(get_clock)


def body(qty=20):
    return {
        "draft_ref": "SYN-DRAFT",
        "request_id": str(uuid.uuid4()),
        "lines": [{"product_id": "test-milk", "qty": qty}, {"product_id": "test-fish", "qty": 8}],
    }


def test_br40_br56_before_cutoff_and_idempotent_draft(client, store_data, session_maker):
    headers = auth_header(client, "store_manager")
    request = body()
    response = client.post("/api/v1/orders", headers=headers, json=request)
    assert response.status_code == 200, response.text
    order = response.json()[0]
    assert order["delivery_date"] == "2026-04-07"
    assert order["submission_status"] == "placed"
    again = client.post("/api/v1/orders", headers=headers, json=request)
    assert again.json() == response.json()
    with session_maker() as db:
        assert len(list(db.scalars(select(Event).where(Event.type == "order.placed")))) == 1


@pytest.mark.parametrize("local_time", ["16:00:00", "16:01:00"])
def test_br40_at_cutoff_skips_next_day_and_nonoperating(
    client, store_data, session_maker, local_time
):
    instant = datetime.fromisoformat(f"2026-04-06T{local_time}+05:30")

    def fixed():
        with session_maker() as db:
            return Clock(db, real_now=lambda: instant)

    client.app.dependency_overrides[get_clock] = fixed
    response = client.post(
        "/api/v1/orders", headers=auth_header(client, "store_manager"), json=body()
    )
    assert response.status_code == 200, response.text
    assert response.json()[0]["delivery_date"] == "2026-04-09"


def test_br42_unusual_requires_explicit_confirmation_without_write(
    client, store_data, session_maker
):
    headers = auth_header(client, "store_manager")
    request = body(61)
    checked = client.post("/api/v1/orders/check", headers=headers, json={"lines": request["lines"]})
    assert checked.json()["warnings"][0]["usual_qty"] == 20
    rejected = client.post("/api/v1/orders", headers=headers, json=request)
    assert rejected.status_code == 422
    assert rejected.json()["rule_id"] == "BR-42"
    with session_maker() as db:
        assert db.scalar(select(Order)).status == "draft"
        assert not list(db.scalars(select(Event)))
    request["confirm_unusual"] = True
    assert client.post("/api/v1/orders", headers=headers, json=request).status_code == 200


def test_br41_mixed_draft_rejected_and_zero_removes_item(client, store_data):
    headers = auth_header(client, "store_manager")
    request = body()
    request["lines"].append({"product_id": "test-rice", "qty": 2})
    assert client.post("/api/v1/orders", headers=headers, json=request).json()["rule_id"] == "BR-41"
    request["lines"] = [
        {"product_id": "test-milk", "qty": 20},
        {"product_id": "test-fish", "qty": 0},
    ]
    response = client.post("/api/v1/orders", headers=headers, json=request)
    assert response.status_code == 200
    assert len(response.json()[0]["lines"]) == 1


def delivered(session_maker):
    with session_maker() as db:
        order = db.scalar(select(Order))
        order.status = "delivered"
        for line in order.lines:
            line.qty_delivered = line.qty_ordered
        db.commit()


def test_br46_receipt_idempotent_and_driver_counts_preserved(client, store_data, session_maker):
    delivered(session_maker)
    headers = auth_header(client, "store_manager")
    response = client.post("/api/v1/orders/SYN-DRAFT/receipt", headers=headers, json={})
    assert response.status_code == 200, response.text
    assert (
        client.post("/api/v1/orders/SYN-DRAFT/receipt", headers=headers, json={}).json()
        == response.json()
    )
    with session_maker() as db:
        assert len(list(db.scalars(select(Receipt)))) == 1
        assert len(list(db.scalars(select(ReceiptLine)))) == 2
        assert [
            x.qty_delivered for x in db.scalars(select(OrderLine).order_by(OrderLine.product_id))
        ] == [8, 20]
        assert len(list(db.scalars(select(Event).where(Event.type == "receipt.confirmed")))) == 1


def test_br46_changed_counts_open_count_conflict(client, store_data, session_maker):
    delivered(session_maker)
    with session_maker() as db:
        lines = list(db.scalars(select(OrderLine)))
        counts = [{"order_line_id": str(x.id), "store_qty": x.qty_ordered - 1} for x in lines]
    response = client.post(
        "/api/v1/orders/SYN-DRAFT/receipt",
        headers=auth_header(client, "store_manager"),
        json={"lines": counts},
    )
    assert response.status_code == 200, response.text
    with session_maker() as db:
        assert db.scalar(select(Issue)).kind == "count_conflict"
    counts[0]["store_qty"] -= 1
    assert (
        client.post(
            "/api/v1/orders/SYN-DRAFT/receipt",
            headers=auth_header(client, "store_manager"),
            json={"lines": counts},
        ).status_code
        == 409
    )


def test_br47_report_confirms_good_cases_and_retries_once(client, store_data, session_maker):
    delivered(session_maker)
    with session_maker() as db:
        lines = {x.product_id: x for x in db.scalars(select(OrderLine))}
    request = {
        "request_id": str(uuid.uuid4()),
        "lines": [
            {"order_line_id": str(lines["test-milk"].id), "problem": "damaged", "qty": 2},
            {"order_line_id": str(lines["test-fish"].id), "problem": "missing", "qty": 1},
        ],
    }
    headers = auth_header(client, "store_manager")
    url = "/api/v1/orders/SYN-DRAFT/issues"
    response = client.post(url, headers=headers, json=request)
    assert response.status_code == 200, response.text
    assert client.post(url, headers=headers, json=request).json() == response.json()
    with session_maker() as db:
        assert len(list(db.scalars(select(Issue)))) == 1
        assert db.scalar(select(Issue)).kind == "store_report"
        assert db.scalar(select(Receipt)).total_cases == 25
        assert len(list(db.scalars(select(Event)))) == 2


def test_br47_invalid_line_creates_nothing(client, store_data, session_maker):
    request = {
        "request_id": str(uuid.uuid4()),
        "lines": [{"order_line_id": str(uuid.uuid4()), "problem": "missing", "qty": 1}],
    }
    response = client.post(
        "/api/v1/orders/SYN-DRAFT/issues",
        headers=auth_header(client, "store_manager"),
        json=request,
    )
    assert response.status_code == 422
    with session_maker() as db:
        assert not list(db.scalars(select(Receipt)))
        assert not list(db.scalars(select(Issue)))


def test_br55_order_role_and_outlet_scope(client, store_data, session_maker):
    assert (
        client.get("/api/v1/stores/me/orders", headers=auth_header(client, "driver")).status_code
        == 403
    )
    with session_maker() as db:
        db.scalar(select(Order)).outlet_code = "OTHER"
        db.commit()
    assert (
        client.get(
            "/api/v1/orders/SYN-DRAFT", headers=auth_header(client, "store_manager")
        ).status_code
        == 404
    )


def test_br44_notices_scoped_and_read_idempotent(client, store_data, session_maker):
    with session_maker() as db:
        notice = Notification(
            outlet_code="STORE1",
            kind="deferral",
            title="Delivery deferred",
            body="Chilled delivery moved",
            lang="en",
            created_at=NOW,
            data={"next_run": "2026-04-09"},
        )
        foreign = Notification(
            outlet_code="OTHER",
            kind="deferral",
            title="Private",
            body="Private",
            lang="en",
            created_at=NOW,
        )
        db.add_all([notice, foreign])
        db.commit()
        ids = str(notice.id), str(foreign.id)
    headers = auth_header(client, "store_manager")
    assert len(client.get("/api/v1/notifications", headers=headers).json()) == 1
    assert client.post(f"/api/v1/notifications/{ids[1]}/read", headers=headers).status_code == 404
    url = f"/api/v1/notifications/{ids[0]}/read"
    first = client.post(url, headers=headers)
    assert first.status_code == 200
    assert first.json() == client.post(url, headers=headers).json()
    with session_maker() as db:
        assert len(list(db.scalars(select(Event)))) == 1


def test_br43_br54_tracking_reads_latest_published_events(client, store_data, session_maker):
    from app.models import Vehicle
    from app.modules.planning.models import Plan, PlanVersion, Stop, StopOrder, Trip

    with session_maker() as db:
        db.add(
            Vehicle(
                code="STOREV",
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
        plan = Plan(depot="TestDepot", operating_date=DAY)
        db.add(plan)
        db.flush()
        version = PlanVersion(plan_id=plan.id, number=1, status="published", published_at=NOW)
        db.add(version)
        db.flush()
        trip = Trip(
            version_id=version.id,
            vehicle_code="STOREV",
            trip_no=1,
            brand="Fresh",
            district="StoreDistrict",
            lane="predawn",
            plan_minutes=30,
        )
        db.add(trip)
        db.flush()
        stop = Stop(
            trip_id=trip.id,
            seq=1,
            outlet_code="STORE1",
            status="planned",
            plan_arrival=time(5),
            likely_from=time(5, 15),
            likely_to=time(5, 35),
        )
        db.add(stop)
        db.flush()
        order = db.scalar(select(Order))
        db.add(StopOrder(stop_id=stop.id, order_id=order.id, planned_cases=28))
        actor = db.scalar(select(User).where(User.role == "driver"))
        db.add(
            Event(
                event_id=uuid.uuid4(),
                type="trip_loaded",
                actor_id=actor.id,
                entity_type="trip",
                entity_id=str(trip.id),
                plan_version_id=version.id,
                event_time=NOW,
                received_at=NOW,
                payload={},
            )
        )
        db.commit()
        stop_id, version_id = stop.id, version.id
    headers = auth_header(client, "store_manager")
    order = client.get("/api/v1/orders/SYN-DRAFT", headers=headers).json()
    assert order["status"] == "loaded"
    assert order["tracking"][0]["likely_from"] == "05:15:00"
    with session_maker() as db:
        db.add(
            Event(
                event_id=uuid.uuid4(),
                type="outcome_recorded",
                actor_id=actor.id,
                entity_type="stop",
                entity_id=str(stop_id),
                plan_version_id=version_id,
                event_time=NOW,
                received_at=NOW + timedelta(hours=1),
                payload={"outcome": "delivered", "cases_handed_over": 28},
            )
        )
        db.commit()
    order = client.get("/api/v1/orders/SYN-DRAFT", headers=headers).json()
    assert order["status"] == "delivered"
    assert order["tracking"][0]["event_time"] != order["tracking"][0]["received_at"]
    receipt = client.get("/api/v1/orders/SYN-DRAFT/receipt-draft", headers=headers).json()
    assert receipt["can_confirm"]
    assert receipt["total_cases"] == 28
    with session_maker() as db:
        assert db.get(Stop, stop_id).status == "planned"
        assert db.get(PlanVersion, version_id).status == "published"
        assert len(list(db.scalars(select(Event)))) == 2
