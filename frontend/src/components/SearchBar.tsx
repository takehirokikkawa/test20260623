"use client";

import { useRef } from "react";
import { Icon } from "./Icon";

interface SearchBarProps {
  value: string;
  onChange: (q: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleClear = () => {
    onChange("");
    inputRef.current?.focus();
  };

  const isActive = value.trim().length > 0;

  return (
    <div className="w-full">
      <div className="relative">
        {/* Search icon */}
        <span className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-slate-400">
          <Icon name="search" className="w-5 h-5" strokeWidth={1.8} aria-hidden />
        </span>

        <input
          ref={inputRef}
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search articles by topic, concept, or technology…"
          aria-label="Search articles"
          className="w-full pl-10 pr-24 py-3 rounded-xl border border-slate-300 bg-white shadow-sm text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-accent-500 transition-colors"
        />

        <div className="absolute inset-y-0 right-3 flex items-center gap-2">
          {isActive && (
            <button
              onClick={handleClear}
              className="text-slate-400 hover:text-slate-600 transition-colors"
              aria-label="Clear search"
            >
              <Icon name="close" className="w-4 h-4" aria-hidden />
            </button>
          )}
          {isActive && (
            <span className="text-xs font-medium bg-accent-100 text-accent-700 px-2 py-0.5 rounded-full">
              Hybrid
            </span>
          )}
        </div>
      </div>

      {/* Explainer */}
      {isActive && (
        <p className="mt-1.5 text-xs text-slate-500 pl-1">
          Searching with <strong>lexical</strong>, <strong>fuzzy</strong>, and{" "}
          <strong>semantic</strong> signals fused via RRF — see per-result badges below.
        </p>
      )}
    </div>
  );
}
