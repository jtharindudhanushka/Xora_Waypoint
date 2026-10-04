"""`python -m app.seed [--reset-demo]` — run by the api container before the server starts.

* Reference data is merged on every run (idempotent).
* The demo day is inserted only on the first run, so a server restart never wipes a judge's
  progress. Pass --reset-demo (or SEED_RESET_DEMO=true) to start the demo again from scratch.
Exit codes: 0 ok · 2 dataset pack missing or malformed · 1 any other failure.
"""

from __future__ import annotations

import argparse
import sys

from app.core.config import get_settings
from app.core.db import session_factory
from app.core.logging import configure_logging, get_logger
from app.seed.dataset import DatasetError, load_dataset
from app.seed.demo import is_demo_seeded, reset_demo, seed_demo
from app.seed.reference import load_reference, load_travel_ratios


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.seed")
    parser.add_argument("--reset-demo", action="store_true", help="wipe and re-seed the demo day")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level, json=settings.is_production)
    log = get_logger("seed")

    try:
        ds = load_dataset(settings.dataset_dir)
    except DatasetError as exc:
        print(exc, file=sys.stderr)
        return 2

    with session_factory()() as session, session.begin():
        log.info("seed.reference", **load_reference(session, ds))
        log.info("seed.travel_ratios", rows=load_travel_ratios(session, ds))
        reset = args.reset_demo or settings.seed_reset_demo
        if reset:
            reset_demo(session)
        if reset or not is_demo_seeded(session):
            log.info("seed.demo", **seed_demo(session, ds, settings.demo_start))
        else:
            log.info("seed.demo.skipped", reason="already seeded; use --reset-demo to start over")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
