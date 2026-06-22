"use client";

import { useEffect, useState } from "react";
import type { Article, ArticleCreate, ArticleUpdate, Category } from "@/types/api";
import { CATEGORIES } from "@/types/api";
import { createArticle, updateArticle } from "@/lib/api";
import { useToast } from "./Toast";

interface ArticleFormModalProps {
  /** Provide article to edit; omit/null for create mode */
  article?: Article | null;
  onClose: () => void;
  onSaved: (article: Article, isNew: boolean) => void;
}

interface FormState {
  title: string;
  content: string;
  author: string;
  category: Category;
  published_at: string;
}

function toDatetimeLocal(iso: string): string {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return "";
  }
}

function toISOString(local: string): string {
  // Convert datetime-local value to ISO string
  if (!local) return new Date().toISOString();
  return new Date(local).toISOString();
}

export function ArticleFormModal({ article, onClose, onSaved }: ArticleFormModalProps) {
  const { showToast } = useToast();
  const isEdit = article != null;

  const [form, setForm] = useState<FormState>({
    title: article?.title ?? "",
    content: article?.content ?? "",
    author: article?.author ?? "",
    category: (article?.category as Category) ?? "AI/ML",
    published_at: article ? toDatetimeLocal(article.published_at) : toDatetimeLocal(new Date().toISOString()),
  });
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof FormState, string>>>({});

  // Escape to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const set = <K extends keyof FormState>(key: K, val: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: val }));
    setFieldErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  function validate(): boolean {
    const errors: Partial<Record<keyof FormState, string>> = {};
    if (!form.title.trim()) errors.title = "Title is required";
    else if (form.title.trim().length > 300) errors.title = "Max 300 characters";
    if (!form.content.trim()) errors.content = "Content is required";
    if (!form.author.trim()) errors.author = "Author is required";
    else if (form.author.trim().length > 120) errors.author = "Max 120 characters";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      const published_at = toISOString(form.published_at);
      let saved: Article;

      if (isEdit && article) {
        const body: ArticleUpdate = {
          title: form.title.trim(),
          content: form.content.trim(),
          author: form.author.trim(),
          category: form.category,
          published_at,
        };
        saved = await updateArticle(article.id, body);
        showToast("Article updated successfully", "success");
      } else {
        const body: ArticleCreate = {
          title: form.title.trim(),
          content: form.content.trim(),
          author: form.author.trim(),
          category: form.category,
          published_at,
        };
        saved = await createArticle(body);
        showToast("Article created successfully", "success");
      }

      onSaved(saved, !isEdit);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Save failed";
      showToast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="form-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-slate-100 flex items-center justify-between">
          <h2 id="form-title" className="text-lg font-bold text-slate-900">
            {isEdit ? "Edit Article" : "New Article"}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 rounded-lg p-1"
            aria-label="Close form"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form body */}
        <form
          id="article-form"
          onSubmit={handleSubmit}
          className="px-6 py-5 overflow-y-auto flex-1 space-y-5"
          noValidate
        >
          {/* Title */}
          <div>
            <label htmlFor="f-title" className="block text-sm font-medium text-slate-700 mb-1">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              id="f-title"
              type="text"
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
              maxLength={300}
              className={`w-full border rounded-lg px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-accent-500 transition-colors ${fieldErrors.title ? "border-red-400" : "border-slate-300"}`}
              placeholder="Article title"
            />
            {fieldErrors.title && <p className="mt-1 text-xs text-red-500">{fieldErrors.title}</p>}
          </div>

          {/* Author + Category row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="f-author" className="block text-sm font-medium text-slate-700 mb-1">
                Author <span className="text-red-500">*</span>
              </label>
              <input
                id="f-author"
                type="text"
                value={form.author}
                onChange={(e) => set("author", e.target.value)}
                maxLength={120}
                className={`w-full border rounded-lg px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-accent-500 transition-colors ${fieldErrors.author ? "border-red-400" : "border-slate-300"}`}
                placeholder="Author name"
              />
              {fieldErrors.author && <p className="mt-1 text-xs text-red-500">{fieldErrors.author}</p>}
            </div>
            <div>
              <label htmlFor="f-category" className="block text-sm font-medium text-slate-700 mb-1">
                Category <span className="text-red-500">*</span>
              </label>
              <select
                id="f-category"
                value={form.category}
                onChange={(e) => set("category", e.target.value as Category)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-accent-500"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Published at */}
          <div>
            <label htmlFor="f-published-at" className="block text-sm font-medium text-slate-700 mb-1">
              Published date
            </label>
            <input
              id="f-published-at"
              type="datetime-local"
              value={form.published_at}
              onChange={(e) => set("published_at", e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-accent-500"
            />
          </div>

          {/* Content */}
          <div>
            <label htmlFor="f-content" className="block text-sm font-medium text-slate-700 mb-1">
              Content <span className="text-red-500">*</span>
            </label>
            <textarea
              id="f-content"
              value={form.content}
              onChange={(e) => set("content", e.target.value)}
              rows={8}
              className={`w-full border rounded-lg px-3 py-2.5 text-sm text-slate-800 resize-y focus:outline-none focus:ring-2 focus:ring-accent-500 transition-colors ${fieldErrors.content ? "border-red-400" : "border-slate-300"}`}
              placeholder="Article content…"
            />
            {fieldErrors.content && <p className="mt-1 text-xs text-red-500">{fieldErrors.content}</p>}
          </div>
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="article-form"
            disabled={submitting}
            className="px-5 py-2 rounded-lg text-sm font-semibold bg-accent-600 text-white hover:bg-accent-700 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-500 disabled:opacity-60 inline-flex items-center gap-2"
          >
            {submitting && (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {isEdit ? "Save Changes" : "Create Article"}
          </button>
        </div>
      </div>
    </div>
  );
}
