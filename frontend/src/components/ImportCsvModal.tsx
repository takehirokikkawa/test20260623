"use client";

import { useEffect, useRef, useState } from "react";
import type { ImportResult } from "@/types/api";
import { importArticles } from "@/lib/api";
import { useToast } from "./Toast";
import { Icon } from "./Icon";

interface ImportCsvModalProps {
  onClose: () => void;
  /** Called after a successful import so the parent can refresh the list. */
  onImported: (result: ImportResult) => void;
}

export function ImportCsvModal({ onClose, onImported }: ImportCsvModalProps) {
  const { showToast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Escape to close (disabled while importing)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !importing) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose, importing]);

  function pickFile(f: File | null) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      showToast("Please select a .csv file", "error");
      return;
    }
    setFile(f);
    setResult(null);
  }

  async function handleImport() {
    if (!file) return;
    setImporting(true);
    try {
      const res = await importArticles(file);
      setResult(res);
      onImported(res);
      if (res.inserted > 0) {
        showToast(`Imported ${res.inserted} article(s)`, "success");
      } else {
        showToast("No new articles inserted", "info");
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Import failed", "error");
    } finally {
      setImporting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="import-title"
    >
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={() => !importing && onClose()}
        aria-hidden="true"
      />

      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-slate-100 flex items-center justify-between">
          <h2 id="import-title" className="text-lg font-bold text-slate-900">
            Import articles from CSV
          </h2>
          <button
            onClick={onClose}
            disabled={importing}
            className="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 rounded-lg p-1 disabled:opacity-40"
            aria-label="Close import dialog"
          >
            <Icon name="close" className="w-5 h-5" aria-hidden />
          </button>
        </div>

        <div className="px-6 py-5 overflow-y-auto flex-1 space-y-4">
          {/* Format hint */}
          <p className="text-sm text-slate-500">
            Expected columns:{" "}
            <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">
              id, title, content, author, category, published_at
            </code>
            . Embeddings are generated automatically; re-uploading the same file is safe
            (existing rows are skipped).
          </p>

          {/* Dropzone */}
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              pickFile(e.dataTransfer.files?.[0] ?? null);
            }}
            className={`flex flex-col items-center justify-center gap-2 border-2 border-dashed rounded-xl px-4 py-8 cursor-pointer transition-colors ${
              dragging
                ? "border-accent-500 bg-accent-50"
                : "border-slate-300 hover:border-accent-400 hover:bg-slate-50"
            }`}
          >
            <Icon name="upload" className="w-8 h-8 text-slate-400" strokeWidth={1.5} aria-hidden />
            <span className="text-sm font-medium text-slate-700">
              {file ? file.name : "Click to choose a CSV, or drag & drop"}
            </span>
            {file && (
              <span className="text-xs text-slate-400">
                {(file.size / 1024).toFixed(1)} KB
              </span>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
          </label>

          {/* Result summary */}
          {result && (
            <div className="rounded-xl border border-slate-200 overflow-hidden">
              <div className="grid grid-cols-3 divide-x divide-slate-100 text-center">
                <Stat label="Inserted" value={result.inserted} tone="emerald" />
                <Stat label="Skipped" value={result.skipped_existing} tone="slate" />
                <Stat label="Invalid" value={result.invalid} tone={result.invalid ? "red" : "slate"} />
              </div>
              <div className="px-4 py-2 bg-slate-50 text-xs text-slate-500 border-t border-slate-100">
                {result.total_rows} rows read · {result.unique_embeddings} unique embeddings computed
              </div>
              {result.errors.length > 0 && (
                <div className="max-h-40 overflow-y-auto border-t border-slate-100 divide-y divide-slate-50">
                  {result.errors.map((e, i) => (
                    <div key={i} className="px-4 py-1.5 text-xs text-red-600">
                      <span className="font-mono text-slate-400">line {e.row}:</span> {e.error}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={importing}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:opacity-50"
          >
            {result ? "Close" : "Cancel"}
          </button>
          <button
            type="button"
            onClick={handleImport}
            disabled={!file || importing}
            className="px-5 py-2 rounded-lg text-sm font-semibold bg-accent-600 text-white hover:bg-accent-700 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-500 disabled:opacity-50 inline-flex items-center gap-2"
          >
            {importing && (
              <Icon name="spinner" className="w-4 h-4 animate-spin" aria-hidden />
            )}
            {importing ? "Importing…" : result ? "Import again" : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "emerald" | "slate" | "red";
}) {
  const color =
    tone === "emerald"
      ? "text-emerald-600"
      : tone === "red"
      ? "text-red-600"
      : "text-slate-700";
  return (
    <div className="px-4 py-3">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}
