"use client";

import { Icon } from "./Icon";

interface HeaderProps {
  onNewArticle: () => void;
  onImport: () => void;
}

export function Header({ onNewArticle, onImport }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold text-accent-600 tracking-tight">
            TechInsight
          </span>
          <span className="hidden sm:inline text-xs text-slate-400 font-medium mt-0.5 ml-1">
            AI Knowledge Base
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Import CSV — sits to the LEFT of "New Article" */}
          <button
            onClick={onImport}
            className="inline-flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 text-sm font-semibold px-4 py-2 rounded-lg border border-slate-300 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-500 focus:ring-offset-2"
            aria-label="Import articles from CSV"
          >
            <Icon name="upload" className="w-4 h-4" aria-hidden />
            <span className="hidden sm:inline">Import CSV</span>
          </button>
          <button
            onClick={onNewArticle}
            className="inline-flex items-center gap-1.5 bg-accent-600 hover:bg-accent-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-accent-500 focus:ring-offset-2"
            aria-label="Create new article"
          >
            <Icon name="plus" className="w-4 h-4" aria-hidden />
            New Article
          </button>
        </div>
      </div>
    </header>
  );
}
