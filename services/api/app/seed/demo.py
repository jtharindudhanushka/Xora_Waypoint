"""Seed the demo day: scenario S1 orders and fleet (dataset) plus our own fixtures (YAML)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.catalog.models import OutletProfile, Product, UsualQuantity
from app.modules.fleet.models import VehicleDay
from app.modules.ops.models import ClockSetting
from app.modules.orders.models import DriverNote, Order, OrderLine
from app.seed.dataset import Dataset

EXTRAS_PATH = Path(__file__).with_name("demo_extras.yaml")
DEMO_PASSWORD = "demo1234"

# Operational tables, child before parent. TRUNCATE bypasses the append-only row trigger on
# `events`, which is intended: a demo reset starts a new history, it doesn't edit one.
OPERATIONAL_TABLES = (
    "repair_options", "holds", "shortfalls", "issue_lines", "issues", "receipt_lines",
    "receipts", "notifications", "exceptions", "events", "plan_acks", "deferrals",
    "stop_orders", "stops", "trips", "plan_versions", "plans", "driver_notes", "order_lines",
    "orders", "fuel_ledger", "vehicle_days", "usual_quantities", "outlet_profiles", "users",
    "clock_settings",
)  # fmt: skip


class SeedError(RuntimeError):
    pass


def load_extras() -> dict[str, Any]:
    with EXTRAS_PATH.open(encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data


def is_demo_seeded(session: Session) -> bool:
    return session.scalar(select(User.id).limit(1)) is not None


def reset_demo(session: Session) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text(f"TRUNCATE {', '.join(OPERATIONAL_TABLES)} CASCADE"))
    else:
        for table in OPERATIONAL_TABLES:
            session.execute(text(f"DELETE FROM {table}"))
    session.flush()


def seed_demo(session: Session, ds: Dataset, demo_start: datetime) -> dict[str, int]:
    extras = load_extras()
    scenario = extras["scenario"]
    operating_date = date.fromisoformat(str(scenario["operating_date"]))

    for p in extras["products"]:
        session.merge(Product(**p))
    for code, profile in extras["outlet_profiles"].items():
        session.merge(OutletProfile(outlet_code=code, **profile))
    for outlet, items in extras["usual_quantities"].items():
        for product_id, cases in items.items():
            session.merge(
                UsualQuantity(outlet_code=outlet, product_id=product_id, usual_cases=cases)
            )

    password_hash = hash_password(DEMO_PASSWORD)
    for u in extras["users"]:
        session.add(
            User(
                email=u["email"],
                name=u["name"],
                role=u["role"],
                password_hash=password_hash,
                depot=u.get("depot"),
                dock=u.get("dock"),
                vehicle_code=u.get("vehicle"),
                outlet_code=u.get("outlet"),
            )
        )

    orders = ds.read("Test Data/task2b_peak_day_scenarios.csv")
    orders = orders[orders.scenario == scenario["id"]]
    drafts = set(scenario["draft_order_refs"])
    by_ref: dict[str, Order] = {}
    for r in orders.itertuples():
        is_draft = r.order_ref in drafts
        order = Order(
            ref=r.order_ref,
            outlet_code=r.outlet_id,
            brand=r.brand,
            temp_requirement=r.temp_requirement,
            delivery_date=operating_date,
            units=int(r.order_units),
            weight_kg=float(r.order_weight_kg),
            volume_m3=float(r.order_volume_m3),
            deferred_yesterday=r.deferred_yesterday == "1",
            days_since_last_served=int(r.days_since_last_served),
            status="draft" if is_draft else "placed",
            source="dataset",
            placed_at=None if is_draft else demo_start.astimezone(UTC),
        )
        session.add(order)
        by_ref[r.order_ref] = order
    session.flush()

    for ref, items in extras["order_lines"].items():
        order = by_ref.get(ref)
        if order is None:
            raise SeedError(f"demo_extras.yaml lists lines for unknown order {ref}")
        total = sum(items.values())
        if order.status != "draft" and total != order.units:
            raise SeedError(f"{ref}: item cases {total} ≠ dataset order_units {order.units}")
        for product_id, cases in items.items():
            session.add(OrderLine(order_id=order.id, product_id=product_id, qty_ordered=cases))

    fleet = ds.read("Test Data/task2b_peak_day_fleet.csv")
    switched_off: dict[str, str] = scenario.get("switched_off", {})
    for r in fleet[fleet.scenario == scenario["id"]].itertuples():
        session.add(
            VehicleDay(
                vehicle_code=r.vehicle_id,
                date=operating_date,
                status=r.status,
                switched_on=r.status == "available" and r.vehicle_id not in switched_off,
                off_reason=switched_off.get(r.vehicle_id),
            )
        )

    for note in extras.get("driver_notes", []):
        session.add(
            DriverNote(
                outlet_code=note["outlet"],
                for_date=date.fromisoformat(str(note["for_date"])),
                text=note["text"],
            )
        )

    # The demo clock runs forward from demo_start, anchored at the real time of seeding.
    session.merge(ClockSetting(id=1, demo_now=demo_start.astimezone(UTC), set_at=datetime.now(UTC)))
    session.flush()
    return {
        "users": len(extras["users"]),
        "orders": len(by_ref),
        "draft_orders": len(drafts),
        "vehicle_days": int((fleet.scenario == scenario["id"]).sum()),
    }
