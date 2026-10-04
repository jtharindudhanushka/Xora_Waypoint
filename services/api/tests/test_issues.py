"""BR-51/52 decisions keep original evidence and notify both parties."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models import Depot, Order, OrderLine, Outlet, Product, User
from app.modules.ops.models import Notification
from app.modules.receipts.models import Issue, IssueLine
from app.modules.stream.broker import broker
from app.modules.sync.models import Event
from tests.conftest import auth_header
from tests.test_planning import planning_data  # noqa: F401

pytestmark = pytest.mark.usefixtures("planning_data")


def make_issue(session_maker, kind="store_report"):
    with session_maker() as db:
        order = db.scalar(select(Order).where(Order.ref == "TEST-OK"))
        driver = db.scalar(select(User).where(User.role == "driver"))
        driver.vehicle_code = "TESTV"
        product = Product(id="test-yogurt", name="Test yoghurt", brand="Fresh", is_chilled=True)
        db.add(product)
        db.flush()
        line = OrderLine(order_id=order.id, product_id=product.id, qty_ordered=10, qty_delivered=10)
        db.add(line)
        db.flush()
        event = Event(
            event_id=uuid.uuid4(),
            type="outcome_recorded",
            actor_id=driver.id,
            entity_type="order",
            entity_id=str(order.id),
            payload={"cases": 10},
            event_time=datetime(2026, 4, 7, 1, 22, tzinfo=UTC),
            received_at=datetime(2026, 4, 7, 2, 18, tzinfo=UTC),
        )
        db.add(event)
        db.flush()
        issue = Issue(
            order_id=order.id,
            kind=kind,
            status="open",
            driver_event_id=event.event_id,
            driver_qty=10,
            store_qty=8,
            opened_at=datetime(2026, 4, 7, 1, 40, tzinfo=UTC),
        )
        db.add(issue)
        db.flush()
        db.add(
            IssueLine(
                issue_id=issue.id,
                order_line_id=line.id,
                product_id=product.id,
                problem="damaged",
                qty=2,
            )
        )
        db.commit()
        return issue.id, event.event_id, order.id


@pytest.mark.parametrize(
    "kind,resolution",
    [
        ("store_report", "redeliver"),
        ("store_report", "credit"),
        ("store_report", "reject"),
        ("count_conflict", "driver_stands"),
        ("count_conflict", "store_stands"),
        ("count_conflict", "recount"),
    ],
)
def test_br51_br52_decisions_preserve_evidence_and_notify_both_sides(
    client, session_maker, monkeypatch, kind, resolution
):
    identifier, event_id, order_id = make_issue(session_maker, kind)
    messages = []

    async def capture(name, data, audience=None):
        messages.append((name, data, audience))

    monkeypatch.setattr(broker, "publish", capture)
    headers = auth_header(client, "dispatcher")
    response = client.post(
        f"/api/v1/issues/{identifier}/resolve",
        headers=headers,
        json={"resolution": resolution, "note": "Evidence reviewed"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "resolved"
    assert response.json()["driver_qty"] == 10 and response.json()["store_qty"] == 8
    with session_maker() as db:
        event = db.get(Event, event_id)
        assert event.payload == {"cases": 10}
        assert event.event_time.hour == 1 and event.received_at.hour == 2
        assert db.get(Order, order_id).units == 10
        notices = list(db.scalars(select(Notification).where(Notification.kind == "decision")))
        assert any(n.outlet_code == "TEST1" for n in notices)
        assert any(n.recipient_user_id == event.actor_id for n in notices)
        decision = db.scalar(select(Event).where(Event.type == "issue.resolved"))
        assert decision.payload["resolution"] == resolution
        if resolution == "redeliver":
            redelivery = db.get(Order, uuid.UUID(decision.payload["redelivery_order_id"]))
            assert redelivery.units == 2 and redelivery.weight_kg == 20
            assert redelivery.lines[0].qty_ordered == 2
        if resolution == "store_stands":
            claim = db.get(Issue, uuid.UUID(decision.payload["short_claim_id"]))
            assert claim.kind == "store_report" and claim.status == "open"
            assert claim.lines[0].qty == 2
        assert messages[0][2]({"outlet": "TEST1"})
        assert messages[0][2]({"user_id": str(event.actor_id)})
        assert not messages[0][2](
            {"role": "store_manager", "outlet": "OTHER", "depot": "TestDepot"}
        )
    assert (
        client.post(
            f"/api/v1/issues/{identifier}/resolve",
            headers=headers,
            json={"resolution": resolution, "note": "Again"},
        ).status_code
        == 409
    )


def test_br51_reject_needs_reason_and_wrong_kind_rejected(client, session_maker):
    identifier, _, _ = make_issue(session_maker)
    headers = auth_header(client, "dispatcher")
    result = client.post(
        f"/api/v1/issues/{identifier}/resolve", headers=headers, json={"resolution": "reject"}
    )
    assert result.status_code == 422 and result.json()["rule_id"] == "BR-51"
    result = client.post(
        f"/api/v1/issues/{identifier}/resolve",
        headers=headers,
        json={"resolution": "driver_stands"},
    )
    assert result.status_code == 422


def test_br55_issue_list_detail_and_decision_are_depot_scoped(client, session_maker):
    identifier, _, _ = make_issue(session_maker)
    headers = auth_header(client, "dispatcher")
    assert len(client.get("/api/v1/issues?status=open", headers=headers).json()) == 1
    assert (
        client.get(
            f"/api/v1/issues/{identifier}", headers=auth_header(client, "driver")
        ).status_code
        == 403
    )
    with session_maker() as db:
        db.add(Depot(name="OtherDepot"))
        db.flush()
        outlet = db.get(Outlet, "TEST1")
        outlet.depot = "OtherDepot"
        db.commit()
    assert client.get("/api/v1/issues?status=open", headers=headers).json() == []
    assert client.get(f"/api/v1/issues/{identifier}", headers=headers).status_code == 404
    assert (
        client.post(
            f"/api/v1/issues/{identifier}/resolve", headers=headers, json={"resolution": "credit"}
        ).status_code
        == 404
    )
