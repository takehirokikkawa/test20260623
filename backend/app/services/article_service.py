"""Business logic layer for article CRUD.

Orchestrates the repository and the embedding generator.  The embedding is
(re)computed whenever:
  - A new article is created.
  - An update changes ``title`` or ``content``.
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app import embeddings as emb
from app.models import Article
from app.repositories.article_repository import ArticleRepository
from app.schemas import ArticleCreate, ArticleUpdate


class ArticleService:
    def __init__(self, session: AsyncSession) -> None:
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
        sort: str = "-published_at",
    ) -> Tuple[List[Article], int]:
        return await self._repo.list(
            page=page,
            size=size,
            category=category,
            author=author,
            sort=sort,
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_article(self, data: ArticleCreate) -> Article:
        """Create a new article with a freshly generated embedding."""
        text_for_embedding = f"{data.title} {data.content}"
        embedding = emb.embed_text(text_for_embedding)
        return await self._repo.create(data, embedding=embedding)

    async def update_article(
        self, article_id: uuid.UUID, data: ArticleUpdate
    ) -> Optional[Article]:
        """Partially update an article; regenerate embedding if text changed."""
        article = await self._repo.get(article_id)
        if article is None:
            return None

        embedding: Optional[List[float]] = None
        title_changed = data.title is not None and data.title != article.title
        content_changed = (
            data.content is not None and data.content != article.content
        )

        if title_changed or content_changed:
            new_title = data.title if data.title is not None else article.title
            new_content = (
                data.content if data.content is not None else article.content
            )
            embedding = emb.embed_text(f"{new_title} {new_content}")

        return await self._repo.update(article, data, embedding=embedding)

    async def delete_article(self, article_id: uuid.UUID) -> bool:
        """Delete an article.  Returns True if it existed, False otherwise."""
        article = await self._repo.get(article_id)
        if article is None:
            return False
        await self._repo.delete(article)
        return True
