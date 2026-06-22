# Search-Quality Evaluation Harness

A lightweight, DB-free evaluation script that measures the retrieval quality of
TechInsight's `/api/search` endpoint against a set of labeled queries.

---

## Quick Start

```bash
# 1. Start the full stack (db + backend with embeddings, etc.)
docker compose up

# 2. Run the evaluation (from the repository root)
python backend/eval/evaluate.py

# Optional flags
python backend/eval/evaluate.py --backend-url http://localhost:8000 --k 10
```

Dependencies: only `httpx` (already in `backend/requirements.txt`). No torch, no DB.

---

## How It Works

### Query set (`queries.json`)

Ten labeled queries, each carrying:

| Field | Purpose |
|---|---|
| `query` | The natural-language search string sent to the API |
| `relevant_keywords` | Keywords that should appear in a relevant article's title or content |
| `expected_category` | The article category that indicates relevance (AI/ML, Backend, Frontend, DevOps) |

### Relevance judgement rule

An article returned by the API is counted as **relevant** for a query if **either** condition holds:

1. Its `category` matches `expected_category`, **OR**
2. Its `title + content` (lowercased) contains at least one string from `relevant_keywords`.

This "keyword-OR-category" rule is deliberately lenient: it rewards the search engine for
surfacing thematically related content even when exact keyword overlap is low. The rule is
applied independently to each returned result.

### Metrics

All metrics use a cutoff of **k** (default 10, configurable with `--k`).

| Metric | Formula | Interpretation |
|---|---|---|
| **Precision@k** | `(# relevant in top k) / k` | What fraction of the returned results are useful? |
| **Recall@k** | `(# relevant in top k) / (# relevant in full response)` | How much of the relevant signal is in the top-k? (within-response; see caveat below) |
| **MRR** | `1 / rank_of_first_relevant_result` (0 if none in top k) | How quickly does the first useful result appear? |
| **nDCG@k** | `DCG@k / iDCG@k` (binary gains, log-discount) | Rank-aware quality; rewards putting relevant results higher |

Results are printed per query and then **macro-averaged** across all queries.

---

## Known Limitations

### 1. Heuristic (not human-judged) relevance

The keyword + category rule is an approximation. A relevant article that uses
synonyms not in the keyword list will be counted as *not relevant*, artificially
lowering scores. An irrelevant article that happens to mention a keyword will be
counted as *relevant*, artificially raising scores.

**How to extend**: Replace the `is_relevant()` function in `evaluate.py` with a
lookup into a manually curated relevance table:

```python
# Example: { (query_id, article_id): 0 | 1 | 2 }  (graded 0-2)
HUMAN_LABELS: dict[tuple[str, str], int] = { ... }
```

Human labellers should assess the top-20 results for each query and assign a
binary or graded relevance score. This is the standard TREC/BEIR methodology.

### 2. Recall is within-response, not corpus recall

True Recall requires knowing how many relevant articles exist in the *full database*.
This script only knows what the API returned. The reported Recall@k therefore measures
"what fraction of the relevant articles in the response appear in the top k" — useful
as a rank-quality signal but not a true recall estimate.

**How to extend**: Run the evaluation at `limit=1000` once to collect all results,
use those as the relevance denominator, then re-evaluate at `limit=10`.

---

## Using the Harness to Tune RRF Weights

The RRF search has four tuning constants in `backend/app/services/search_service.py`:

```python
RRF_K          = 60    # Rank-smoothing constant. Lower → more aggressive re-ranking.
WEIGHT_LEXICAL = 1.0   # Weight for full-text (tsvector) candidates.
WEIGHT_VECTOR  = 1.0   # Weight for vector (pgvector HNSW) candidates.
WEIGHT_FUZZY   = 0.5   # Weight for trigram (pg_trgm) candidates.
```

**Tuning workflow:**

1. Establish a baseline by running `evaluate.py` with the current defaults. Record
   macro nDCG@10 and MRR.
2. Change one constant at a time (e.g. increase `WEIGHT_LEXICAL` to 1.5 for datasets
   where keyword precision matters more than semantic recall).
3. Restart the backend (`docker compose restart backend`) and re-run `evaluate.py`.
4. Accept the change if macro nDCG@10 and MRR both improve (or one improves without
   degrading the other).
5. Once human labels are available, use a held-out validation set to avoid overfitting
   the weights to the query set used during development.

For a more principled approach, grid-search or Bayesian optimisation over
`(WEIGHT_LEXICAL, WEIGHT_VECTOR, WEIGHT_FUZZY, RRF_K)` using the eval harness as the
objective function, maximising macro nDCG@10.
