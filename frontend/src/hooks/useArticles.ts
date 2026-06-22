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

  // pagination (list mode only)
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

export function useArticles(): UseArticlesState {
  const [articles, setArticles] = useState<Article[]>([]);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [page, setPageState] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const [query, setQueryState] = useState("");
  const [category, setCategoryState] = useState("");
  const [author, setAuthorState] = useState("");
  const [sort, setSortState] = useState<SortOption>("-published_at");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const isSearchMode = query.trim().length > 0;

  const fetchData = useCallback(async () => {
    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      if (query.trim()) {
        const res = await search({
          q: query.trim(),
          category: category || undefined,
          author: author || undefined,
          limit: 50,
        });
        if (!controller.signal.aborted) {
          setSearchResponse(res);
          setArticles(res.results.map((r) => r.article));
          setTotal(res.count);
          setTotalPages(1);
        }
      } else {
        const res: Page<Article> = await listArticles({
          page,
          size: PAGE_SIZE,
          category: category || undefined,
          author: author || undefined,
          sort,
        });
        if (!controller.signal.aborted) {
          setArticles(res.items);
          setTotal(res.total);
          setTotalPages(res.pages);
          setSearchResponse(null);
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, [query, category, author, sort, page]);

  useEffect(() => {
    fetchData();
    return () => {
      abortRef.current?.abort();
    };
  }, [fetchData]);

  // Reset to page 1 when filters/query change
  const setQuery = useCallback((q: string) => {
    setQueryState(q);
    setPageState(1);
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
