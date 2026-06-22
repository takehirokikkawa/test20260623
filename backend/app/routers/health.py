"""Health-check endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    """Return 200 with DB connectivity status."""
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {"status": "ok", "db": db_status}
