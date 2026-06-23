"""Data-access layer for the articles table.

All queries go through this module so the service layer never touches SQL
directly.  Uses SQLAlchemy async session.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Author, Category
from app.schemas import ArticleCreate, ArticleUpdate

# ---------------------------------------------------------------------------
# Valid sort options
# ---------------------------------------------------------------------------
_SORT_MAP = {
    "published_at": Article.published_at.asc(),
    "-published_at": Article.published_at.desc(),
    "title": Article.title.asc(),
    "-title": Article.title.desc(),
}
_DEFAULT_SORT = "-published_at"


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class ArticleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get(self, article_id: uuid.UUID) -> Optional[Article]:
        """Return a live Article by primary key or None (excludes soft-deleted)."""
        result = await self._session.execute(
            select(Article).where(
                Article.id == article_id,
                Article.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        category: Optional[str] = None,
        author: Optional[str] = None,
        published_from: Optional[datetime] = None,
        published_to: Optional[datetime] = None,
        sort: str = _DEFAULT_SORT,
    ) -> Tuple[List[Article], int]:
        """Return (items, total) for a paginated, filtered, sorted query."""
        stmt = select(Article).where(Article.deleted_at.is_(None))
        count_stmt = (
            select(func.count())
            .select_from(Article)
            .where(Article.deleted_at.is_(None))
        )

        if category:
            cond = Article.category_ref.has(Category.name == category)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if author:
            cond = Article.author_ref.has(Author.name == author)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if published_from:
            stmt = stmt.where(Article.published_at >= published_from)
            count_stmt = count_stmt.where(Article.published_at >= published_from)
        if published_to:
            stmt = stmt.where(Article.published_at <= published_to)
            count_stmt = count_stmt.where(Article.published_at <= published_to)

        order_col = _SORT_MAP.get(sort, _SORT_MAP[_DEFAULT_SORT])
        stmt = stmt.order_by(order_col)

        offset = (page - 1) * size
        stmt = stmt.offset(offset).limit(size)

        total_result = await self._session.execute(count_stmt)
        total: int = total_result.scalar_one()

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def _resolve_category_id(self, name: str) -> int:
        """Map a category name to its id (categories are a fixed seeded set)."""
        result = await self._session.execute(
            select(Category.id).where(Category.name == name)
        )
        cid = result.scalar_one_or_none()
        if cid is None:
            raise ValueError(f"Unknown category: {name!r}")
        return cid

    async def _get_or_create_author_id(self, name: str) -> int:
        """Resolve an author name to its id, inserting the author if new."""
        await self._session.execute(
            pg_insert(Author).values(name=name).on_conflict_do_nothing(index_elements=[Author.name])
        )
        result = await self._session.execute(
            select(Author.id).where(Author.name == name)
        )
        return result.scalar_one()

    async def create(
        self,
        data: ArticleCreate,
        embedding: Optional[List[float]] = None,
    ) -> Article:
        """Insert a new article and return it with server-generated fields."""
        content_hash = _compute_hash(data.content)
        published_at = data.published_at or datetime.now(tz=timezone.utc)

        article = Article(
            id=uuid.uuid4(),
            legacy_id=None,
            title=data.title,
            content=data.content,
            author_id=await self._get_or_create_author_id(data.author),
            category_id=await self._resolve_category_id(data.category),
            published_at=published_at,
            content_hash=content_hash,
            embedding=embedding,
        )
        self._session.add(article)
        await self._session.flush()
        return article

    async def update(
        self,
        article: Article,
        data: ArticleUpdate,
        embedding: Optional[List[float]] = None,
    ) -> Article:
        """Apply partial update to an article."""
        changes: dict = {}

        if data.title is not None:
            changes["title"] = data.title
        if data.content is not None:
            changes["content"] = data.content
            changes["content_hash"] = _compute_hash(data.content)
        if data.author is not None:
            changes["author_id"] = await self._get_or_create_author_id(data.author)
        if data.category is not None:
            changes["category_id"] = await self._resolve_category_id(data.category)
        if data.published_at is not None:
            changes["published_at"] = data.published_at
        if embedding is not None:
            changes["embedding"] = embedding

        if changes:
            await self._session.execute(
                update(Article)
                .where(Article.id == article.id)
                .values(**changes)
            )
            await self._session.flush()

        return article

    async def distinct_authors(self) -> List[str]:
        """Return author names that have at least one live article (sorted).

        Joins the master table to live articles so the facet never offers an
        author whose only articles were soft-deleted. Uses the author_id index.
        """
        result = await self._session.execute(
            select(Author.name)
            .join(Article, Article.author_id == Author.id)
            .where(Article.deleted_at.is_(None))
            .distinct()
            .order_by(Author.name)
        )
        return [row[0] for row in result.all()]

    async def delete(self, article: Article) -> None:
        """Soft-delete an article (set deleted_at); the row is retained."""
        await self._session.execute(
            update(Article)
            .where(Article.id == article.id)
            .values(deleted_at=func.now())
        )
        await self._session.flush()
