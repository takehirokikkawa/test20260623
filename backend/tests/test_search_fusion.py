"""Unit tests for the pure RRF fusion function.

These tests exercise ``reciprocal_rank_fusion`` in isolation — no DB,
no embeddings, no network.  The function is imported directly from the
search_service module.
"""

from __future__ import annotations

import uuid

import pytest

from app.services.search_service import (
    CandidateEntry,
    reciprocal_rank_fusion,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(n: int) -> uuid.UUID:
    """Produce a deterministic UUID from an integer seed for test readability."""
    return uuid.UUID(int=n)


def _entry(n: int, **kw) -> CandidateEntry:
    return CandidateEntry(article_id=_uid(n), **kw)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRecipocalRankFusion:

    def test_empty_lists_return_empty(self):
        result = reciprocal_rank_fusion([], [], [])
        assert result == []

    def test_single_list_lexical(self):
        lex = [_entry(1, ts_rank=0.9), _entry(2, ts_rank=0.5)]
        result = reciprocal_rank_fusion(lex, [], [])
        assert len(result) == 2
        # doc 1 ranked first in lexical → higher fused score
        assert result[0].article_id == _uid(1)
        assert result[1].article_id == _uid(2)

    def test_single_list_vector(self):
        vec = [_entry(10, vector_distance=0.1), _entry(20, vector_distance=0.3)]
        result = reciprocal_rank_fusion([], [], vec)
        assert result[0].article_id == _uid(10)

    def test_union_of_all_lists(self):
        lex = [_entry(1), _entry(2)]
        fuz = [_entry(3)]
        vec = [_entry(4), _entry(1)]
        result = reciprocal_rank_fusion(lex, fuz, vec)
        ids = {fr.article_id for fr in result}
        assert ids == {_uid(1), _uid(2), _uid(3), _uid(4)}

    def test_top_doc_appears_in_all_lists(self):
        """A document that ranks #1 in all three lists should win."""
        lex = [_entry(1), _entry(2), _entry(3)]
        fuz = [_entry(1), _entry(99), _entry(5)]
        vec = [_entry(1), _entry(7), _entry(8)]
        result = reciprocal_rank_fusion(lex, fuz, vec)
        assert result[0].article_id == _uid(1)

    def test_score_formula_single_list(self):
        """Verify the exact RRF score for a one-list scenario."""
        lex = [_entry(1)]
        result = reciprocal_rank_fusion(lex, [], [], k=60, weight_lexical=1.0)
        expected_score = 1.0 / (60 + 1)
        assert abs(result[0].score - expected_score) < 1e-9

    def test_score_accumulates_across_lists(self):
        """Doc appearing rank-1 in both lexical and vector should beat doc in only one."""
        lex = [_entry(1), _entry(2)]
        vec = [_entry(1), _entry(3)]
        result = reciprocal_rank_fusion(lex, [], vec)
        by_id = {fr.article_id: fr for fr in result}

        # doc 1 is rank-1 in both lexical and vector
        # doc 2 is rank-2 in lexical only
        # doc 3 is rank-2 in vector only
        assert by_id[_uid(1)].score > by_id[_uid(2)].score
        assert by_id[_uid(1)].score > by_id[_uid(3)].score

    def test_signals_boolean_flags(self):
        lex = [_entry(1)]
        fuz = [_entry(2)]
        vec = [_entry(3)]
        result = reciprocal_rank_fusion(lex, fuz, vec)
        by_id = {fr.article_id: fr for fr in result}

        assert by_id[_uid(1)].in_lexical is True
        assert by_id[_uid(1)].in_fuzzy is False
        assert by_id[_uid(1)].in_vector is False

        assert by_id[_uid(2)].in_fuzzy is True
        assert by_id[_uid(2)].in_lexical is False

        assert by_id[_uid(3)].in_vector is True
        assert by_id[_uid(3)].in_fuzzy is False

    def test_ts_rank_is_propagated(self):
        lex = [_entry(1, ts_rank=0.75)]
        result = reciprocal_rank_fusion(lex, [], [])
        assert result[0].ts_rank == pytest.approx(0.75)

    def test_vector_distance_is_propagated(self):
        vec = [_entry(42, vector_distance=0.18)]
        result = reciprocal_rank_fusion([], [], vec)
        assert result[0].vector_distance == pytest.approx(0.18)

    def test_fuzzy_weight_lower_than_lexical(self):
        """Fuzzy weight is 0.5, lexical is 1.0; so rank-1 lexical > rank-1 fuzzy."""
        lex = [_entry(1)]
        fuz = [_entry(2)]
        result = reciprocal_rank_fusion(lex, fuz, [])
        by_id = {fr.article_id: fr for fr in result}
        assert by_id[_uid(1)].score > by_id[_uid(2)].score

    def test_descending_score_order(self):
        lex = [_entry(i) for i in range(10)]
        result = reciprocal_rank_fusion(lex, [], [])
        scores = [fr.score for fr in result]
        assert scores == sorted(scores, reverse=True)

    def test_custom_k_parameter(self):
        """Lower k → higher differentiation between ranks."""
        lex = [_entry(1), _entry(2)]
        result_k1 = reciprocal_rank_fusion(lex, [], [], k=1)
        result_k60 = reciprocal_rank_fusion(lex, [], [], k=60)

        # With k=1: scores are 1/(1+1)=0.5 and 1/(1+2)=0.333 → gap = 0.167
        # With k=60: scores are 1/61 and 1/62 → gap ≈ 0.00026
        gap_k1 = result_k1[0].score - result_k1[1].score
        gap_k60 = result_k60[0].score - result_k60[1].score
        assert gap_k1 > gap_k60

    def test_large_lists_still_ordered(self):
        """Stability: 50-item lists, top doc should still sort to front."""
        lex = [_entry(i) for i in range(50)]
        fuz = [_entry(i) for i in reversed(range(50))]
        result = reciprocal_rank_fusion(lex, fuz, [])
        # doc 0 is rank-1 in lexical, rank-50 in fuzzy
        # doc 49 is rank-50 in lexical, rank-1 in fuzzy
        # They should have similar scores — just verify ordering is consistent.
        assert len(result) == 50
        scores = [fr.score for fr in result]
        assert scores == sorted(scores, reverse=True)
