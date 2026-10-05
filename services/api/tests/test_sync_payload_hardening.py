# ruff: noqa: F811  (pytest fixtures imported from test_sync are re-bound as parameters)
"""QA hardening: malformed driver payloads are rejected cleanly and never poison later reads."""

import pytest

from tests.conftest import auth_header
from tests.test_sync import _store_at_test1, ack, event, field, sync  # noqa: F401


def bad_outcome(field, **payload):
    return event("outcome_recorded", "stop", field["stop"], field["version"], **payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"outcome": "delivered", "orders": "205"},
        {"outcome": "delivered", "orders": [205]},
        {"outcome": "delivered", "orders": {"order_id": "x", "cases": 1}},
        {"outcome": "delivered", "orders": [{"order_id": "ORDER", "cases": True}]},
        {"outcome": "delivered", "orders": [{"order_id": "ORDER", "cases": 10**12}]},
        {"outcome": "delivered", "cases_handed_over": "lots"},
        {"outcome": "delivered", "cases_handed_over": -3},
    ],
)
def test_malformed_outcome_is_rejected_not_500(client, field, payload):
    if isinstance(payload.get("orders"), list) and isinstance(payload["orders"][0], dict):
        payload["orders"][0]["order_id"] = field["order"]
    results = sync(client, "driver", ack(field), bad_outcome(field, **payload))
    assert results[1]["status"] == "rejected", results[1]
    assert results[1]["code"] == "INVALID_OUTCOME"


def test_receipt_draft_survives_any_stored_outcome(client, field, session_maker):
    _store_at_test1(session_maker)
    sync(
        client,
        "driver",
        ack(field),
        bad_outcome(
            field,
            outcome="delivered",
            cases_handed_over=205,
            orders=[{"order_id": field["order"], "cases": 205}],
            lines=[{"order_line_id": "x", "qty_delivered": "many"}],
        ),
    )
    draft = client.get(
        "/api/v1/orders/TEST-001/receipt-draft", headers=auth_header(client, "store_manager")
    )
    assert draft.status_code == 200, draft.text


@pytest.mark.parametrize("qty", [True, "2", 2.5])
def test_shortfall_quantity_must_be_a_real_integer(client, field, qty):
    report = event(
        "shortfall_reported",
        "trip",
        field["trip"],
        field["version"],
        order_id=field["order"],
        kind="missing",
        qty=qty,
        reason="other",
    )
    assert sync(client, "loader", report)[0]["status"] == "rejected"
