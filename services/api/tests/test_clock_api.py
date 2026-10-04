import asyncio

from fastapi.testclient import TestClient

from app.modules.stream.broker import Broker
from tests.conftest import auth_header


def test_only_the_dispatcher_can_set_the_demo_clock(client: TestClient) -> None:  # BR-55, BR-56
    body = {"demo_now": "2026-04-06T16:05:00"}
    driver = client.put("/api/v1/clock", json=body, headers=auth_header(client, "driver"))
    assert driver.status_code == 403
    assert driver.json()["rule_id"] == "BR-55"

    dispatcher = client.put("/api/v1/clock", json=body, headers=auth_header(client, "dispatcher"))
    assert dispatcher.status_code == 200
    assert dispatcher.json()["is_demo"] is True
    assert dispatcher.json()["now"].startswith("2026-04-06T16:05")  # bare time read as +05:30

    read = client.get("/api/v1/clock")
    assert read.json()["now"].startswith("2026-04-06T16:0")


def test_clock_can_return_to_real_time(client: TestClient) -> None:
    headers = auth_header(client, "dispatcher")
    client.put("/api/v1/clock", json={"demo_now": "2026-04-07T04:15:00+05:30"}, headers=headers)
    cleared = client.put("/api/v1/clock", json={"demo_now": None}, headers=headers)
    assert cleared.json()["is_demo"] is False


def test_broker_delivers_only_to_the_matching_audience() -> None:
    async def scenario() -> tuple[int, int]:
        broker = Broker()
        async with (
            broker.subscribe({"role": "loader"}) as loader_q,
            broker.subscribe({"role": "store_manager"}) as store_q,
        ):
            await broker.publish("hold.created", {"trip": "T1"}, lambda s: s["role"] == "loader")
            return loader_q.qsize(), store_q.qsize()

    assert asyncio.run(scenario()) == (1, 0)
