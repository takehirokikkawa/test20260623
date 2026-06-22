"""End-to-end API tests against a running stack.

Run after `docker compose up`. Skips automatically if the backend is not
reachable (so unit-test runs and CI lint stages are unaffected).

    BACKEND_URL=http://localhost:8000 pytest tests/test_api_e2e.py
"""

import os
import uuid

import pytest

httpx = pytest.importorskip("httpx")

BASE = os.environ.get("BACKEND_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def client():
    try:
        probe = httpx.Client(base_url=BASE, timeout=5)
        probe.get("/health")
    except Exception:
        pytest.skip(f"backend not reachable at {BASE}")
    with httpx.Client(base_url=BASE, timeout=60) as c:
        yield c


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["db"] == "ok"


def test_facets(client):
    r = client.get("/api/articles/facets")
    assert r.status_code == 200
    data = r.json()
    assert set(data["categories"]) == {"AI/ML", "Backend", "Frontend", "DevOps"}
    assert len(data["authors"]) > 0


def test_list_paginated(client):
    r = client.get("/api/articles", params={"size": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    assert len(data["items"]) <= 5


def test_crud_softdelete_and_search(client):
    token = f"zzqquantumwidget{uuid.uuid4().hex[:8]}"
    body = {
        "title": f"Test {token}",
        "content": f"A unique article body discussing {token} orchestration patterns",
        "author": "E2E Bot",
        "category": "Backend",
    }
    r = client.post("/api/articles", json=body)
    assert r.status_code == 201
    aid = r.json()["id"]

    # Vector + lexical search must surface the new article (validates B1 binding).
    r = client.get("/api/search", params={"q": token, "limit": 5})
    assert r.status_code == 200
    assert any(h["article"]["id"] == aid for h in r.json()["results"])

    # Update
    r = client.put(f"/api/articles/{aid}", json={"title": f"Edited {token}"})
    assert r.status_code == 200
    assert r.json()["title"].startswith("Edited")

    # Soft delete
    assert client.delete(f"/api/articles/{aid}").status_code == 204
    # Hidden from detail and from search
    assert client.get(f"/api/articles/{aid}").status_code == 404
    r = client.get("/api/search", params={"q": token, "limit": 5})
    assert all(h["article"]["id"] != aid for h in r.json()["results"])


def test_search_category_filter(client):
    r = client.get("/api/search", params={"q": "database", "category": "AI/ML", "limit": 5})
    assert r.status_code == 200
    assert all(h["article"]["category"] == "AI/ML" for h in r.json()["results"])


def test_fuzzy_search_runs(client):
    # Exercises the pg_trgm `%` operator path (B5) — should not error.
    r = client.get("/api/search", params={"q": "databse optimiztion", "limit": 5})
    assert r.status_code == 200


def test_import_endpoint(client):
    csv = (
        b"id,title,content,author,category,published_at\n"
        b",Imported E2E Row,Body about kubernetes operators and autoscaling,Imp Bot,DevOps,2024-01-01 00:00:00\n"
    )
    files = {"file": ("t.csv", csv, "text/csv")}
    r = client.post("/api/articles/import", files=files)
    assert r.status_code == 200
    assert r.json()["inserted"] == 1
