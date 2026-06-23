"""SQLAlchemy ORM models.

``category`` and ``author`` are normalised into master tables (``categories`` /
``authors``) referenced by FK (review item: normalisation). To keep the API
response shape unchanged, ``Article`` exposes ``.category`` / ``.author`` as
read-only string properties backed by eager-loaded relationships.

The ``search_tsv`` column is a GENERATED ALWAYS AS ... STORED column managed
entirely by PostgreSQL. The ``embedding`` column uses pgvector's ``Vector(384)``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    FetchedValue,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


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

    category_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("categories.id"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("authors.id"), nullable=False
    )

    # Eager-loaded in all read queries so the string properties below never
    # trigger lazy IO under async (which would raise MissingGreenlet).
    category_ref: Mapped[Category] = relationship(lazy="joined")
    author_ref: Mapped[Author] = relationship(lazy="joined")

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

    # Soft delete: NULL = live, non-NULL = deleted at that time. Physical rows
    # are retained for recovery/audit (review item: logical delete).
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    # updated_at is maintained by a DB trigger (set_updated_at). We deliberately
    # do NOT set ORM onupdate to avoid double-writing the column (review item B4).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Read-only string accessors that preserve the original API shape.
    # Backed by the joined relationships above (no extra IO).
    @property
    def category(self) -> str:
        return self.category_ref.name

    @property
    def author(self) -> str:
        return self.author_ref.name
