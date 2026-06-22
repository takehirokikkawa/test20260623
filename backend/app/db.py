"""Async database engine and session factory.

Usage
-----
Inject ``get_session`` as a FastAPI dependency::

    async def my_endpoint(session: AsyncSession = Depends(get_session)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ---------------------------------------------------------------------------
# Declarative base shared by all models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Lazy engine / session factory.
#
# Created on first use rather than at import time (review item A4) so that
# importing this module (e.g. in unit tests or tooling) does not open a
# connection pool or require a reachable database.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession; the context manager rolls back on error & closes."""
    async with get_sessionmaker()() as session:
        yield session
