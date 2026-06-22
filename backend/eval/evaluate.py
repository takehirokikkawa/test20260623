"""Search-quality evaluation harness for TechInsight's /api/search endpoint.

Usage
-----
    python backend/eval/evaluate.py [--backend-url http://localhost:8000] [--k 10]

Requires only: httpx (stdlib otherwise). Does NOT need torch or sentence-transformers.

Methodology
-----------
Relevance is determined heuristically (not from human judgement labels):
  A returned article is considered RELEVANT for query Q if EITHER of:
    (a) its title or content (lowercased) contains at least one keyword from
        the query's ``relevant_keywords`` list, OR
    (b) its ``category`` matches the query's ``expected_category`` field.

This "keyword-OR-category" rule is a pragmatic stand-in for human relevance
assessments. It is intentionally lenient to avoid penalising the search engine
for surfacing genuinely related articles that happen to use different vocabulary.
See the README for limitations and how to extend with real judgements.

Metrics computed (per query, then macro-averaged across queries)
----------------------------------------------------------------
Precision@k  – fraction of the top-k results that are relevant.
               P@k = (# relevant in top k) / k

Recall@k     – fraction of the *known relevant* corpus that appears in top k.
               Because we lack the full corpus relevance count, we approximate
               "total relevant" as the number of distinct articles the API
               returned across ALL queries for this keyword set (lower bound).
               A simpler and honest formulation: Recall@k is reported as
               "hits / total_relevant_in_response", where total_relevant_in_response
               = total relevant articles among the limit results returned.
               This is a within-response recall, not a corpus recall.

MRR          – Mean Reciprocal Rank.
               MRR = 1 / rank_of_first_relevant_result  (0 if none found in top k)

nDCG@k       – Normalised Discounted Cumulative Gain.
               Gain is binary (1 = relevant, 0 = not relevant).
               DCG@k  = Σ_{i=1}^{k}  rel_i / log2(i + 1)
               iDCG@k = Σ_{i=1}^{r}  1 / log2(i + 1)  where r = min(relevant_count, k)
               nDCG@k = DCG@k / iDCG@k  (1 if none relevant → defined as 0)

Exit codes
----------
0  – evaluation completed (regardless of score levels — this is a measurement tool).
1  – connection error (backend unreachable).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

QUERIES_PATH = Path(__file__).parent / "queries.json"


# ---------------------------------------------------------------------------
# Relevance judgement
# ---------------------------------------------------------------------------

def is_relevant(article: dict[str, Any], keywords: list[str], expected_category: str) -> bool:
    """Return True if the article is considered relevant for a query.

    Rule (keyword-OR-category):
      - If the article's category matches expected_category, it is relevant.
      - Otherwise, if any keyword appears (case-insensitive) in the concatenation
        of title + content, it is relevant.
    """
    if article.get("category", "") == expected_category:
        return True

    haystack = (
        (article.get("title") or "") + " " + (article.get("content") or "")
    ).lower()

    return any(kw.lower() in haystack for kw in keywords)


# ---------------------------------------------------------------------------
# Metric calculations
# ---------------------------------------------------------------------------

def precision_at_k(relevance_flags: list[bool], k: int) -> float:
    """Fraction of top-k results that are relevant."""
    top_k = relevance_flags[:k]
    if not top_k:
        return 0.0
    return sum(top_k) / len(top_k)


def recall_at_k(relevance_flags: list[bool], k: int) -> float:
    """Within-response recall: relevant-in-top-k / total-relevant-in-response.

    NOTE: This is NOT corpus recall (we do not know how many relevant articles
    exist in the database). It measures how much of the relevant signal surfaced
    in the response is captured in the top-k positions.
    """
    total_relevant = sum(relevance_flags)
    if total_relevant == 0:
        return 0.0
    hits_in_top_k = sum(relevance_flags[:k])
    return hits_in_top_k / total_relevant


def mrr(relevance_flags: list[bool], k: int) -> float:
    """Reciprocal rank of the first relevant result in top-k (0 if none)."""
    for i, rel in enumerate(relevance_flags[:k]):
        if rel:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(relevance_flags: list[bool], k: int) -> float:
    """Binary nDCG@k.

    DCG@k  = Σ rel_i / log2(i+2)   (i is 0-indexed, so rank = i+1, divisor = log2(rank+1))
    iDCG@k = Σ_{i=0}^{min(R,k)-1} 1 / log2(i+2)   where R = total relevant articles
    nDCG@k = DCG@k / iDCG@k        (0.0 when iDCG == 0, i.e. no relevant articles)
    """
    top_k = relevance_flags[:k]
    dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(top_k))

    total_relevant = sum(relevance_flags)
    ideal_count = min(total_relevant, k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_count))

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def fetch_search_results(
    client: httpx.Client,
    backend_url: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Call GET /api/search and return the list of article dicts.

    Returns an empty list on non-200 responses (logged to stderr).
    Raises httpx.ConnectError / httpx.ConnectTimeout for connection failures.
    """
    resp = client.get(
        f"{backend_url.rstrip('/')}/api/search",
        params={"q": query, "limit": limit},
        timeout=15.0,
    )
    if resp.status_code != 200:
        print(
            f"  [WARN] HTTP {resp.status_code} for query '{query}' — skipping.",
            file=sys.stderr,
        )
        return []
    data = resp.json()
    # data shape: { "query": ..., "count": ..., "results": [{"article": {...}, "score": ..., "signals": ...}] }
    return [hit["article"] for hit in data.get("results", [])]


# ---------------------------------------------------------------------------
# Evaluation loop
# ---------------------------------------------------------------------------

def evaluate(backend_url: str, k: int) -> None:
    queries = json.loads(QUERIES_PATH.read_text())

    all_precision: list[float] = []
    all_recall: list[float] = []
    all_mrr: list[float] = []
    all_ndcg: list[float] = []

    print(f"\nTechInsight Search Evaluation  (backend={backend_url}, k={k})")
    print("=" * 72)

    try:
        with httpx.Client() as client:
            for entry in queries:
                query: str = entry["query"]
                keywords: list[str] = entry["relevant_keywords"]
                expected_category: str = entry["expected_category"]

                # Fetch results
                articles = fetch_search_results(client, backend_url, query, limit=k)
                if not articles:
                    # No results or connection problem already handled above
                    relevance_flags = []
                else:
                    relevance_flags = [
                        is_relevant(a, keywords, expected_category) for a in articles
                    ]

                p = precision_at_k(relevance_flags, k)
                r = recall_at_k(relevance_flags, k)
                m = mrr(relevance_flags, k)
                n = ndcg_at_k(relevance_flags, k)

                all_precision.append(p)
                all_recall.append(r)
                all_mrr.append(m)
                all_ndcg.append(n)

                relevant_count = sum(relevance_flags)
                returned_count = len(articles)

                print(f"\nQuery : {query!r}")
                print(f"  Category expected : {expected_category}")
                print(f"  Results returned  : {returned_count}  |  Relevant in response: {relevant_count}")
                print(
                    f"  P@{k}={p:.3f}  R@{k}={r:.3f}  MRR={m:.3f}  nDCG@{k}={n:.3f}"
                )

    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        print(f"\n[ERROR] Cannot reach backend at {backend_url}: {exc}", file=sys.stderr)
        print("Ensure the stack is running: docker compose up", file=sys.stderr)
        sys.exit(1)

    # Macro-average
    n_queries = len(queries)
    if n_queries == 0:
        print("\nNo queries found in queries.json.")
        return

    macro_p = sum(all_precision) / n_queries
    macro_r = sum(all_recall) / n_queries
    macro_mrr = sum(all_mrr) / n_queries
    macro_ndcg = sum(all_ndcg) / n_queries

    print("\n" + "=" * 72)
    print("Macro-averaged results across all queries")
    print("-" * 72)
    print(f"  Precision@{k}  : {macro_p:.4f}")
    print(f"  Recall@{k}    : {macro_r:.4f}  (within-response; see README for caveat)")
    print(f"  MRR          : {macro_mrr:.4f}")
    print(f"  nDCG@{k}      : {macro_ndcg:.4f}")
    print("=" * 72)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate TechInsight search quality against a running backend."
    )
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Base URL of the backend API (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Cutoff rank k for Precision@k, Recall@k, nDCG@k (default: 10).",
    )
    args = parser.parse_args()
    evaluate(backend_url=args.backend_url, k=args.k)


if __name__ == "__main__":
    main()
