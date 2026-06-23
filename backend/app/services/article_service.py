"""Business logic layer for article CRUD.

Orchestrates the repository and the embedding generator.  The embedding is
(re)computed whenever:
  - A new article is created.
  - An update changes ``title`` or ``content``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app import embeddings as emb
from app.models import Article
from app.repositories.article_repository import ArticleRepository
from app.schemas import CATEGORY_CHOICES, ArticleCreate, ArticleUpdate, FacetsResponse


class ArticleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ArticleRepository(session)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_article(self, article_id: uuid.UUID) -> Optional[Article]:
        return await self._repo.get(article_id)

    async def list_articles(
        self,
        *,
        page: int = 1,
        size: int = 20,
        category: Optional[str] = None,
        author: Optional[str] = None,
        published_from: Optional[datetime] = None,
        published_to: Optional[datetime] = None,
        sort: str = "-published_at",
    ) -> Tuple[List[Article], int]:
        return await self._repo.list(
            page=page,
            size=size,
            category=category,
            author=author,
            published_from=published_from,
            published_to=published_to,
            sort=sort,
        )

    async def facets(self) -> FacetsResponse:
        """Filter choices for the UI: fixed category set + live authors."""
        authors = await self._repo.distinct_authors()
        return FacetsResponse(categories=list(CATEGORY_CHOICES), authors=authors)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_article(self, data: ArticleCreate) -> Article:
        """Create a new article with a freshly generated embedding.

        Owns the transaction boundary (commits) so routers stay free of
        scattered commit calls (review item A3).
        """
        embedding = await emb.aembed_text(emb.document_text(data.content))
        article = await self._repo.create(data, embedding=embedding)
        await self._session.commit()
        # Re-fetch so joined category/author relationships and server defaults
        # are populated for the response.
        return await self._repo.get(article.id)

    async def update_article(
        self, article_id: uuid.UUID, data: ArticleUpdate
    ) -> Optional[Article]:
        """Partially update an article; regenerate embedding if content changed."""
        article = await self._repo.get(article_id)
        if article is None:
            return None

        # Embedding depends only on content (see embeddings.document_text).
        embedding: Optional[List[float]] = None
        if data.content is not None and data.content != article.content:
            embedding = await emb.aembed_text(emb.document_text(data.content))

        await self._repo.update(article, data, embedding=embedding)
        await self._session.commit()
        return await self._repo.get(article_id)

    async def delete_article(self, article_id: uuid.UUID) -> bool:
        """Soft-delete an article.  Returns True if it existed, False otherwise."""
        article = await self._repo.get(article_id)
        if article is None:
            return False
        await self._repo.delete(article)
        await self._session.commit()
        return True
