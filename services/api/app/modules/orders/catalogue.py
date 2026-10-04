"""Original demo case measurements, never derived from the competition pack.

Products have no physical measurements in the foundation schema. These server-side
fixtures make app-created orders usable by the planning engine; seeded orders retain
 their authoritative per-case aggregate measurements (ADR-0008).
"""

# kg / m³ per case: illustrative fixtures, not measured operational catalogue data.
CASE_MEASUREMENTS: dict[str, tuple[float, float]] = {
    "milk-1l": (12.0, 0.024),
    "yoghurt-1kg": (6.0, 0.012),
    "butter-200g": (4.8, 0.009),
    "chicken-whole": (12.0, 0.024),
    "fish-fillet": (10.0, 0.020),
    "rice-5kg": (20.0, 0.032),
    "tea-400g": (8.0, 0.016),
}
