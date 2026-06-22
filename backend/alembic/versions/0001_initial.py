"""Initial schema: extensions, articles table, indexes, trigger.

Revision ID: 0001
Revises:
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # ------------------------------------------------------------------
    # articles table
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE articles (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            legacy_id     INTEGER UNIQUE,
            title         TEXT NOT NULL,
            content       TEXT NOT NULL,
            author        TEXT NOT NULL,
            category      TEXT NOT NULL,
            published_at  TIMESTAMPTZ NOT NULL,
            content_hash  TEXT NOT NULL,
            embedding     vector(384),
            search_tsv    tsvector GENERATED ALWAYS AS (
                             to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,''))
                          ) STORED,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    # Vector nearest-neighbour (cosine) — HNSW
    op.execute(
        "CREATE INDEX idx_articles_embedding_hnsw "
        "ON articles USING hnsw (embedding vector_cosine_ops);"
    )

    # Full-text search
    op.execute(
        "CREATE INDEX idx_articles_tsv ON articles USING gin (search_tsv);"
    )

    # Trigram fuzzy match on title
    op.execute(
        "CREATE INDEX idx_articles_title_trgm "
        "ON articles USING gin (title gin_trgm_ops);"
    )

    # Facet filters and sort
    op.execute("CREATE INDEX idx_articles_category ON articles (category);")
    op.execute("CREATE INDEX idx_articles_author   ON articles (author);")
    op.execute(
        "CREATE INDEX idx_articles_published ON articles (published_at DESC);"
    )

    # ------------------------------------------------------------------
    # updated_at trigger
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_articles_updated
            BEFORE UPDATE ON articles
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_articles_updated ON articles;")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
    op.execute("DROP TABLE IF EXISTS articles;")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
    op.execute("DROP EXTENSION IF EXISTS vector;")
