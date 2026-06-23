"""Bulk CSV import service.

This is the UI/API counterpart of ``app.scripts.ingest_csv`` and follows the
SAME requirement-compliant pipeline:

  * accepts the provided CSV format (``id,title,content,author,category,published_at``)
  * validates each row and reports row-level errors
  * assigns a fresh UUID per row, keeps the CSV ``id`` as ``legacy_id``
  * embeds the **unique** contents only once (content-hash cache) and reuses them
  * inserts idempotently via ``ON CONFLICT (legacy_id) DO NOTHING`` so re-uploading
    the same file does not create duplicates

It runs on the async request session. The (CPU-bound) embedding step is offloaded
to a worker thread so the event loop is not blocked.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import embeddings as emb
from app.models import Article, Author, Category
from app.schemas import ImportResult, ImportRowError

VALID_CATEGORIES = {"AI/ML", "Backend", "Frontend", "DevOps"}
REQUIRED_COLUMNS = {"title", "content", "author", "category"}
MAX_REPORTED_ERRORS = 100


def _parse_published_at(value: Optional[str]) -> datetime:
    """Parse the CSV timestamp; default to now() (UTC) when absent/invalid."""
    if not value or not value.strip():
        return datetime.now(tz=timezone.utc)
    s = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(tz=timezone.utc)


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_csv(raw: bytes) -> tuple[list[dict], list[ImportRowError], int]:
    """Pure parse+validate of CSV bytes (no DB, no embeddings — unit-testable).

    Returns (valid_rows, errors, total_data_rows). Each valid row is a dict with
    legacy_id/title/content/author/category/published_at. Raises ``ValueError``
    if the header is missing required columns.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not valid UTF-8 text: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text))
    headers = {(h or "").strip() for h in (reader.fieldnames or [])}
    if not REQUIRED_COLUMNS.issubset(headers):
        missing = sorted(REQUIRED_COLUMNS - headers)
        raise ValueError(
            "CSV is missing required column(s): "
            f"{', '.join(missing)}. Required: {sorted(REQUIRED_COLUMNS)}."
        )

    rows = list(reader)
    errors: list[ImportRowError] = []
    valid: list[dict] = []
    seen_legacy: set[int] = set()

    for line_no, row in enumerate(rows, start=2):  # header is line 1
        title = (row.get("title") or "").strip()
        content = (row.get("content") or "").strip()
        author = (row.get("author") or "").strip()
        category = (row.get("category") or "").strip()

        missing = [
            name
            for name, val in (("title", title), ("content", content), ("author", author), ("category", category))
            if not val
        ]
        if missing:
            errors.append(ImportRowError(row=line_no, error=f"missing required field(s): {', '.join(missing)}"))
            continue
        if category not in VALID_CATEGORIES:
            errors.append(ImportRowError(row=line_no, error=f"invalid category '{category}' (allowed: {sorted(VALID_CATEGORIES)})"))
            continue

        raw_id = (row.get("id") or "").strip()
        legacy_id: Optional[int] = None
        if raw_id:
            try:
                legacy_id = int(raw_id)
            except ValueError:
                errors.append(ImportRowError(row=line_no, error=f"invalid id '{raw_id}' (must be an integer)"))
                continue
            if legacy_id in seen_legacy:
                errors.append(ImportRowError(row=line_no, error=f"duplicate id {legacy_id} within file"))
                continue
            seen_legacy.add(legacy_id)

        valid.append(
            {
                "legacy_id": legacy_id,
                "title": title,
                "content": content,
                "author": author,
                "category": category,
                "published_at": _parse_published_at(row.get("published_at")),
            }
        )

    return valid, errors, len(rows)


class ImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def import_csv(self, raw: bytes) -> ImportResult:
        valid, errors, total = parse_csv(raw)
        invalid = total - len(valid)

        if not valid:
            return ImportResult(
                total_rows=total,
                valid=0,
                invalid=invalid,
                inserted=0,
                skipped_existing=0,
                unique_embeddings=0,
                errors=errors[:MAX_REPORTED_ERRORS],
            )

        # ---- Embedding cache: embed each unique content once -----------------
        hashes = [_content_hash(v["content"]) for v in valid]
        unique_content_by_hash: dict[str, str] = {}
        for h, v in zip(hashes, valid, strict=True):
            unique_content_by_hash.setdefault(h, v["content"])
        unique_hashes = list(unique_content_by_hash.keys())
        unique_contents = [unique_content_by_hash[h] for h in unique_hashes]

        vectors = await asyncio.to_thread(emb.embed_texts, unique_contents)
        vec_by_hash = {unique_hashes[i]: vectors[i] for i in range(len(unique_hashes))}

        # ---- Resolve normalised FK ids (categories seeded; authors upserted) -
        cat_rows = (await self._session.execute(select(Category.id, Category.name))).all()
        category_id_by_name = {name: cid for cid, name in cat_rows}
        author_names = sorted({v["author"] for v in valid})
        await self._session.execute(
            pg_insert(Author)
            .values([{"name": n} for n in author_names])
            .on_conflict_do_nothing(index_elements=[Author.name])
        )
        auth_rows = (await self._session.execute(select(Author.id, Author.name))).all()
        author_id_by_name = {name: aid for aid, name in auth_rows}

        # ---- Build records and bulk-insert idempotently ----------------------
        records = [
            {
                "id": uuid.uuid4(),
                "legacy_id": v["legacy_id"],
                "title": v["title"],
                "content": v["content"],
                "author_id": author_id_by_name[v["author"]],
                "category_id": category_id_by_name[v["category"]],
                "published_at": v["published_at"],
                "content_hash": h,
                "embedding": vec_by_hash[h],
            }
            for h, v in zip(hashes, valid, strict=True)
        ]

        stmt = (
            pg_insert(Article)
            .values(records)
            .on_conflict_do_nothing(index_elements=[Article.legacy_id])
            .returning(Article.id)
        )
        result = await self._session.execute(stmt)
        inserted = len(result.fetchall())
        await self._session.commit()
        skipped = len(valid) - inserted

        return ImportResult(
            total_rows=total,
            valid=len(valid),
            invalid=invalid,
            inserted=inserted,
            skipped_existing=skipped,
            unique_embeddings=len(unique_hashes),
            errors=errors[:MAX_REPORTED_ERRORS],
        )
