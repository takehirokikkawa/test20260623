"""Async database engine and session factory.

Usage
-----
Inject ``get_session`` as a FastAPI dependency::

    async def my_endpoint(session: AsyncSession = Depends(get_session)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Declarative base shared by all models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession and ensure it is closed afterwards."""
    async with AsyncSessionLocal() as session:
        yield session
