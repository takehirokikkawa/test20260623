"""Hybrid search endpoint.

GET /api/search?q=<query>[&category=...][&author=...][&limit=...]
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search(
    q: str = Query(..., min_length=1, description="Natural-language search query"),
    category: Optional[str] = Query(default=None, description="Facet filter by category"),
    author: Optional[str] = Query(default=None, description="Facet filter by author"),
    limit: int = Query(default=20, ge=1, le=50, description="Max results to return"),
    session: AsyncSession = Depends(get_session),
):
    service = SearchService(session)
    return await service.search(
        q,
        category=category,
        author=author,
        limit=limit,
    )
