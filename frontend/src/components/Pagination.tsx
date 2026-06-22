"use client";

import { Icon } from "./Icon";

interface PaginationProps {
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}

export function Pagination({ page, totalPages, onPage }: PaginationProps) {
  if (totalPages <= 1) return null;

  const pages: (number | "…")[] = [];

  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push("…");
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
      pages.push(i);
    }
    if (page < totalPages - 2) pages.push("…");
    pages.push(totalPages);
  }

  return (
    <nav
      className="flex items-center justify-center gap-1 mt-8"
      aria-label="Pagination"
    >
      <button
        onClick={() => onPage(page - 1)}
        disabled={page === 1}
        className="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:pointer-events-none transition-colors"
        aria-label="Previous page"
      >
        <Icon name="chevron-left" className="w-4 h-4" aria-hidden />
      </button>

      {pages.map((p, i) =>
        p === "…" ? (
          <span key={`ellipsis-${i}`} className="px-2 py-1.5 text-sm text-slate-400">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPage(p as number)}
            aria-current={p === page ? "page" : undefined}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              p === page
                ? "bg-accent-600 text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onPage(page + 1)}
        disabled={page === totalPages}
        className="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:pointer-events-none transition-colors"
        aria-label="Next page"
      >
        <Icon name="chevron-right" className="w-4 h-4" aria-hidden />
      </button>
    </nav>
  );
}
