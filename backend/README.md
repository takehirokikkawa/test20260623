# TechInsight — Backend

FastAPI backend for the TechInsight AI knowledge base.

## Quick start (full stack)

```bash
# From the repo root:
docker compose up --build
# API docs: http://localhost:8000/docs
# Health:   http://localhost:8000/health
```

## Local development (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
# Install CPU torch first to avoid CUDA downloads:
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1
pip install -r requirements.txt

# Set env vars (or copy .env.example):
export DATABASE_URL="postgresql+asyncpg://techinsight:techinsight@localhost:5432/techinsight"
export ALEMBIC_DATABASE_URL="postgresql+psycopg2://techinsight:techinsight@localhost:5432/techinsight"
export CSV_PATH="../data/articles.csv"

# Run migrations:
alembic upgrade head

# Ingest CSV:
python -m app.scripts.ingest_csv

# Start the server:
uvicorn app.main:app --reload --port 8000
```

## Project layout

```
backend/
  alembic/                # Alembic migration scripts
    versions/0001_initial.py
  app/
    main.py               # FastAPI app, CORS, router includes
    config.py             # pydantic-settings (env vars)
    db.py                 # async engine + session dependency
    models.py             # SQLAlchemy Article model
    schemas.py            # Pydantic v2 request/response schemas
    embeddings.py         # Lazy SentenceTransformer singleton
    repositories/
      article_repository.py
    services/
      article_service.py  # CRUD + embedding orchestration
      search_service.py   # Hybrid RRF search
    routers/
      articles.py         # CRUD endpoints
      search.py           # GET /api/search
      health.py           # GET /health
    scripts/
      ingest_csv.py       # Idempotent CSV import
  tests/
    test_schemas.py       # Schema validation unit tests
    test_search_fusion.py # RRF pure-function unit tests
```

## Running tests

```bash
pytest tests/ -v
```

The test suite requires only `pytest`, `pydantic`, and standard library
modules — no database, no torch, no network.

## Hybrid search (RRF)

The `/api/search` endpoint executes three PostgreSQL queries in parallel
and merges them via Reciprocal Rank Fusion:

| Stream    | Query | Weight |
|-----------|-------|--------|
| Lexical   | `search_tsv @@ websearch_to_tsquery(...)` ordered by `ts_rank` | 1.0 |
| Fuzzy     | `similarity(title, q) > 0.1` ordered by similarity | 0.5 |
| Vector    | `embedding <=> :qvec` (HNSW cosine ANN) | 1.0 |

RRF formula: `score = Σ weight_i / (k + rank_i)` with `k=60`.

Each result includes `signals` indicating which streams it matched and raw
scores (`ts_rank`, `vector_distance`) for explainability.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async DB URL for FastAPI |
| `ALEMBIC_DATABASE_URL` | derived from above | Sync DB URL for Alembic |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace model name |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `CSV_PATH` | `/data/articles.csv` | Path to the CSV to ingest |
| `TRANSFORMERS_OFFLINE` | `1` (in Docker) | Prevent HF hub network calls |
| `HF_HUB_OFFLINE` | `1` (in Docker) | Prevent HF hub network calls |
