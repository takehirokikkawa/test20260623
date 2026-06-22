"""FastAPI application factory.

Includes:
- CORS middleware (origins from CORS_ORIGINS env var)
- /health router
- /api/articles router
- /api/search router
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import articles, health, search

app = FastAPI(
    title="TechInsight API",
    description=(
        "AI-powered knowledge base with hybrid search "
        "(full-text + trigram + vector, fused via RRF)."
    ),
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(articles.router)
app.include_router(search.router)
