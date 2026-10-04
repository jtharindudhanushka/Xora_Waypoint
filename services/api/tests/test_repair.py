"""Synthetic dispatcher repair tests; loading reports are owned by the loader track."""

import uuid
from datetime import UTC, datetime, time

import pytest
from sqlalchemy import select

from app.core.clock import Clock
from app.core.deps import DbDep, get_clock
from app.models import ClockSetting, Order, OutletProfile, User
from app.modules.loading.models import Hold, Shortfall
from app.modules.planning.models import PlanVersion, Trip
from app.modules.sync.models import Event
from tests.conftest import auth_header
from tests.test_planning import (
    DAY,
    generate,
    planning_data,  # noqa: F401
)


@pytest.fixture
def shortfall_data(client, session_maker, request):
    request.getfixturevalue("planning_data")
    with session_maker() as db:
        for order in db.scalars(select(Order)):
            order.weight_kg = 600
            order.days_since_last_served = 0
        db.add(OutletProfile(outlet_code="TEST1", split_rule="same_morning_only", language="en"))
        db.commit()
    plan = generate(client)
    with session_maker() as db:
        version = db.get(PlanVersion, uuid.UUID(plan["id"]))
        for trip in version.trips:
            departure = 280 if trip.trip_no == 1 else 380
            old = trip.planned_depart.hour * 60 + trip.planned_depart.minute
            trip.planned_depart = time(departure // 60, departure % 60)
            for stop in trip.stops:
                for field in ("plan_arrival", "likely_from", "likely_to"):
                    value = getattr(stop, field)
                    minutes = value.hour * 60 + value.minute + departure - old
                    setattr(stop, field, time(minutes // 60, minutes % 60))
        db.commit()
    published = client.post(
        f"/api/v1/plan-versions/{plan['id']}/publish",
        headers=auth_header(client, "dispatcher"),
        json={"accept_late_risk": True},
    )
    assert published.status_code == 200, published.text
    with session_maker() as db:
        version = db.get(PlanVersion, uuid.UUID(plan["id"]))
        source = next(t for t in version.trips if t.trip_no == 1)
        loader = db.scalar(select(User).where(User.role == "loader"))
        loader.dock = "Test Dock"
        report_time = datetime(2026, 4, 6, 22, 48, tzinfo=UTC)  # Tue 04:18 Colombo.
        shortfall = Shortfall(
            trip_id=source.id,
            order_id=source.stops[0].orders[0].order_id,
            kind="missing",
            qty=2,
            reason="short_from_chiller_pick",
            reported_by=loader.id,
            event_time=report_time,
        )
        db.add(shortfall)
        db.flush()
        db.add(
            Hold(
                trip_id=source.id,
                shortfall_id=shortfall.id,
                status="active",
                created_at=report_time,
            )
        )
        setting = db.get(ClockSetting, 1)
        setting.demo_now = datetime(2026, 4, 6, 22, 49, tzinfo=UTC)
        anchor = datetime(2026, 10, 4, 12, tzinfo=UTC)
        setting.set_at = anchor
        db.commit()

        def frozen_clock(db: DbDep) -> Clock:
            return Clock(db, real_now=lambda: anchor)

        client.app.dependency_overrides[get_clock] = frozen_clock
        return str(shortfall.id), str(source.id), plan["id"]


def options(client, shortfall_data):
    response = client.get(
        f"/api/v1/shortfalls/{shortfall_data[0]}/options", headers=auth_header(client, "dispatcher")
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_br28_br29_options_preselect_a_and_flag_c_without_auto_apply(
    client, shortfall_data, session_maker
):
    body = options(client, shortfall_data)
    assert body["waiting_seconds"] == 60
    assert body["to_departure_minutes"] == 21
    assert {o["label"] for o in body["options"]} == {"A", "B", "C"}
    assert next(o for o in body["options"] if o["recommended"])["label"] == "A"
    assert next(o for o in body["options"] if o["label"] == "C")["breaks_store_rule"]
    assert options(client, shortfall_data)["options"] == body["options"]
    with session_maker() as db:
        assert len(list(db.scalars(select(PlanVersion)))) == 1
        assert db.scalar(select(Hold)).status == "active"


def test_br30_apply_a_publishes_v2_links_topup_and_keeps_hold(
    client, shortfall_data, session_maker
):
    body = options(client, shortfall_data)
    option_id = next(o["id"] for o in body["options"] if o["label"] == "A")
    response = client.post(
        f"/api/v1/shortfalls/{shortfall_data[0]}/apply",
        headers=auth_header(client, "dispatcher"),
        json={"option_id": option_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "published"
    assert response.json()["number"] == 2
    order_ref = body["order_ref"]
    portions = [
        o["cases"]
        for t in response.json()["trips"]
        for s in t["stops"]
        for o in s["orders"]
        if o["order_ref"] == order_ref
    ]
    assert sorted(portions) == [2, 8]
    assert any(
        o["top_up_of_order_ref"] == order_ref
        for t in response.json()["trips"]
        for s in t["stops"]
        for o in s["orders"]
    )
    with session_maker() as db:
        old = db.get(PlanVersion, uuid.UUID(shortfall_data[2]))
        new = db.get(PlanVersion, uuid.UUID(response.json()["id"]))
        assert old.status == "published"
        assert next(t for t in old.trips if t.trip_no == 1).stops[0].orders[0].planned_cases == 10
        topups = [
            so for t in new.trips for s in t.stops for so in s.orders if so.top_up_of_order_id
        ]
        assert topups[0].planned_cases == 2
        hold = db.scalar(select(Hold))
        assert hold.status == "active"
        assert db.get(Trip, hold.trip_id).version_id == new.id
        assert {e.type for e in db.scalars(select(Event))} >= {"repair.applied", "plan.published"}
    assert (
        client.post(
            f"/api/v1/shortfalls/{shortfall_data[0]}/apply",
            headers=auth_header(client, "dispatcher"),
            json={"option_id": option_id},
        ).status_code
        == 409
    )


def test_br30_apply_c_creates_linked_next_operating_day_obligation(
    client, shortfall_data, session_maker
):
    body = options(client, shortfall_data)
    option_id = next(o["id"] for o in body["options"] if o["label"] == "C")
    response = client.post(
        f"/api/v1/shortfalls/{shortfall_data[0]}/apply",
        headers=auth_header(client, "dispatcher"),
        json={"option_id": option_id},
    )
    assert response.status_code == 200, response.text
    with session_maker() as db:
        future = db.scalar(select(Order).where(Order.ref.startswith("R-")))
        assert future.units == 2
        assert future.delivery_date > DAY
        audit = db.scalar(select(Event).where(Event.type == "repair.applied"))
        assert audit.payload["future_order_id"] == str(future.id)
        assert audit.payload["breaks_store_rule"] is True


def test_br28_stale_option_rejects_after_fleet_capacity_change(
    client, shortfall_data, session_maker
):
    body = options(client, shortfall_data)
    option_id = next(o["id"] for o in body["options"] if o["label"] == "A")
    from app.models import Vehicle

    with session_maker() as db:
        db.get(Vehicle, "TESTV").weight_cap_kg = 600
        db.commit()
    response = client.post(
        f"/api/v1/shortfalls/{shortfall_data[0]}/apply",
        headers=auth_header(client, "dispatcher"),
        json={"option_id": option_id},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "STALE_REPAIR_OPTION"


def test_br55_repair_rejects_non_dispatcher(client, shortfall_data):
    response = client.get(
        f"/api/v1/shortfalls/{shortfall_data[0]}/options", headers=auth_header(client, "driver")
    )
    assert response.status_code == 403


def test_br28_departed_trip_is_not_repaired(client, shortfall_data, session_maker):
    with session_maker() as db:
        source = db.get(Trip, uuid.UUID(shortfall_data[1]))
        source.stops[0].status = "in_transit"
        db.commit()
    assert options(client, shortfall_data)["options"] == []


def test_br30_apply_b_delays_departure_and_preserves_cases(client, shortfall_data):
    body = options(client, shortfall_data)
    option_id = next(o["id"] for o in body["options"] if o["label"] == "B")
    response = client.post(
        f"/api/v1/shortfalls/{shortfall_data[0]}/apply",
        headers=auth_header(client, "dispatcher"),
        json={"option_id": option_id},
    )
    assert response.status_code == 200, response.text
    first = next(t for t in response.json()["trips"] if t["trip_no"] == 1)
    assert first["planned_depart"] == "05:05:00"
    assert first["stops"][0]["orders"][0]["cases"] == 10


def test_br27_repair_preserves_other_active_holds(client, shortfall_data, session_maker):
    with session_maker() as db:
        source = db.get(Trip, uuid.UUID(shortfall_data[1]))
        later = next(t for t in source.version.trips if t.trip_no == 2)
        loader = db.scalar(select(User).where(User.role == "loader"))
        other = Shortfall(
            trip_id=later.id,
            order_id=later.stops[0].orders[0].order_id,
            kind="missing",
            qty=1,
            reason="not_on_dock",
            reported_by=loader.id,
            event_time=datetime(2026, 4, 6, 22, 48, tzinfo=UTC),
        )
        db.add(other)
        db.flush()
        db.add(
            Hold(
                trip_id=later.id,
                shortfall_id=other.id,
                status="active",
                created_at=other.event_time,
            )
        )
        db.commit()
        other_id = str(other.id)
    body = options(client, shortfall_data)
    assert "A" not in {o["label"] for o in body["options"]}
    response = client.post(
        f"/api/v1/shortfalls/{shortfall_data[0]}/apply",
        headers=auth_header(client, "dispatcher"),
        json={"option_id": next(o["id"] for o in body["options"] if o["label"] == "B")},
    )
    assert response.status_code == 200, response.text
    with session_maker() as db:
        holds = list(db.scalars(select(Hold)))
        assert len(holds) == 2
        assert all(h.status == "active" for h in holds)
        assert all(str(db.get(Trip, h.trip_id).version_id) == response.json()["id"] for h in holds)
    remaining = client.get(
        f"/api/v1/shortfalls/{other_id}/options", headers=auth_header(client, "dispatcher")
    )
    assert remaining.status_code == 200, remaining.text
    assert remaining.json()["version_number"] == 2


@pytest.mark.asyncio
async def test_br30_repair_publishes_scoped_sse(client, shortfall_data, session_maker):
    from app.modules.repair import service
    from app.modules.repair.repository import Repository
    from app.modules.stream.broker import broker

    body = options(client, shortfall_data)
    option_id = uuid.UUID(next(o["id"] for o in body["options"] if o["label"] == "A"))
    with session_maker() as db:
        user = db.scalar(select(User).where(User.role == "dispatcher"))
        async with (
            broker.subscribe({"depot": "TestDepot"}) as dock,
            broker.subscribe({"vehicle": "TESTV"}) as driver,
            broker.subscribe({"depot": "OtherDepot"}) as other,
        ):
            version = await service.apply(
                Repository(db, "TestDepot"),
                user,
                client.app.dependency_overrides[get_clock](db),
                uuid.UUID(shortfall_data[0]),
                option_id,
            )
            assert (await dock.get()).event == "plan.published"
            assert (await driver.get()).data["version_id"] == str(version.id)
            assert other.empty()
