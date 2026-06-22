"""Health-check endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    """Liveness + DB readiness.

    Returns 200 only when the database is reachable; otherwise 503 so a load
    balancer / orchestrator can mark the instance unhealthy (review item B6).
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503, content={"status": "error", "db": "error"}
        )
    return {"status": "ok", "db": "ok"}
