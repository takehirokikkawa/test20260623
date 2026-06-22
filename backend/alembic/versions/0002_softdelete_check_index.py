"""Soft-delete column, category CHECK constraint, composite index.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-23

Addresses review items:
  * logical delete  -> articles.deleted_at
  * category integrity (no CHECK) -> ck_articles_category
  * facet + sort speed -> idx_articles_category_published
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Soft delete: NULL = live, non-NULL = deleted timestamp.
    op.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;")

    # Enforce the allowed category set at the DB level.
    op.execute(
        """
        ALTER TABLE articles
        ADD CONSTRAINT ck_articles_category
        CHECK (category IN ('AI/ML', 'Backend', 'Frontend', 'DevOps'));
        """
    )

    # Speeds up "filter by category + sort by recency" (facet browsing).
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_category_published "
        "ON articles (category, published_at DESC);"
    )

    # Keep live-row scans cheap (most queries filter deleted_at IS NULL).
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_live "
        "ON articles (published_at DESC) WHERE deleted_at IS NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_articles_live;")
    op.execute("DROP INDEX IF EXISTS idx_articles_category_published;")
    op.execute("ALTER TABLE articles DROP CONSTRAINT IF EXISTS ck_articles_category;")
    op.execute("ALTER TABLE articles DROP COLUMN IF EXISTS deleted_at;")
