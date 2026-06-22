"""CRUD endpoints for articles.

Routes
------
GET    /api/articles          list_articles
GET    /api/articles/{id}     get_article
POST   /api/articles          create_article
PUT    /api/articles/{id}     update_article
DELETE /api/articles/{id}     delete_article

Session sharing: FastAPI deduplicates Depends(get_session) per request,
so the session injected into _get_service and into the route handler is the
same object.  The route handler calls session.commit() after the service
has flushed changes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import (
    Article,
    ArticleCreate,
    ArticleUpdate,
    FacetsResponse,
    ImportResult,
    Page,
)
from app.services.article_service import ArticleService
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/articles", tags=["articles"])


# ---------------------------------------------------------------------------
# Bulk CSV import (defined before "/{article_id}" routes; distinct path/method)
# ---------------------------------------------------------------------------

@router.post("/import", response_model=ImportResult, status_code=status.HTTP_200_OK)
async def import_articles(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Import articles from an uploaded CSV.

    Follows the same pipeline as the initial ingest: content-hash embedding
    cache, UUID + legacy_id, idempotent ON CONFLICT (legacy_id) DO NOTHING.
    """
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")
    raw = await file.read()
    if not raw.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        result = await ImportService(session).import_csv(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


# ---------------------------------------------------------------------------
# Facets (filter choices for the UI)
# ---------------------------------------------------------------------------

@router.get("/facets", response_model=FacetsResponse, status_code=status.HTTP_200_OK)
async def get_facets(session: AsyncSession = Depends(get_session)):
    return await ArticleService(session).facets()


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("", response_model=Page[Article], status_code=status.HTTP_200_OK)
async def list_articles(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    author: Optional[str] = Query(default=None),
    published_from: Optional[datetime] = Query(default=None),
    published_to: Optional[datetime] = Query(default=None),
    sort: str = Query(
        default="-published_at",
        pattern=r"^-?(?:published_at|title)$",
    ),
    session: AsyncSession = Depends(get_session),
):
    service = ArticleService(session)
    items, total = await service.list_articles(
        page=page,
        size=size,
        category=category,
        author=author,
        published_from=published_from,
        published_to=published_to,
        sort=sort,
    )
    article_schemas = [Article.model_validate(item) for item in items]
    return Page[Article].create(
        items=article_schemas, total=total, page=page, size=size
    )


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

@router.get("/{article_id}", response_model=Article, status_code=status.HTTP_200_OK)
async def get_article(
    article_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    service = ArticleService(session)
    article = await service.get_article(article_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )
    return Article.model_validate(article)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("", response_model=Article, status_code=status.HTTP_201_CREATED)
async def create_article(
    body: ArticleCreate,
    session: AsyncSession = Depends(get_session),
):
    service = ArticleService(session)
    article = await service.create_article(body)
    return Article.model_validate(article)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.put("/{article_id}", response_model=Article, status_code=status.HTTP_200_OK)
async def update_article(
    article_id: uuid.UUID,
    body: ArticleUpdate,
    session: AsyncSession = Depends(get_session),
):
    service = ArticleService(session)
    article = await service.update_article(article_id, body)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )
    return Article.model_validate(article)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{article_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_article(
    article_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    service = ArticleService(session)
    deleted = await service.delete_article(article_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )
