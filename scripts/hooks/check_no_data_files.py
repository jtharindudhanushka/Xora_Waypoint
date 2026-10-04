"""Pre-commit hook: block competition data and derivatives from being committed (ADR-0007)."""

from __future__ import annotations

import sys
from pathlib import PurePosixPath

BLOCKED_SUFFIXES = {".csv", ".parquet", ".xlsx", ".pdf", ".dump", ".joblib", ".pkl"}
BLOCKED_PARTS = {"datasets", "Training Data", "Test Data", "General Data", "Submission Templates"}
ALLOWED_PREFIXES = ("services/api/tests/fixtures/", "packages/engine/tests/fixtures/")


def is_blocked(path: str) -> bool:
    if path.startswith(ALLOWED_PREFIXES):
        return False
    p = PurePosixPath(path.replace("\\", "/"))
    return p.suffix.lower() in BLOCKED_SUFFIXES or bool(BLOCKED_PARTS & set(p.parts))


def main(argv: list[str]) -> int:
    blocked = [f for f in argv if is_blocked(f)]
    for f in blocked:
        print(f"Blocked: {f} looks like competition data. See ADR-0007; never commit datasets.")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
