"""Schema validation tests — no DB required.

Tests cover:
- ArticleCreate / ArticleUpdate validation (happy path + rejection).
- Page.create() pagination maths.
- Signals / SearchHit / SearchResponse construction.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    Article,
    ArticleCreate,
    ArticleUpdate,
    Page,
    SearchHit,
    SearchResponse,
    Signals,
)


# ---------------------------------------------------------------------------
# ArticleCreate
# ---------------------------------------------------------------------------

class TestArticleCreate:
    def test_valid_payload(self, sample_article_data):
        obj = ArticleCreate(**sample_article_data)
        assert obj.title == "Understanding Vector Databases"
        assert obj.category == "AI/ML"

    def test_invalid_category(self, sample_article_data):
        sample_article_data["category"] = "InvalidCat"
        with pytest.raises(ValidationError, match="category must be one of"):
            ArticleCreate(**sample_article_data)

    def test_title_too_long(self, sample_article_data):
        sample_article_data["title"] = "x" * 301
        with pytest.raises(ValidationError):
            ArticleCreate(**sample_article_data)

    def test_empty_title(self, sample_article_data):
        sample_article_data["title"] = ""
        with pytest.raises(ValidationError):
            ArticleCreate(**sample_article_data)

    def test_empty_content(self, sample_article_data):
        sample_article_data["content"] = ""
        with pytest.raises(ValidationError):
            ArticleCreate(**sample_article_data)

    def test_optional_published_at(self, sample_article_data):
        sample_article_data.pop("published_at", None)
        obj = ArticleCreate(**sample_article_data)
        assert obj.published_at is None

    def test_all_valid_categories(self, sample_article_data):
        for cat in ("AI/ML", "Backend", "Frontend", "DevOps"):
            sample_article_data["category"] = cat
            obj = ArticleCreate(**sample_article_data)
            assert obj.category == cat


# ---------------------------------------------------------------------------
# ArticleUpdate
# ---------------------------------------------------------------------------

class TestArticleUpdate:
    def test_all_none(self):
        obj = ArticleUpdate()
        assert obj.title is None
        assert obj.content is None
        assert obj.category is None

    def test_partial_update(self, sample_article_update_data):
        obj = ArticleUpdate(**sample_article_update_data)
        assert obj.title == "Understanding Vector DBs (revised)"
        assert obj.content is None

    def test_invalid_category(self):
        with pytest.raises(ValidationError, match="category must be one of"):
            ArticleUpdate(category="NotACategory")

    def test_valid_category(self):
        obj = ArticleUpdate(category="Backend")
        assert obj.category == "Backend"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

class TestPage:
    def test_page_create_basic(self):
        page = Page[dict].create(
            items=[{"id": 1}, {"id": 2}],
            total=50,
            page=1,
            size=20,
        )
        assert page.total == 50
        assert page.pages == 3
        assert page.page == 1
        assert page.size == 20
        assert len(page.items) == 2

    def test_page_exact_multiple(self):
        page = Page[dict].create(items=[], total=100, page=5, size=20)
        assert page.pages == 5

    def test_page_single(self):
        page = Page[dict].create(items=[], total=5, page=1, size=20)
        assert page.pages == 1

    def test_page_empty(self):
        page = Page[dict].create(items=[], total=0, page=1, size=20)
        assert page.pages == 1  # at least 1 page even when empty

    def test_page_partial_last(self):
        page = Page[dict].create(items=[], total=21, page=2, size=20)
        assert page.pages == 2


# ---------------------------------------------------------------------------
# SearchResponse
# ---------------------------------------------------------------------------

class TestSearchResponse:
    def _make_article_dict(self):
        return {
            "id": "f1c2d3e4-1111-2222-3333-444444444444",
            "legacy_id": 1,
            "title": "Test Article",
            "content": "Some content here.",
            "author": "Bob",
            "category": "Backend",
            "published_at": "2024-01-01T00:00:00Z",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

    def test_search_response_construction(self):
        art = Article(**self._make_article_dict())
        sig = Signals(lexical=True, semantic=True, vector_distance=0.21, ts_rank=0.087)
        hit = SearchHit(article=art, score=0.0489, signals=sig)
        resp = SearchResponse(query="test query", count=1, results=[hit])

        assert resp.query == "test query"
        assert resp.count == 1
        assert resp.results[0].signals.lexical is True
        assert resp.results[0].signals.fuzzy is False

    def test_signals_defaults(self):
        sig = Signals()
        assert sig.lexical is False
        assert sig.fuzzy is False
        assert sig.semantic is False
        assert sig.vector_distance is None
        assert sig.ts_rank is None
