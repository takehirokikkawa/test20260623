"""Generate a sample articles.csv faithful to the analyzed dataset.

The provided dataset (per docs/REQUIREMENTS.md §2) has:
  - 1,000 rows, 6 columns: id, title, content, author, category, published_at
  - English content, mean length ~312 chars (low variance)
  - 449 UNIQUE contents (duplicates, up to ~8x)
  - 4 categories (~even), 8 authors (~even)
  - published_at between 2023-01 and 2025-09, no timezone

This script reproduces those characteristics deterministically (fixed seed) so the
app is fully runnable. Replace data/articles.csv with the real file to use real data;
the ingest pipeline is schema-compatible and idempotent.

Usage:  python data/generate_sample_csv.py
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20260622
N_ROWS = 1000
N_UNIQUE = 449
OUT = Path(__file__).resolve().parent / "articles.csv"

CATEGORIES = ["AI/ML", "Backend", "Frontend", "DevOps"]
AUTHORS = [
    "Alice Tanaka", "Bob Suzuki", "Carol Yamamoto", "David Kim",
    "Erin Nakamura", "Frank Watanabe", "Grace Ito", "Henry Sato",
]

# Topic vocabulary per category — used to compose titles and ~312-char bodies.
TOPICS = {
    "AI/ML": [
        ("vector embeddings", "semantic search", "transformer models", "fine-tuning",
         "retrieval augmented generation", "model inference", "tokenization", "cosine similarity"),
        "Modern machine learning systems increasingly rely on {a} to power {b}. By representing text as "
        "dense {c}, engineers can compare meaning rather than exact words. This article walks through how {d} "
        "improves relevance, the trade-offs in latency and recall, and practical tips for deploying these models "
        "in production without sacrificing throughput or accuracy at scale.",
    ],
    "Backend": [
        ("REST APIs", "database indexing", "connection pooling", "caching layers",
         "asynchronous I/O", "message queues", "rate limiting", "query optimization"),
        "Building reliable backend services means thinking carefully about {a} and {b}. We examine how {c} "
        "reduces tail latency, when to introduce {d}, and how to keep the system observable. The post covers "
        "schema design, transaction boundaries, and idempotency so that your services stay correct and fast even "
        "as traffic grows from hundreds to millions of requests per day.",
    ],
    "Frontend": [
        ("React hooks", "server components", "state management", "accessibility",
         "responsive layouts", "client-side caching", "optimistic updates", "code splitting"),
        "A great frontend balances {a} with {b}. This guide explores how {c} keeps interfaces snappy, why {d} "
        "matters for perceived performance, and how to structure components for reuse across a growing team. We "
        "share patterns for loading states, error boundaries, and incremental adoption so the user experience "
        "stays smooth on slow networks and small screens alike.",
    ],
    "DevOps": [
        ("container orchestration", "CI/CD pipelines", "infrastructure as code", "observability",
         "blue-green deployments", "secret management", "autoscaling", "health checks"),
        "Operating software at scale depends on {a} and {b}. Here we cover how {c} shortens feedback loops, the "
        "role of {d} in safe releases, and strategies for zero-downtime rollouts. Expect concrete advice on "
        "monitoring, alerting, and reproducible environments so that any engineer can recover the system quickly "
        "when something inevitably breaks in production.",
    ],
}

TITLE_TEMPLATES = [
    "A Practical Guide to {x}",
    "Understanding {x} in Production",
    "Scaling {x} Without the Pain",
    "{x}: Patterns and Pitfalls",
    "Deep Dive into {x}",
    "How We Improved {x}",
    "Lessons Learned from {x}",
    "Getting Started with {x}",
]


def title_case(term: str) -> str:
    return term[:1].upper() + term[1:]


def build_unique_articles(rng: random.Random):
    articles = []
    for i in range(N_UNIQUE):
        category = CATEGORIES[i % len(CATEGORIES)]
        terms, body_tmpl = TOPICS[category]
        a, b, c, d = rng.sample(terms, 4)
        content = body_tmpl.format(a=a, b=b, c=c, d=d)
        title = rng.choice(TITLE_TEMPLATES).format(x=title_case(a))
        articles.append({"title": title, "content": content, "category": category})
    return articles


def main() -> None:
    rng = random.Random(SEED)
    unique = build_unique_articles(rng)

    # Assign duplicates: every unique body appears once, the remaining rows reuse
    # bodies with a long-tail distribution (some appear up to ~8 times).
    assignment = list(range(N_UNIQUE))
    weights = [rng.random() ** 2 for _ in range(N_UNIQUE)]  # skew toward a few popular ones
    while len(assignment) < N_ROWS:
        assignment.append(rng.choices(range(N_UNIQUE), weights=weights, k=1)[0])
    rng.shuffle(assignment)

    start = datetime(2023, 1, 1)
    span_days = (datetime(2025, 9, 30) - start).days

    rows = []
    for row_id, uidx in enumerate(assignment, start=1):
        art = unique[uidx]
        published = start + timedelta(
            days=rng.randint(0, span_days),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )
        rows.append({
            "id": row_id,
            "title": art["title"],
            "content": art["content"],
            "author": rng.choice(AUTHORS),
            "category": art["category"],
            "published_at": published.strftime("%Y-%m-%d %H:%M:%S"),
        })

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "title", "content", "author", "category", "published_at"]
        )
        writer.writeheader()
        writer.writerows(rows)

    lengths = [len(r["content"]) for r in rows]
    print(f"Wrote {len(rows)} rows -> {OUT}")
    print(f"unique contents: {len({r['content'] for r in rows})}")
    print(f"content length: mean={sum(lengths)/len(lengths):.0f} min={min(lengths)} max={max(lengths)}")


if __name__ == "__main__":
    main()
