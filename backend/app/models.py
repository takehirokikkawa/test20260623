"""SQLAlchemy ORM model for the articles table.

The ``search_tsv`` column is a GENERATED ALWAYS AS ... STORED column managed
entirely by PostgreSQL.  We map it as a read-only server-computed column using
``FetchedValue`` so SQLAlchemy never tries to INSERT/UPDATE it.

The ``embedding`` column uses pgvector's ``Vector(384)`` type.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    FetchedValue,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    legacy_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    # pgvector 384-dim column; nullable so articles can exist before embedding.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384), nullable=True
    )

    # DB-generated tsvector column — read-only from ORM perspective.
    # We use FetchedValue so SQLAlchemy knows the DB populates it.
    search_tsv: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        server_default=FetchedValue(),
        server_onupdate=FetchedValue(),
        deferred=True,  # Don't load by default to save bandwidth.
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
