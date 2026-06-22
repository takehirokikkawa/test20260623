"use client";

import { useEffect } from "react";

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = "Delete",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 id="confirm-title" className="text-lg font-semibold text-slate-900">
          {title}
        </h2>
        <p className="text-sm text-slate-600">{message}</p>

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
