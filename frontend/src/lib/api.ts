// Typed fetch client for the TechInsight API.
// Reads NEXT_PUBLIC_API_BASE_URL at runtime (client-side only — no server-side fetch).

import type {
  Article,
  ArticleCreate,
  ArticleUpdate,
  ListArticlesParams,
  Page,
  SearchParams,
  SearchResponse,
} from "@/types/api";

function getBase(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
  );
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = `${getBase()}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (res.status === 204) {
    return undefined as unknown as T;
  }

  const data = await res.json();

  if (!res.ok) {
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : JSON.stringify(data?.detail ?? data);
    throw new Error(message);
  }

  return data as T;
}

// ── Articles ──────────────────────────────────────────────────────────────────

export async function listArticles(
  params: ListArticlesParams = {}
): Promise<Page<Article>> {
  const qs = new URLSearchParams();
  if (params.page != null) qs.set("page", String(params.page));
  if (params.size != null) qs.set("size", String(params.size));
  if (params.category) qs.set("category", params.category);
  if (params.author) qs.set("author", params.author);
  if (params.sort) qs.set("sort", params.sort);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<Page<Article>>(`/api/articles${query}`);
}

export async function getArticle(id: string): Promise<Article> {
  return apiFetch<Article>(`/api/articles/${encodeURIComponent(id)}`);
}

export async function createArticle(body: ArticleCreate): Promise<Article> {
  return apiFetch<Article>("/api/articles", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateArticle(
  id: string,
  body: ArticleUpdate
): Promise<Article> {
  return apiFetch<Article>(`/api/articles/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteArticle(id: string): Promise<void> {
  return apiFetch<void>(`/api/articles/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

// ── Search ────────────────────────────────────────────────────────────────────

export async function search(params: SearchParams): Promise<SearchResponse> {
  const qs = new URLSearchParams({ q: params.q });
  if (params.category) qs.set("category", params.category);
  if (params.author) qs.set("author", params.author);
  if (params.limit != null) qs.set("limit", String(params.limit));
  return apiFetch<SearchResponse>(`/api/search?${qs.toString()}`);
}
