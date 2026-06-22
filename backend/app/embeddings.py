"""Local embedding provider (sentence-transformers).

Design
------
* ``EmbeddingProvider`` is a small Protocol so the rest of the app depends on an
  interface, not a concrete model. Swapping providers (different model, remote
  service, fake for tests) only requires another implementation.
* ``SentenceTransformerProvider`` lazily loads the model on first use (no import
  side-effect; tests that mock embeddings never pull in torch).
* ``document_text()`` is the SINGLE source of truth for what text represents a
  document when embedding. Keeping it here guarantees the bulk ingest, the CSV
  import and the create/update paths all embed identically (review item AI3).
  We embed the article **content**; this matches ``content_hash`` (the embedding
  cache key) and the originally ingested corpus, so the whole dataset is uniform.
* Query embeddings are memoised with an LRU cache (review item AI1) — repeated
  queries skip CPU inference.
* ``a*`` helpers offload the CPU-bound encode to a worker thread so async request
  handlers never block the event loop (review item A1).

Runtime sets ``TRANSFORMERS_OFFLINE=1`` / ``HF_HUB_OFFLINE=1``; the model is loaded
from the cache baked into the image — no network, no API key.
"""

from __future__ import annotations

import asyncio
import threading
from functools import lru_cache
from typing import List, Protocol, Sequence

from app.config import settings

EMBEDDING_DIM = 384
QUERY_CACHE_SIZE = 512


# ---------------------------------------------------------------------------
# Provider abstraction (review item A2)
# ---------------------------------------------------------------------------

class EmbeddingProvider(Protocol):
    """Anything that can turn texts into normalized vectors."""

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        ...


class SentenceTransformerProvider:
    """Lazy, thread-safe sentence-transformers provider."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    # Imported lazily so unit tests that mock embeddings don't
                    # need torch installed.
                    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

                    self._model = SentenceTransformer(self._model_name)
        return self._model

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self._get_model().encode(
            list(texts),
            normalize_embeddings=True,  # makes cosine distance meaningful
            show_progress_bar=False,
            batch_size=64,
        )
        return [v.tolist() for v in vectors]


# Module-level provider instance (the one dependency seam to swap).
_provider: EmbeddingProvider = SentenceTransformerProvider(settings.embedding_model)


def set_provider(provider: EmbeddingProvider) -> None:
    """Swap the active provider (used by tests / alternative backends)."""
    global _provider
    _provider = provider
    _query_vec_cached.cache_clear()


# ---------------------------------------------------------------------------
# What we embed (single source of truth — review item AI3)
# ---------------------------------------------------------------------------

def document_text(content: str) -> str:
    """Return the text used to embed an article. Embeds the content body.

    Centralised so ingest / import / create / update never diverge.
    """
    return content


# ---------------------------------------------------------------------------
# Synchronous API
# ---------------------------------------------------------------------------

def embed_text(text: str) -> List[float]:
    return _provider.encode([text])[0]


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    return _provider.encode(texts)


@lru_cache(maxsize=QUERY_CACHE_SIZE)
def _query_vec_cached(query: str) -> tuple:
    return tuple(_provider.encode([query])[0])


def embed_query(query: str) -> List[float]:
    """Embed a search query, memoised (review item AI1)."""
    return list(_query_vec_cached(query.strip()))


# ---------------------------------------------------------------------------
# Async API — offloads CPU-bound work off the event loop (review item A1)
# ---------------------------------------------------------------------------

async def aembed_text(text: str) -> List[float]:
    return await asyncio.to_thread(embed_text, text)


async def aembed_texts(texts: Sequence[str]) -> List[List[float]]:
    return await asyncio.to_thread(embed_texts, texts)


async def aembed_query(query: str) -> List[float]:
    return await asyncio.to_thread(embed_query, query)
