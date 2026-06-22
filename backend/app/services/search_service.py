"""Hybrid search service: lexical + trigram fuzzy + vector, fused via RRF.

Architecture
------------
1. Three candidate lists are retrieved from PostgreSQL (each up to CANDIDATE_LIMIT rows):
   - **lexical**: tsvector full-text search ordered by ts_rank.
   - **fuzzy**:   pg_trgm trigram similarity on title, ordered by similarity score.
   - **vector**:  pgvector HNSW cosine-distance nearest-neighbour search.

2. The three ranked lists are fused with Reciprocal Rank Fusion (RRF):
       score(d) = Σ_i  weight_i / (k + rank_i)
   where rank_i is the 1-based position of document d in list i.

3. The function ``reciprocal_rank_fusion`` is a PURE function (no DB, no I/O)
   so it can be unit-tested without a running database.

4. The top ``limit`` documents (by fused score, descending) are fetched in
   bulk and returned as ``SearchHit`` objects with full ``signals`` metadata.

Constants
---------
RRF_K          Smoothing constant (higher → less extreme re-ranking). Default 60.
WEIGHT_LEXICAL Weight for the full-text candidate list.
WEIGHT_VECTOR  Weight for the vector candidate list.
WEIGHT_FUZZY   Weight for the trigram candidate list.
CANDIDATE_LIMIT Max candidates retrieved per sub-list.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import embeddings as emb
from app.models import Article
from app.schemas import Article as ArticleSchema
from app.schemas import SearchHit, SearchResponse, Signals

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
RRF_K: int = 60
WEIGHT_LEXICAL: float = 1.0
WEIGHT_VECTOR: float = 1.0
WEIGHT_FUZZY: float = 0.5
CANDIDATE_LIMIT: int = 50
FUZZY_THRESHOLD: float = 0.1


# ---------------------------------------------------------------------------
# Internal data-transfer type for RRF input
# ---------------------------------------------------------------------------

@dataclass
class CandidateEntry:
    """One row from a candidate list, carrying optional signal metadata."""

    article_id: uuid.UUID
    vector_distance: Optional[float] = None
    ts_rank: Optional[float] = None


# ---------------------------------------------------------------------------
# Pure RRF fusion function (unit-testable without DB)
# ---------------------------------------------------------------------------

@dataclass
class FusionResult:
    article_id: uuid.UUID
    score: float = 0.0
    in_lexical: bool = False
    in_fuzzy: bool = False
    in_vector: bool = False
    vector_distance: Optional[float] = None
    ts_rank: Optional[float] = None


def reciprocal_rank_fusion(
    lexical: List[CandidateEntry],
    fuzzy: List[CandidateEntry],
    vector: List[CandidateEntry],
    *,
    k: int = RRF_K,
    weight_lexical: float = WEIGHT_LEXICAL,
    weight_fuzzy: float = WEIGHT_FUZZY,
    weight_vector: float = WEIGHT_VECTOR,
) -> List[FusionResult]:
    """Fuse three ranked candidate lists using Reciprocal Rank Fusion.

    Parameters
    ----------
    lexical, fuzzy, vector:
        Ordered lists of CandidateEntry (rank = 1-based index + 1).
    k, weight_*:
        RRF hyper-parameters.

    Returns
    -------
    List of FusionResult sorted by descending fused score.  The list may
    contain entries that appeared in only one or two of the source lists.
    """
    scores: Dict[uuid.UUID, float] = {}
    meta: Dict[uuid.UUID, FusionResult] = {}

    def _ensure(aid: uuid.UUID) -> FusionResult:
        if aid not in meta:
            meta[aid] = FusionResult(article_id=aid)
        return meta[aid]

    for rank_0, entry in enumerate(lexical):
        aid = entry.article_id
        contrib = weight_lexical / (k + rank_0 + 1)
        scores[aid] = scores.get(aid, 0.0) + contrib
        fr = _ensure(aid)
        fr.in_lexical = True
        if entry.ts_rank is not None:
            fr.ts_rank = entry.ts_rank

    for rank_0, entry in enumerate(fuzzy):
        aid = entry.article_id
        contrib = weight_fuzzy / (k + rank_0 + 1)
        scores[aid] = scores.get(aid, 0.0) + contrib
        fr = _ensure(aid)
        fr.in_fuzzy = True

    for rank_0, entry in enumerate(vector):
        aid = entry.article_id
        contrib = weight_vector / (k + rank_0 + 1)
        scores[aid] = scores.get(aid, 0.0) + contrib
        fr = _ensure(aid)
        fr.in_vector = True
        if entry.vector_distance is not None:
            fr.vector_distance = entry.vector_distance

    results = []
    for aid, score in scores.items():
        fr = meta[aid]
        fr.score = score
        results.append(fr)

    results.sort(key=lambda x: x.score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Search service
# ---------------------------------------------------------------------------

class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        query: str,
        *,
        category: Optional[str] = None,
        author: Optional[str] = None,
        limit: int = 20,
    ) -> SearchResponse:
        """Execute hybrid search and return a SearchResponse."""

        # Build optional filter clauses that are injected into each sub-query.
        filter_clauses = self._build_filter_sql(category=category, author=author)

        # ------------------------------------------------------------------
        # 1. Lexical candidate list (tsvector full-text search)
        # ------------------------------------------------------------------
        lexical_rows = await self._lexical_search(query, filter_clauses)

        # ------------------------------------------------------------------
        # 2. Fuzzy / trigram candidate list
        # ------------------------------------------------------------------
        fuzzy_rows = await self._fuzzy_search(query, filter_clauses)

        # ------------------------------------------------------------------
        # 3. Vector / semantic candidate list
        # ------------------------------------------------------------------
        query_vec = emb.embed_text(query)
        vector_rows = await self._vector_search(query_vec, filter_clauses)

        # ------------------------------------------------------------------
        # 4. RRF fusion (pure function — no DB)
        # ------------------------------------------------------------------
        fused = reciprocal_rank_fusion(
            lexical_rows,
            fuzzy_rows,
            vector_rows,
        )
        top_fused = fused[:limit]

        if not top_fused:
            return SearchResponse(query=query, count=0, results=[])

        # ------------------------------------------------------------------
        # 5. Bulk-fetch article rows for the top results
        # ------------------------------------------------------------------
        top_ids = [fr.article_id for fr in top_fused]
        rows_result = await self._session.execute(
            select(Article).where(Article.id.in_(top_ids))
        )
        articles_by_id: Dict[uuid.UUID, Article] = {
            a.id: a for a in rows_result.scalars().all()
        }

        # ------------------------------------------------------------------
        # 6. Assemble SearchHit list in fused-score order
        # ------------------------------------------------------------------
        hits: List[SearchHit] = []
        for fr in top_fused:
            article = articles_by_id.get(fr.article_id)
            if article is None:
                continue  # Stale reference — skip.

            signals = Signals(
                lexical=fr.in_lexical,
                fuzzy=fr.in_fuzzy,
                semantic=fr.in_vector,
                vector_distance=fr.vector_distance,
                ts_rank=fr.ts_rank,
            )
            hits.append(
                SearchHit(
                    article=ArticleSchema.model_validate(article),
                    score=round(fr.score, 6),
                    signals=signals,
                )
            )

        return SearchResponse(query=query, count=len(hits), results=hits)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filter_sql(
        category: Optional[str], author: Optional[str]
    ) -> Tuple[str, dict]:
        """Return (WHERE clause fragment, bind params dict).

        The returned fragment starts with ``AND`` so it can be appended to
        an existing WHERE clause.
        """
        clauses: List[str] = []
        params: dict = {}

        if category:
            clauses.append("AND category = :filter_category")
            params["filter_category"] = category
        if author:
            clauses.append("AND author = :filter_author")
            params["filter_author"] = author

        return " ".join(clauses), params

    async def _lexical_search(
        self, query: str, filter_sql: Tuple[str, dict]
    ) -> List[CandidateEntry]:
        """Full-text tsvector search ordered by ts_rank."""
        filter_clause, filter_params = filter_sql
        sql = text(
            f"""
            SELECT
                id,
                ts_rank(search_tsv, websearch_to_tsquery('english', :q)) AS rank
            FROM articles
            WHERE search_tsv @@ websearch_to_tsquery('english', :q)
            {filter_clause}
            ORDER BY rank DESC
            LIMIT :limit
            """
        )
        params = {"q": query, "limit": CANDIDATE_LIMIT, **filter_params}
        result = await self._session.execute(sql, params)
        rows = result.fetchall()
        return [
            CandidateEntry(article_id=row[0], ts_rank=float(row[1]))
            for row in rows
        ]

    async def _fuzzy_search(
        self, query: str, filter_sql: Tuple[str, dict]
    ) -> List[CandidateEntry]:
        """pg_trgm trigram similarity on title."""
        filter_clause, filter_params = filter_sql
        sql = text(
            f"""
            SELECT id
            FROM articles
            WHERE similarity(title, :q) > :threshold
            {filter_clause}
            ORDER BY similarity(title, :q) DESC
            LIMIT :limit
            """
        )
        params = {
            "q": query,
            "threshold": FUZZY_THRESHOLD,
            "limit": CANDIDATE_LIMIT,
            **filter_params,
        }
        result = await self._session.execute(sql, params)
        rows = result.fetchall()
        return [CandidateEntry(article_id=row[0]) for row in rows]

    async def _vector_search(
        self, query_vec: List[float], filter_sql: Tuple[str, dict]
    ) -> List[CandidateEntry]:
        """pgvector HNSW cosine-distance nearest-neighbour search."""
        filter_clause, filter_params = filter_sql
        # pgvector registers its own type; we pass the list as a plain Python
        # list and let the driver handle the casting via ::vector.
        sql = text(
            f"""
            SELECT id, (embedding <=> CAST(:qvec AS vector)) AS distance
            FROM articles
            WHERE embedding IS NOT NULL
            {filter_clause}
            ORDER BY distance ASC
            LIMIT :limit
            """
        )
        params = {
            "qvec": str(query_vec),
            "limit": CANDIDATE_LIMIT,
            **filter_params,
        }
        result = await self._session.execute(sql, params)
        rows = result.fetchall()
        return [
            CandidateEntry(article_id=row[0], vector_distance=float(row[1]))
            for row in rows
        ]
