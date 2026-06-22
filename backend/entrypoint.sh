#!/usr/bin/env bash
# Entrypoint for both the one-shot "migrate" job and the long-running "serve" process.
#   ./entrypoint.sh migrate   -> alembic upgrade head + idempotent CSV ingest, then exit
#   ./entrypoint.sh serve     -> start uvicorn
set -euo pipefail

MODE="${1:-serve}"

wait_for_db() {
  echo "[entrypoint] waiting for database..."
  python - <<'PY'
import os, time, sys
import psycopg2
url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ["DATABASE_URL"]
# psycopg2 wants a libpq DSN; strip the SQLAlchemy driver prefix.
dsn = url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")
for attempt in range(30):
    try:
        psycopg2.connect(dsn).close()
        print("[entrypoint] database is ready")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print(f"[entrypoint] db not ready ({attempt+1}/30): {e}")
        time.sleep(2)
sys.exit("[entrypoint] database did not become ready in time")
PY
}

case "$MODE" in
  migrate)
    wait_for_db
    echo "[entrypoint] running alembic migrations..."
    alembic upgrade head
    echo "[entrypoint] ingesting CSV..."
    python -m app.scripts.ingest_csv
    echo "[entrypoint] migrate job done."
    ;;
  serve)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 1
    ;;
esac
