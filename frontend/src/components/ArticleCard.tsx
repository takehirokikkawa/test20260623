"use client";

import type { Article, Signals } from "@/types/api";
import { SearchSignals } from "./SearchSignals";

const CATEGORY_COLORS: Record<string, string> = {
  "AI/ML": "bg-violet-100 text-violet-700",
  Backend: "bg-blue-100 text-blue-700",
  Frontend: "bg-emerald-100 text-emerald-700",
  DevOps: "bg-amber-100 text-amber-700",
};

interface ArticleCardProps {
  article: Article;
  signals?: Signals;
  score?: number;
  onView: (article: Article) => void;
  onEdit: (article: Article) => void;
  onDelete: (article: Article) => void;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function snippet(content: string, max = 150): string {
  const trimmed = content.replace(/\s+/g, " ").trim();
  if (trimmed.length <= max) return trimmed;
  return trimmed.slice(0, max).trimEnd() + "…";
}

export function ArticleCard({
  article,
  signals,
  score,
  onView,
  onEdit,
  onDelete,
}: ArticleCardProps) {
  const catColor =
    CATEGORY_COLORS[article.category] ?? "bg-slate-100 text-slate-700";

  return (
    <article className="group bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md hover:border-accent-300 transition-all duration-150 flex flex-col">
      {/* Clickable body */}
      <button
        className="flex-1 text-left p-5 focus:outline-none focus:ring-2 focus:ring-accent-500 focus:ring-inset rounded-t-xl"
        onClick={() => onView(article)}
        aria-label={`Read article: ${article.title}`}
      >
        {/* Category + date */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${catColor}`}
          >
            {article.category}
          </span>
          <time
            dateTime={article.published_at}
            className="text-xs text-slate-400 shrink-0"
          >
            {formatDate(article.published_at)}
          </time>
        </div>

        {/* Title */}
        <h2 className="text-base font-semibold text-slate-900 group-hover:text-accent-700 transition-colors leading-snug mb-1 line-clamp-2">
          {article.title}
        </h2>

        {/* Author */}
        <p className="text-xs text-slate-500 mb-2">{article.author}</p>

        {/* Snippet */}
        <p className="text-sm text-slate-600 leading-relaxed line-clamp-3">
          {snippet(article.content)}
        </p>

        {/* Search signals (FR-8) */}
        {signals != null && score != null && (
          <SearchSignals signals={signals} score={score} />
        )}
      </button>

      {/* Action row */}
      <div className="flex items-center justify-end gap-1 px-4 py-2 border-t border-slate-100">
        <button
          onClick={() => onEdit(article)}
          className="text-xs text-slate-500 hover:text-accent-600 font-medium px-2.5 py-1 rounded-lg hover:bg-accent-50 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-400"
          aria-label={`Edit article: ${article.title}`}
        >
          Edit
        </button>
        <button
          onClick={() => onDelete(article)}
          className="text-xs text-slate-500 hover:text-red-600 font-medium px-2.5 py-1 rounded-lg hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
          aria-label={`Delete article: ${article.title}`}
        >
          Delete
        </button>
      </div>
    </article>
  );
}
