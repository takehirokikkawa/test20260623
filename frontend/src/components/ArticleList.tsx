"use client";

import type { Article, SearchResponse } from "@/types/api";
import { ArticleCard } from "./ArticleCard";

// Skeleton card
function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="h-5 w-16 bg-slate-200 rounded-full" />
        <div className="h-4 w-20 bg-slate-100 rounded" />
      </div>
      <div className="h-5 bg-slate-200 rounded mb-1.5 w-4/5" />
      <div className="h-4 bg-slate-100 rounded mb-3 w-1/4" />
      <div className="space-y-1.5">
        <div className="h-3.5 bg-slate-100 rounded w-full" />
        <div className="h-3.5 bg-slate-100 rounded w-5/6" />
        <div className="h-3.5 bg-slate-100 rounded w-3/4" />
      </div>
    </div>
  );
}

interface ArticleListProps {
  articles: Article[];
  searchResponse: SearchResponse | null;
  isSearchMode: boolean;
  loading: boolean;
  error: string | null;
  total: number;
  onView: (article: Article) => void;
  onEdit: (article: Article) => void;
  onDelete: (article: Article) => void;
}

export function ArticleList({
  articles,
  searchResponse,
  isSearchMode,
  loading,
  error,
  total,
  onView,
  onEdit,
  onDelete,
}: ArticleListProps) {
  // Build a lookup from article id -> search hit (for signals/score)
  const hitMap = new Map(
    searchResponse?.results.map((r) => [r.article.id, r]) ?? []
  );

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center gap-3">
        <svg
          className="w-12 h-12 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
          />
        </svg>
        <p className="text-slate-700 font-medium">Something went wrong</p>
        <p className="text-sm text-slate-500 max-w-md">{error}</p>
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center gap-3">
        <svg
          className="w-12 h-12 text-slate-300"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
          />
        </svg>
        <p className="text-slate-700 font-medium">
          {isSearchMode ? "No results found" : "No articles yet"}
        </p>
        <p className="text-sm text-slate-500 max-w-xs">
          {isSearchMode
            ? "Try different keywords or remove some filters."
            : "Create your first article to get started."}
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Result count */}
      <p className="text-sm text-slate-500 mb-3">
        {isSearchMode ? (
          <>
            <span className="font-medium text-slate-700">{total}</span> result
            {total !== 1 ? "s" : ""} for hybrid search
          </>
        ) : (
          <>
            <span className="font-medium text-slate-700">{total}</span> article
            {total !== 1 ? "s" : ""}
          </>
        )}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {articles.map((article) => {
          const hit = hitMap.get(article.id);
          return (
            <ArticleCard
              key={article.id}
              article={article}
              signals={hit?.signals}
              score={hit?.score}
              onView={onView}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          );
        })}
      </div>
    </>
  );
}
