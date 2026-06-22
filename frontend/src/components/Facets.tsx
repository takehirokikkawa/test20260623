"use client";

import { CATEGORIES } from "@/types/api";
import type { SortOption } from "@/types/api";

interface FacetsProps {
  category: string;
  author: string;
  sort: SortOption;
  isSearchMode: boolean;
  authors: string[];
  onCategory: (c: string) => void;
  onAuthor: (a: string) => void;
  onSort: (s: SortOption) => void;
}

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "-published_at", label: "Newest first" },
  { value: "published_at", label: "Oldest first" },
  { value: "title", label: "Title A–Z" },
  { value: "-title", label: "Title Z–A" },
];

export function Facets({
  category,
  author,
  sort,
  isSearchMode,
  authors,
  onCategory,
  onAuthor,
  onSort,
}: FacetsProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Category filter */}
      <div className="flex items-center gap-1.5">
        <label htmlFor="facet-category" className="text-xs font-medium text-slate-500 whitespace-nowrap">
          Category
        </label>
        <select
          id="facet-category"
          value={category}
          onChange={(e) => onCategory(e.target.value)}
          className="text-sm border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-accent-500"
        >
          <option value="">All</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Author filter — dropdown populated from facets */}
      <div className="flex items-center gap-1.5">
        <label htmlFor="facet-author" className="text-xs font-medium text-slate-500 whitespace-nowrap">
          Author
        </label>
        <select
          id="facet-author"
          value={author}
          onChange={(e) => onAuthor(e.target.value)}
          className="text-sm border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-accent-500"
        >
          <option value="">All authors</option>
          {authors.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>

      {/* Sort (list mode only) */}
      {!isSearchMode && (
        <div className="flex items-center gap-1.5 ml-auto">
          <label htmlFor="facet-sort" className="text-xs font-medium text-slate-500 whitespace-nowrap">
            Sort
          </label>
          <select
            id="facet-sort"
            value={sort}
            onChange={(e) => onSort(e.target.value as SortOption)}
            className="text-sm border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-accent-500"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
