"use client";

interface HeaderProps {
  onNewArticle: () => void;
}

export function Header({ onNewArticle }: HeaderProps) {
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
        <button
          onClick={onNewArticle}
          className="inline-flex items-center gap-1.5 bg-accent-600 hover:bg-accent-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-accent-500 focus:ring-offset-2"
          aria-label="Create new article"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Article
        </button>
      </div>
    </header>
  );
}
