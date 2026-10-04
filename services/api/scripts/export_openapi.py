"""Write the API contract to services/api/openapi.json (consumed by `npm run gen:api`).

Run after changing any schema or route:  python scripts/export_openapi.py
CI fails if the committed file is out of date, so the web client never drifts from the API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from app.main import create_app  # noqa: E402

OUT = API_DIR / "openapi.json"


def main() -> None:
    OUT.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(API_DIR.parents[1])}")


if __name__ == "__main__":
    main()
