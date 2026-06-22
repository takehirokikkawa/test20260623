"""Application configuration via pydantic-settings.

All settings are read from environment variables (case-insensitive).
Sensible defaults allow the app to start without a .env file for local
development — docker-compose provides the real values at runtime.
"""

from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Async URL used by the FastAPI app (asyncpg).
    database_url: str = (
        "postgresql+asyncpg://techinsight:techinsight@localhost:5432/techinsight"
    )

    # Sync URL used by Alembic (psycopg2).  Defaults to the async URL with
    # driver swapped — docker-compose sets this explicitly.
    alembic_database_url: str = ""

    # sentence-transformers model name.  The model is baked into the Docker
    # image; offline mode prevents any network calls at runtime.
    embedding_model: str = "all-MiniLM-L6-v2"

    # Comma-separated origins allowed for CORS.
    cors_origins: str = "http://localhost:3000"

    # Path to the CSV file mounted by docker-compose.
    csv_path: str = "/data/articles.csv"

    @field_validator("alembic_database_url", mode="before")
    @classmethod
    def default_alembic_url(cls, v: str, info) -> str:
        """If not set, derive from database_url by swapping the driver."""
        if v:
            return v
        # We cannot easily access other fields in a field_validator with
        # mode="before" and no model context; return empty so the property
        # below handles it.
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list (split on comma, strip whitespace)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_alembic_url(self) -> str:
        if self.alembic_database_url:
            return self.alembic_database_url
        return self.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )


# Module-level singleton — imported everywhere.
settings = Settings()
