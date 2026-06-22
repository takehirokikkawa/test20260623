"use client";

import { useEffect } from "react";
import type { Article } from "@/types/api";

const CATEGORY_COLORS: Record<string, string> = {
  "AI/ML": "bg-violet-100 text-violet-700",
  Backend: "bg-blue-100 text-blue-700",
  Frontend: "bg-emerald-100 text-emerald-700",
  DevOps: "bg-amber-100 text-amber-700",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  } catch {
    return iso;
  }
}

interface ArticleDetailModalProps {
  article: Article;
  onClose: () => void;
  onEdit: (article: Article) => void;
  onDelete: (article: Article) => void;
}

export function ArticleDetailModal({
  article,
  onClose,
  onEdit,
  onDelete,
}: ArticleDetailModalProps) {
  // Keyboard close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const catColor =
    CATEGORY_COLORS[article.category] ?? "bg-slate-100 text-slate-700";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="detail-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-slate-100">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${catColor}`}>
                  {article.category}
                </span>
              </div>
              <h2
                id="detail-title"
                className="text-xl font-bold text-slate-900 leading-snug"
              >
                {article.title}
              </h2>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
                <span>
                  <span className="font-medium text-slate-700">{article.author}</span>
                </span>
                <span className="text-slate-300">·</span>
                <time dateTime={article.published_at}>
                  {formatDate(article.published_at)}
                </time>
              </div>
            </div>
            <button
              onClick={onClose}
              className="shrink-0 text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 rounded-lg p-1"
              aria-label="Close article detail"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body / scrollable content */}
        <div className="px-6 py-5 overflow-y-auto flex-1">
          <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
            {article.content}
          </p>

          {/* Metadata */}
          <dl className="mt-6 pt-5 border-t border-slate-100 grid grid-cols-2 gap-x-6 gap-y-3 text-xs text-slate-500">
            <div>
              <dt className="font-medium text-slate-400 uppercase tracking-wide">ID</dt>
              <dd className="mt-0.5 font-mono text-slate-600 break-all">{article.id}</dd>
            </div>
            {article.legacy_id != null && (
              <div>
                <dt className="font-medium text-slate-400 uppercase tracking-wide">Legacy ID</dt>
                <dd className="mt-0.5 text-slate-600">{article.legacy_id}</dd>
              </div>
            )}
            <div>
              <dt className="font-medium text-slate-400 uppercase tracking-wide">Created</dt>
              <dd className="mt-0.5 text-slate-600">{formatDateTime(article.created_at)}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-400 uppercase tracking-wide">Updated</dt>
              <dd className="mt-0.5 text-slate-600">{formatDateTime(article.updated_at)}</dd>
            </div>
          </dl>
        </div>

        {/* Footer actions */}
        <div className="px-6 py-4 border-t border-slate-100 flex justify-end gap-2">
          <button
            onClick={() => onEdit(article)}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            Edit
          </button>
          <button
            onClick={() => onDelete(article)}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
          >
            Delete
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-accent-600 text-white hover:bg-accent-700 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-500"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
