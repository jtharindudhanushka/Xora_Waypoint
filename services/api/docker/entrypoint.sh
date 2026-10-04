#!/bin/sh
# Container entrypoint: migrate → seed (idempotent) → serve.
set -e
alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
