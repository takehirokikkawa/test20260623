"use client";

import type { Signals } from "@/types/api";

interface SearchSignalsProps {
  signals: Signals;
  score: number;
}

export function SearchSignals({ signals, score }: SearchSignalsProps) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2" aria-label="Search match signals">
      {/* Fused RRF score */}
      <span
        className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200"
        title="Reciprocal Rank Fusion score"
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
        </svg>
        RRF {score.toFixed(4)}
      </span>

      {/* Lexical */}
      {signals.lexical && (
        <span
          className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200"
          title={signals.ts_rank != null ? `Full-text rank: ${signals.ts_rank.toFixed(4)}` : "Full-text search match"}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block" />
          Lexical
          {signals.ts_rank != null && (
            <span className="text-blue-500 font-normal">{signals.ts_rank.toFixed(3)}</span>
          )}
        </span>
      )}

      {/* Fuzzy */}
      {signals.fuzzy && (
        <span
          className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200"
          title="Trigram fuzzy match"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" />
          Fuzzy
        </span>
      )}

      {/* Semantic */}
      {signals.semantic && (
        <span
          className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-200"
          title={signals.vector_distance != null ? `Cosine distance: ${signals.vector_distance.toFixed(4)}` : "Vector semantic match"}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-violet-500 inline-block" />
          Semantic
          {signals.vector_distance != null && (
            <span className="text-violet-500 font-normal">d={signals.vector_distance.toFixed(3)}</span>
          )}
        </span>
      )}
    </div>
  );
}
