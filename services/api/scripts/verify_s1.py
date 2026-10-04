"""Local-only S1 generate → confirm → publish → Task 2B check (dataset never required in CI)."""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.clock import COLOMBO
from app.core.config import Settings
from app.core.db import get_db
from app.main import create_app
from app.models import Base
from app.seed.dataset import load_dataset
from app.seed.demo import seed_demo
from app.seed.reference import load_reference, load_travel_ratios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=Path("datasets"))
    parser.add_argument("--output", type=Path, default=Path("datasets/s1_allocation.csv"))
    args = parser.parse_args()
    # Keep organiser data and all derivatives under the ignored local dataset directory.
    root = args.dataset_dir.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(root):
        parser.error("The allocation output must stay inside --dataset-dir")
    dataset = load_dataset(root)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker() as db:
        load_reference(db, dataset)
        load_travel_ratios(db, dataset)
        seed_demo(db, dataset, datetime(2026, 4, 6, 16, 5, tzinfo=COLOMBO))
        db.commit()
    app = create_app(Settings(jwt_secret="local-verification-secret-at-least-32-bytes"))

    def get_test_db():
        with maker() as db:
            yield db

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "dispatch.peliyagoda@waypoint.demo", "password": "demo1234"},
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        response = client.post("/api/v1/plans/2026-04-07/generate", headers=headers)
        assert response.status_code == 200, response.text
        plan = response.json()
        if plan["deferrals"]:
            response = client.post(
                f"/api/v1/plan-versions/{plan['id']}/deferrals/confirm",
                headers=headers,
                json={
                    "items": [
                        {
                            "deferral_id": d["id"],
                            "reason": "Capacity and time limits on the next run",
                        }
                        for d in plan["deferrals"]
                    ]
                },
            )
            assert response.status_code == 200, response.text
        gate = client.get(f"/api/v1/plan-versions/{plan['id']}/publish-check", headers=headers)
        assert gate.status_code == 200 and gate.json()["can_publish"], gate.text
        response = client.post(
            f"/api/v1/plan-versions/{plan['id']}/publish",
            headers=headers,
            json={"accept_late_risk": True},
        )
        assert response.status_code == 200, response.text
        plan = response.json()
        assignments = {
            so["order_ref"]: (t["vehicle_code"], t["trip_no"])
            for t in plan["trips"]
            for s in t["stops"]
            for so in s["orders"]
        }
        assert len([t for t in plan["trips"] if t["vehicle_code"] == "VEH036"]) == 2
        assert any(s["outlet_code"] == "OUT074" for t in plan["trips"] for s in t["stops"])
        with output.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["scenario", "order_ref", "decision", "vehicle_id", "trip_id"])
            refs = list(assignments) + [d["order_ref"] for d in plan["deferrals"]]
            for ref in refs:
                vehicle, number = assignments.get(ref, ("", ""))
                writer.writerow(["S1", ref, "served" if vehicle else "deferred", vehicle, number])
        print(
            json.dumps(
                {"status": plan["status"], "solve_ms": plan["solve_ms"], "kpis": plan["kpis"]},
                indent=2,
            )
        )
    subprocess.run([sys.executable, str(root / "check_allocation.py"), str(output)], check=True)


if __name__ == "__main__":
    main()
