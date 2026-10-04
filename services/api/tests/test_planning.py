"""Synthetic generate → confirm → publish regression, independent of competition data."""

import uuid
from datetime import UTC, date, datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    CalendarDay,
    ClockSetting,
    Depot,
    District,
    Order,
    Outlet,
    ServiceAllowance,
    Vehicle,
    VehicleDay,
)
from app.modules.planning.models import PlanVersion
from app.modules.stream.broker import broker
from app.modules.sync.models import Event
from tests.conftest import auth_header

DAY = date(2026, 4, 7)


@pytest.fixture
def planning_data(session_maker: sessionmaker[Session]) -> None:
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
        db.add(ServiceAllowance(brand="Fresh", dock_type="street", minutes=16))
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
        db.flush()
        db.add(VehicleDay(vehicle_code="TESTV", date=DAY, status="available", switched_on=True))
        for day in (DAY, date(2026, 4, 8)):
            iso_year, iso_week, _ = day.isocalendar()
            db.add(
                CalendarDay(
                    date=day,
                    dow=day.weekday(),
                    iso_year=iso_year,
                    iso_week=iso_week,
                    is_payday=False,
                    festival_ramp=0,
                    is_holiday=False,
                    monsoon=False,
                    is_operating=True,
                )
            )
        db.add(
            Order(
                ref="TEST-OK",
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
        db.add(
            Order(
                ref="TEST-DEFER",
                outlet_code="TEST1",
                brand="Fresh",
                temp_requirement="chilled",
                delivery_date=DAY,
                units=10,
                weight_kg=2000,
                volume_m3=1,
                status="placed",
                days_since_last_served=3,
            )
        )
        db.add(
            ClockSetting(
                id=1, demo_now=datetime(2026, 4, 6, 11, tzinfo=UTC), set_at=datetime.now(UTC)
            )
        )
        db.commit()


def generate(client: TestClient):
    response = client.post(
        f"/api/v1/plans/{DAY}/generate", headers=auth_header(client, "dispatcher")
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_br20_lock_survives_rerun(client, planning_data):
    body = generate(client)
    headers = auth_header(client, "dispatcher")
    trip = body["trips"][0]
    locked = client.post(f"/api/v1/trips/{trip['id']}/lock", headers=headers)
    assert locked.status_code == 200
    assert locked.json()["trips"][0]["locked"]
    rerun = generate(client)
    assert rerun["trips"][0]["locked"]
    assert rerun["trips"][0]["planned_depart"] == trip["planned_depart"]
    assert rerun["trips"][0]["stops"][0]["outlet_code"] == trip["stops"][0]["outlet_code"]


def test_br16_infeasible_serve_instead_rejects_without_creating_version(
    client, planning_data, session_maker
):
    body = generate(client)
    response = client.post(
        f"/api/v1/deferrals/{body['deferrals'][0]['id']}/serve-instead",
        headers=auth_header(client, "dispatcher"),
        json={"confirm": True},
    )
    assert response.status_code == 422
    assert response.json()["rule_id"] == "BR-16"
    with session_maker() as db:
        assert len(list(db.scalars(select(PlanVersion)))) == 1


def test_br16_preview_is_read_only_and_apply_creates_replacement_draft(
    client, planning_data, session_maker
):
    with session_maker() as db:
        for row in db.scalars(select(Order)):
            row.weight_kg = 1000
        db.add(
            Order(
                ref="TEST-THIRD",
                outlet_code="TEST1",
                brand="Fresh",
                temp_requirement="chilled",
                delivery_date=DAY,
                units=10,
                weight_kg=1000,
                volume_m3=1,
                status="placed",
                days_since_last_served=0,
            )
        )
        db.commit()
    body = generate(client)
    deferred = body["deferrals"][0]
    headers = auth_header(client, "dispatcher")
    url = f"/api/v1/deferrals/{deferred['id']}/serve-instead"
    preview = client.post(url, headers=headers, json={"confirm": False})
    assert preview.status_code == 200, preview.text
    assert preview.json()["displaces"]
    assert preview.json()["version"] is None
    applied = client.post(url, headers=headers, json={"confirm": True})
    assert applied.status_code == 200, applied.text
    assert applied.json()["version"]["number"] == 2
    served = {
        o["order_ref"]
        for t in applied.json()["version"]["trips"]
        for s in t["stops"]
        for o in s["orders"]
    }
    assert deferred["order_ref"] in served
    assert client.post(url, headers=headers, json={"confirm": True}).status_code == 409


def test_br21_br22_br23_generate_confirm_publish(client, planning_data, session_maker):
    body = generate(client)
    assert body["kpis"]["orders_served"] == 1
    assert body["kpis"]["deferrals"] == 1
    version_id = body["id"]
    headers = auth_header(client, "dispatcher")
    gate = client.get(f"/api/v1/plan-versions/{version_id}/publish-check", headers=headers).json()
    assert not gate["can_publish"]
    assert (
        client.post(f"/api/v1/plan-versions/{version_id}/publish", headers=headers).status_code
        == 422
    )
    item = {"deferral_id": body["deferrals"][0]["id"]}
    confirm_url = f"/api/v1/plan-versions/{version_id}/deferrals/confirm"
    rejected = client.post(confirm_url, headers=headers, json={"items": [item]})
    assert rejected.json()["rule_id"] == "BR-21"
    item["reason"] = "No vehicle can carry this whole order"
    assert client.post(confirm_url, headers=headers, json={"items": [item]}).status_code == 200
    published = client.post(f"/api/v1/plan-versions/{version_id}/publish", headers=headers)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert client.post(confirm_url, headers=headers, json={"items": [item]}).status_code == 409
    assert (
        client.post(f"/api/v1/plan-versions/{version_id}/publish", headers=headers).status_code
        == 409
    )
    with session_maker() as db:
        events = list(db.scalars(select(Event)))
        assert {e.type for e in events} == {
            "plan.generated",
            "deferrals.confirmed",
            "plan.published",
        }
        assert db.get(PlanVersion, uuid.UUID(version_id)).status == "published"
    assert client.get(f"/api/v1/plans/{DAY}", headers=headers).json()["id"] == version_id


def test_br55_planning_rejects_non_dispatcher(client, planning_data):
    assert (
        client.post(
            f"/api/v1/plans/{DAY}/generate", headers=auth_header(client, "driver")
        ).status_code
        == 403
    )


def test_br10_fleet_switch_reason_and_publish_revalidation(client, planning_data):
    version = generate(client)
    headers = auth_header(client, "dispatcher")
    switch_url = f"/api/v1/fleet/TESTV/{DAY}"
    assert client.patch(switch_url, headers=headers, json={"switched_on": False}).status_code == 422
    switched = client.patch(
        switch_url, headers=headers, json={"switched_on": False, "off_reason": "No driver"}
    )
    assert switched.status_code == 200, switched.text
    gate = client.get(
        f"/api/v1/plan-versions/{version['id']}/publish-check", headers=headers
    ).json()
    assert any(v["rule_id"] == "BR-10" for v in gate["violations"])


def test_br10_workshop_is_locked_off(client, planning_data, session_maker):
    with session_maker() as db:
        day = db.get(VehicleDay, ("TESTV", DAY))
        day.status = "in_workshop"
        day.switched_on = False
        db.commit()
    response = client.patch(
        f"/api/v1/fleet/TESTV/{DAY}",
        headers=auth_header(client, "dispatcher"),
        json={"switched_on": True},
    )
    assert response.status_code == 422
    assert response.json()["rule_id"] == "BR-10"


def test_br40_generation_blocks_before_cutoff(client, planning_data, session_maker):
    with session_maker() as db:
        setting = db.get(ClockSetting, 1)
        setting.demo_now = datetime(2026, 4, 6, 9, tzinfo=UTC)
        setting.set_at = datetime.now(UTC)
        db.commit()
    response = client.post(
        f"/api/v1/plans/{DAY}/generate", headers=auth_header(client, "dispatcher")
    )
    assert response.json()["code"] == "ORDERS_OPEN"


def test_br23_stale_draft_cannot_publish(client, planning_data):
    first = generate(client)
    second = generate(client)
    assert second["number"] == first["number"] + 1
    gate = client.get(
        f"/api/v1/plan-versions/{first['id']}/publish-check",
        headers=auth_header(client, "dispatcher"),
    ).json()
    assert any(v["code"] == "STALE_DRAFT" for v in gate["violations"])


def test_br55_foreign_depot_version_is_forbidden(client, planning_data, session_maker):
    version = generate(client)
    with session_maker() as db:
        db.add(Depot(name="OtherDepot"))
        db.flush()
        row = db.get(PlanVersion, uuid.UUID(version["id"]))
        row.plan.depot = "OtherDepot"
        db.commit()
    response = client.get(
        f"/api/v1/plan-versions/{version['id']}/publish-check",
        headers=auth_header(client, "dispatcher"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_br23_broker_filters_published_plan_audience():
    async with (
        broker.subscribe({"depot": "TestDepot"}) as same,
        broker.subscribe({"depot": "OtherDepot"}) as other,
    ):
        await broker.publish(
            "plan.published", {"number": 1}, audience=lambda s: s.get("depot") == "TestDepot"
        )
        assert (await same.get()).event == "plan.published"
        assert other.empty()


def test_br22_late_risk_requires_explicit_acceptance(client, planning_data, session_maker):
    with session_maker() as db:
        outlet = db.get(Outlet, "TEST1")
        outlet.window_close = time(3, 30)
        db.commit()
    version = generate(client)
    headers = auth_header(client, "dispatcher")
    items = [{"deferral_id": d["id"], "reason": "Over capacity"} for d in version["deferrals"]]
    client.post(
        f"/api/v1/plan-versions/{version['id']}/deferrals/confirm",
        headers=headers,
        json={"items": items},
    )
    url = f"/api/v1/plan-versions/{version['id']}/publish"
    rejected = client.post(url, headers=headers)
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "LATE_RISK_ACCEPTANCE"
    assert client.post(url, headers=headers, json={"accept_late_risk": True}).status_code == 200


@pytest.mark.asyncio
async def test_br23_publish_emits_scoped_sse(planning_data, session_maker):
    from app.core.clock import Clock
    from app.models import User
    from app.modules.planning import service
    from app.modules.planning.schemas import ConfirmIn, ConfirmItem

    with session_maker() as db:
        user = db.scalar(select(User).where(User.role == "dispatcher"))
        clock = Clock(db)
        repo = service.repository(db, user)
        version = service.generate(repo, user, clock, DAY)
        service.confirm(
            repo,
            user,
            clock,
            version.id,
            ConfirmIn(
                items=[
                    ConfirmItem(deferral_id=d.id, reason="Over capacity") for d in version.deferrals
                ]
            ),
        )
        async with (
            broker.subscribe({"depot": "TestDepot"}) as same,
            broker.subscribe({"depot": "OtherDepot"}) as other,
            broker.subscribe({"outlet": "TEST1"}) as store,
        ):
            await service.publish(repo, user, clock, version.id, True)
            assert (await same.get()).event == "plan.published"
            assert (await store.get()).data["version_id"] == str(version.id)
            assert other.empty()
