"""pytest configuration and shared fixtures.

All tests in this suite that require only schema validation or pure-function
logic run WITHOUT a database connection, keeping them fast and portable.

If you later add integration tests that need a live DB, add an async fixture
here that creates the engine from TEST_DATABASE_URL.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_article_data() -> dict:
    """Return a valid ArticleCreate payload as a dict."""
    return {
        "title": "Understanding Vector Databases",
        "content": "Vector databases store embeddings for semantic search.",
        "author": "Alice Tanaka",
        "category": "AI/ML",
        "published_at": "2024-05-01T00:00:00Z",
    }


@pytest.fixture
def sample_article_update_data() -> dict:
    """Return a valid ArticleUpdate payload as a dict (partial)."""
    return {
        "title": "Understanding Vector DBs (revised)",
    }
