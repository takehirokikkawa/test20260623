"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { listArticles, search } from "@/lib/api";
import type {
  Article,
  Page,
  SearchResponse,
  SortOption,
} from "@/types/api";

export interface UseArticlesState {
  // data
  articles: Article[];
  searchResponse: SearchResponse | null;
  isSearchMode: boolean;

  // pagination
  page: number;
  totalPages: number;
  total: number;

  // filters
  query: string;
  category: string;
  author: string;
  sort: SortOption;

  // status
  loading: boolean;
  error: string | null;

  // actions
  setQuery: (q: string) => void;
  setCategory: (c: string) => void;
  setAuthor: (a: string) => void;
  setSort: (s: SortOption) => void;
  setPage: (p: number) => void;
  refresh: () => void;

  // optimistic helpers
  optimisticAdd: (article: Article) => void;
  optimisticUpdate: (article: Article) => void;
  optimisticRemove: (id: string) => void;
}

const PAGE_SIZE = 20;
const SEARCH_PAGE_SIZE = 12;
const DEBOUNCE_MS = 300;

export function useArticles(): UseArticlesState {
  const [articles, setArticles] = useState<Article[]>([]);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  // All search hits (up to 50); client-side paged
  const [allSearchHits, setAllSearchHits] = useState<SearchResponse["results"]>([]);
  const [page, setPageState] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const [query, setQueryState] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [category, setCategoryState] = useState("");
  const [author, setAuthorState] = useState("");
  const [sort, setSortState] = useState<SortOption>("-published_at");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isSearchMode = debouncedQuery.trim().length > 0;

  // ── Debounce query ────────────────────────────────────────────────────────

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(query);
      setPageState(1);
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  // ── Fetch ─────────────────────────────────────────────────────────────────

  const fetchData = useCallback(async () => {
    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const { signal } = controller;

    setLoading(true);
    setError(null);

    try {
      if (debouncedQuery.trim()) {
        const res = await search(
          {
            q: debouncedQuery.trim(),
            category: category || undefined,
            author: author || undefined,
            limit: 50,
          },
          signal
        );
        if (!signal.aborted) {
          setSearchResponse(res);
          setAllSearchHits(res.results);
          setTotal(res.count);
          // totalPages driven by client-side slicing (updated in pagination effect below)
        }
      } else {
        const res: Page<Article> = await listArticles(
          {
            page,
            size: PAGE_SIZE,
            category: category || undefined,
            author: author || undefined,
            sort,
          },
          signal
        );
        if (!signal.aborted) {
          setArticles(res.items);
          setTotal(res.total);
          setTotalPages(res.pages);
          setSearchResponse(null);
          setAllSearchHits([]);
        }
      }
    } catch (err) {
      if (signal.aborted) return; // Ignore AbortError
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      if (!signal.aborted) {
        setLoading(false);
      }
    }
  }, [debouncedQuery, category, author, sort, page]);

  useEffect(() => {
    fetchData();
    return () => {
      abortRef.current?.abort();
    };
  }, [fetchData]);

  // ── Client-side search pagination ─────────────────────────────────────────

  useEffect(() => {
    if (!isSearchMode) return;
    const pages = Math.max(1, Math.ceil(allSearchHits.length / SEARCH_PAGE_SIZE));
    setTotalPages(pages);
    const start = (page - 1) * SEARCH_PAGE_SIZE;
    const slice = allSearchHits.slice(start, start + SEARCH_PAGE_SIZE);
    setArticles(slice.map((r) => r.article));
    // Keep searchResponse in sync so ArticleCard can look up signals by id
    setSearchResponse((prev) =>
      prev
        ? { ...prev, results: allSearchHits, count: allSearchHits.length }
        : null
    );
  }, [isSearchMode, allSearchHits, page]);

  // ── Setters ───────────────────────────────────────────────────────────────

  // Reset to page 1 when filters/query change
  const setQuery = useCallback((q: string) => {
    setQueryState(q);
    // page reset happens in the debounce effect
  }, []);

  const setCategory = useCallback((c: string) => {
    setCategoryState(c);
    setPageState(1);
  }, []);

  const setAuthor = useCallback((a: string) => {
    setAuthorState(a);
    setPageState(1);
  }, []);

  const setSort = useCallback((s: SortOption) => {
    setSortState(s);
    setPageState(1);
  }, []);

  const setPage = useCallback((p: number) => {
    setPageState(p);
  }, []);

  const refresh = useCallback(() => {
    fetchData();
  }, [fetchData]);

  // Optimistic UI helpers
  const optimisticAdd = useCallback((article: Article) => {
    setArticles((prev) => [article, ...prev]);
    setTotal((t) => t + 1);
  }, []);

  const optimisticUpdate = useCallback((article: Article) => {
    setArticles((prev) =>
      prev.map((a) => (a.id === article.id ? article : a))
    );
  }, []);

  const optimisticRemove = useCallback((id: string) => {
    setArticles((prev) => prev.filter((a) => a.id !== id));
    setTotal((t) => Math.max(0, t - 1));
  }, []);

  return {
    articles,
    searchResponse,
    isSearchMode,
    page,
    totalPages,
    total,
    query,
    category,
    author,
    sort,
    loading,
    error,
    setQuery,
    setCategory,
    setAuthor,
    setSort,
    setPage,
    refresh,
    optimisticAdd,
    optimisticUpdate,
    optimisticRemove,
  };
}
