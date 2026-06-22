"""Lazy-loading singleton for the local SentenceTransformer model.

At module import time nothing is loaded; the model is instantiated on the
first call to ``embed_text`` or ``embed_texts``.  This keeps import cost low
and avoids loading the model during unit tests that do not need it.

Runtime environment sets ``TRANSFORMERS_OFFLINE=1`` / ``HF_HUB_OFFLINE=1``,
so the model is loaded entirely from the local HF cache baked into the image.
"""

from __future__ import annotations

import threading
from typing import List

from app.config import settings

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------
_model = None
_lock = threading.Lock()


def _get_model():
    """Return the SentenceTransformer singleton, loading it on first call."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                # Import here to avoid pulling in torch at module-level for
                # tests that mock this module.
                from sentence_transformers import SentenceTransformer  # noqa: PLC0415

                _model = SentenceTransformer(
                    settings.embedding_model,
                    # Ensure we use whatever device is available (CPU in prod).
                    device=None,
                )
    return _model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_text(text: str) -> List[float]:
    """Encode a single string and return a normalized 384-dim vector.

    Normalizing embeddings makes cosine distance equivalent to dot-product
    distance, which is what the ``<=>`` pgvector operator computes.
    """
    model = _get_model()
    vector = model.encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vector.tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Batch-encode a list of strings.

    Much faster than calling ``embed_text`` in a loop because the model
    can vectorize the forward pass across the batch.
    """
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=64,
    )
    return [v.tolist() for v in vectors]
