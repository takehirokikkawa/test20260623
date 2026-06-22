"""Idempotent CSV ingest script.

Usage (run after alembic upgrade head):
    python -m app.scripts.ingest_csv

Algorithm
---------
1. Read CSV_PATH (default /data/articles.csv).
2. Compute content_hash = sha256(content) for each row.
3. Collect the UNIQUE content hashes, batch-embed them once using the local
   SentenceTransformer model (avoids recomputing identical embeddings).
4. For each CSV row assign a fresh UUID, keep legacy_id = csv.id.
5. Batch-INSERT rows 500 at a time with ON CONFLICT (legacy_id) DO NOTHING
   so re-runs skip already-inserted rows.
6. Log inserted / skipped counts.

This script runs synchronously via psycopg2 so it works standalone without
an asyncio event loop, matching the entrypoint's `python -m app.scripts.ingest_csv`.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

BATCH_SIZE = 500


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _parse_published_at(value: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM:SS' and return a timezone-aware UTC datetime."""
    try:
        dt = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # Fallback: try ISO 8601 with T separator
        dt = datetime.fromisoformat(value.strip())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def run() -> None:
    # ------------------------------------------------------------------
    # Configuration from environment
    # ------------------------------------------------------------------
    csv_path = os.environ.get("CSV_PATH", "/data/articles.csv")
    db_url = os.environ.get(
        "ALEMBIC_DATABASE_URL",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg2://techinsight:techinsight@localhost:5432/techinsight",
        ),
    )
    # Normalise to a plain libpq DSN for psycopg2.
    db_url = (
        db_url
        .replace("postgresql+psycopg2://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )

    embedding_model = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    log.info("CSV path: %s", csv_path)
    log.info("Embedding model: %s", embedding_model)

    # ------------------------------------------------------------------
    # Read CSV
    # ------------------------------------------------------------------
    log.info("Reading CSV...")
    rows: List[dict] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)

    total_rows = len(rows)
    log.info("Loaded %d rows from CSV.", total_rows)

    # ------------------------------------------------------------------
    # Compute content hashes and collect unique ones
    # ------------------------------------------------------------------
    log.info("Computing content hashes...")
    for row in rows:
        row["_hash"] = _compute_hash(row["content"])

    unique_hashes: List[str] = list(dict.fromkeys(r["_hash"] for r in rows))
    log.info(
        "Unique content hashes: %d (out of %d rows, %.0f%% dedup savings).",
        len(unique_hashes),
        total_rows,
        100.0 * (1 - len(unique_hashes) / max(total_rows, 1)),
    )

    # ------------------------------------------------------------------
    # Batch-embed unique contents (one embedding per unique hash)
    # ------------------------------------------------------------------
    log.info("Loading embedding model '%s'...", embedding_model)
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

    model = SentenceTransformer(embedding_model)

    # Map: hash -> content string for the unique set
    hash_to_content: Dict[str, str] = {}
    for row in rows:
        h = row["_hash"]
        if h not in hash_to_content:
            hash_to_content[h] = row["content"]

    unique_contents = [hash_to_content[h] for h in unique_hashes]

    log.info("Embedding %d unique contents...", len(unique_contents))
    embeddings_list = model.encode(
        unique_contents,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=64,
    )

    # Map: hash -> embedding vector (as Python list for psycopg2)
    hash_to_embedding: Dict[str, List[float]] = {
        unique_hashes[i]: embeddings_list[i].tolist()
        for i in range(len(unique_hashes))
    }
    log.info("Embeddings computed.")

    # ------------------------------------------------------------------
    # Connect to PostgreSQL
    # ------------------------------------------------------------------
    import psycopg2  # noqa: PLC0415
    import psycopg2.extras  # noqa: PLC0415

    log.info("Connecting to database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # Batch INSERT with ON CONFLICT DO NOTHING
    # ------------------------------------------------------------------
    insert_sql = """
        INSERT INTO articles
            (id, legacy_id, title, content, author, category, published_at,
             content_hash, embedding)
        VALUES %s
        ON CONFLICT (legacy_id) DO NOTHING
    """

    def _row_to_tuple(row: dict):
        article_id = str(uuid.uuid4())
        legacy_id = int(row["id"])
        title = row["title"]
        content = row["content"]
        author = row["author"]
        category = row["category"]
        published_at = _parse_published_at(row["published_at"])
        content_hash = row["_hash"]
        embedding = hash_to_embedding[content_hash]
        # psycopg2 needs the vector as a string like '[0.1, 0.2, ...]'
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        return (
            article_id,
            legacy_id,
            title,
            content,
            author,
            category,
            published_at,
            content_hash,
            embedding_str,
        )

    log.info("Inserting %d rows in batches of %d...", total_rows, BATCH_SIZE)
    inserted_total = 0
    skipped_total = 0

    for batch_start in range(0, total_rows, BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]
        tuples = [_row_to_tuple(r) for r in batch]

        # We need to handle the vector column specially.
        # Build VALUES manually to allow casting embedding to vector type.
        # Use execute_values with a template that casts the last placeholder.
        template = (
            "(%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)"
        )

        before_count = _get_row_count(cur)
        psycopg2.extras.execute_values(
            cur,
            insert_sql,
            tuples,
            template=template,
            page_size=BATCH_SIZE,
        )
        conn.commit()
        after_count = _get_row_count(cur)

        batch_inserted = after_count - before_count
        batch_skipped = len(batch) - batch_inserted
        inserted_total += batch_inserted
        skipped_total += batch_skipped

        log.info(
            "Batch %d-%d: inserted %d, skipped %d.",
            batch_start + 1,
            batch_start + len(batch),
            batch_inserted,
            batch_skipped,
        )

    cur.close()
    conn.close()

    log.info(
        "Ingest complete. Total inserted: %d, total skipped (already existed): %d.",
        inserted_total,
        skipped_total,
    )


def _get_row_count(cur) -> int:
    cur.execute("SELECT COUNT(*) FROM articles;")
    return cur.fetchone()[0]


if __name__ == "__main__":
    run()
