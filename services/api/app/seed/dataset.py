"""Locate and validate the organisers' dataset pack before anything is written (ADR-0007).

The pack is never committed. If it is missing or malformed we stop with a message that says
exactly what to copy where, instead of failing half-way through a seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED: dict[str, set[str]] = {
    "General Data/outlets.csv": {
        "outlet_id", "brand", "district", "depot", "dock_type", "parking_constraint",
        "mall_window", "window_open_time", "window_close_time",
    },
    "General Data/vehicles.csv": {
        "vehicle_id", "type", "temp", "weight_cap_kg", "volume_cap_m3", "fuel_type",
        "km_per_l", "weekly_fuel_quota_l", "depot",
    },
    "General Data/calendar.csv": {
        "date", "dow", "iso_year", "iso_week", "is_payday", "festival", "festival_ramp",
        "is_holiday", "monsoon", "is_operating",
    },
    "General Data/district_travel.csv": {
        "district", "depot", "road_class", "free_flow_kmh", "depot_to_district_km",
        "depot_to_district_freeflow_min", "inter_stop_km", "inter_stop_freeflow_min",
    },
    "General Data/service_allowance.csv": {"brand", "dock_type", "service_allowance_min"},
    "Test Data/task2b_peak_day_scenarios.csv": {
        "scenario", "order_ref", "outlet_id", "brand", "temp_requirement", "order_units",
        "order_weight_kg", "order_volume_m3", "deferred_yesterday", "days_since_last_served",
    },
    "Test Data/task2b_peak_day_fleet.csv": {"scenario", "vehicle_id", "status"},
}  # fmt: skip

OPTIONAL: dict[str, set[str]] = {
    "Training Data/route_legs_train.csv": {
        "district", "planned_depart_time", "planned_travel_duration_min",
        "actual_travel_duration_min",
    },
}  # fmt: skip


class DatasetError(RuntimeError):
    """The dataset pack is missing or doesn't have the expected layout."""


@dataclass(frozen=True)
class Dataset:
    root: Path

    def path(self, relative: str) -> Path:
        return self.root / "data" / relative

    def read(self, relative: str) -> pd.DataFrame:
        return pd.read_csv(self.path(relative), dtype=str, keep_default_na=False)

    def has(self, relative: str) -> bool:
        return self.path(relative).is_file()


def _hint(root: Path) -> str:
    return (
        f"Expected the organisers' Tech-Triathlon 2026 dataset pack at '{root}'.\n"
        "Copy the pack so that it contains 'data/General Data/outlets.csv' etc. "
        "(set DATASET_DIR to use another folder). The data is confidential: never commit it. "
        "See README › Quick start and docs/09-seed-and-demo.md."
    )


def load_dataset(root: Path) -> Dataset:
    dataset = Dataset(root)
    problems: list[str] = []
    for relative, columns in REQUIRED.items():
        if not dataset.has(relative):
            problems.append(f"missing file: data/{relative}")
            continue
        header = set(pd.read_csv(dataset.path(relative), nrows=0).columns)
        if missing := columns - header:
            problems.append(f"data/{relative} lacks columns: {', '.join(sorted(missing))}")
    if problems:
        raise DatasetError("\n".join(["Dataset pack check failed:", *problems, "", _hint(root)]))
    return dataset
