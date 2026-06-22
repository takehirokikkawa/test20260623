"""Pydantic v2 schemas for request/response shapes.

These schemas are the single source of truth for the OpenAPI spec that the
frontend uses to generate its TypeScript types.

Internal fields (``content_hash``, ``embedding``) are deliberately excluded
from all response schemas.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Article response
# ---------------------------------------------------------------------------

class Article(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legacy_id: Optional[int] = None
    title: str
    content: str
    author: str
    category: str
    published_at: datetime
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Create / Update request bodies
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {"AI/ML", "Backend", "Frontend", "DevOps"}


class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1, max_length=120)
    category: str
    published_at: Optional[datetime] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(
                f"category must be one of {sorted(VALID_CATEGORIES)}, got {v!r}"
            )
        return v


class ArticleUpdate(BaseModel):
    """All fields optional for partial updates."""

    title: Optional[str] = Field(None, min_length=1, max_length=300)
    content: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1, max_length=120)
    category: Optional[str] = None
    published_at: Optional[datetime] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_CATEGORIES:
            raise ValueError(
                f"category must be one of {sorted(VALID_CATEGORIES)}, got {v!r}"
            )
        return v


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int) -> "Page[T]":
        pages = max(1, math.ceil(total / size)) if size > 0 else 1
        return cls(items=items, total=total, page=page, size=size, pages=pages)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class Signals(BaseModel):
    """Hit-reason metadata returned alongside each search result."""

    lexical: bool = False
    fuzzy: bool = False
    semantic: bool = False
    vector_distance: Optional[float] = None
    ts_rank: Optional[float] = None


class SearchHit(BaseModel):
    article: Article
    score: float
    signals: Signals


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[SearchHit]
