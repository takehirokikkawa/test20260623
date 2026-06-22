// TechInsight API types — mirrors API_DESIGN.md exactly.

export type Category = "AI/ML" | "Backend" | "Frontend" | "DevOps";

export const CATEGORIES: Category[] = ["AI/ML", "Backend", "Frontend", "DevOps"];

// ── Article ──────────────────────────────────────────────────────────────────

export interface Article {
  id: string;
  legacy_id: number | null;
  title: string;
  content: string;
  author: string;
  category: Category;
  published_at: string; // ISO 8601 UTC
  created_at: string;
  updated_at: string;
}

// ── ArticleCreate / ArticleUpdate ────────────────────────────────────────────

export interface ArticleCreate {
  title: string;           // 1..300
  content: string;         // 1..
  author: string;          // 1..120
  category: Category;
  published_at?: string;   // ISO 8601; omit → server uses now()
}

export interface ArticleUpdate {
  title?: string;
  content?: string;
  author?: string;
  category?: Category;
  published_at?: string;
}

// ── Pagination ────────────────────────────────────────────────────────────────

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ── Search ────────────────────────────────────────────────────────────────────

export interface Signals {
  lexical: boolean;
  fuzzy: boolean;
  semantic: boolean;
  vector_distance?: number;
  ts_rank?: number;
}

export interface SearchHit {
  article: Article;
  score: number;
  signals: Signals;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchHit[];
}

// ── List query params ─────────────────────────────────────────────────────────

export type SortOption =
  | "published_at"
  | "-published_at"
  | "title"
  | "-title";

export interface ListArticlesParams {
  page?: number;
  size?: number;
  category?: string;
  author?: string;
  sort?: SortOption;
}

export interface SearchParams {
  q: string;
  category?: string;
  author?: string;
  limit?: number;
}

// ── Facets ───────────────────────────────────────────────────────────────────

export interface FacetsResponse {
  categories: string[];
  authors: string[];
}

// ── CSV import ──────────────────────────────────────────────────────────────

export interface ImportRowError {
  row: number;
  error: string;
}

export interface ImportResult {
  total_rows: number;
  valid: number;
  invalid: number;
  inserted: number;
  skipped_existing: number;
  unique_embeddings: number;
  errors: ImportRowError[];
}
