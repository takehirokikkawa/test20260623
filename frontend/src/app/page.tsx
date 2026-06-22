"use client";

import { useState, useCallback } from "react";
import type { Article } from "@/types/api";
import { deleteArticle } from "@/lib/api";
import { useArticles } from "@/hooks/useArticles";
import { useToast } from "@/components/Toast";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { Facets } from "@/components/Facets";
import { ArticleList } from "@/components/ArticleList";
import { Pagination } from "@/components/Pagination";
import { ArticleDetailModal } from "@/components/ArticleDetailModal";
import { ArticleFormModal } from "@/components/ArticleFormModal";
import { ConfirmDialog } from "@/components/ConfirmDialog";

type Modal =
  | { type: "detail"; article: Article }
  | { type: "form"; article?: Article }
  | { type: "confirm-delete"; article: Article }
  | null;

export default function HomePage() {
  const { showToast } = useToast();
  const state = useArticles();
  const [modal, setModal] = useState<Modal>(null);
  const [deleting, setDeleting] = useState(false);

  // ── Modal handlers ─────────────────────────────────────────────────────────

  const openNew = useCallback(() => setModal({ type: "form" }), []);

  const openView = useCallback((article: Article) => {
    setModal({ type: "detail", article });
  }, []);

  const openEdit = useCallback((article: Article) => {
    setModal({ type: "form", article });
  }, []);

  const openDelete = useCallback((article: Article) => {
    setModal({ type: "confirm-delete", article });
  }, []);

  const closeModal = useCallback(() => setModal(null), []);

  // From detail modal: open edit
  const handleDetailEdit = useCallback((article: Article) => {
    setModal({ type: "form", article });
  }, []);

  // From detail modal: open delete confirm
  const handleDetailDelete = useCallback((article: Article) => {
    setModal({ type: "confirm-delete", article });
  }, []);

  // Form saved
  const handleSaved = useCallback(
    (article: Article, isNew: boolean) => {
      if (isNew) {
        state.optimisticAdd(article);
      } else {
        state.optimisticUpdate(article);
      }
      setModal(null);
    },
    [state]
  );

  // Delete confirmed
  const handleDeleteConfirm = useCallback(async () => {
    if (modal?.type !== "confirm-delete") return;
    const article = modal.article;

    // Optimistic remove
    state.optimisticRemove(article.id);
    setModal(null);
    setDeleting(true);

    try {
      await deleteArticle(article.id);
      showToast("Article deleted", "success");
    } catch (err) {
      // Rollback: refresh the list
      state.refresh();
      showToast(
        err instanceof Error ? err.message : "Delete failed",
        "error"
      );
    } finally {
      setDeleting(false);
    }
  }, [modal, state, showToast]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header onNewArticle={openNew} />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-5">
        {/* Search */}
        <SearchBar value={state.query} onChange={state.setQuery} />

        {/* Facets / filters */}
        <Facets
          category={state.category}
          author={state.author}
          sort={state.sort}
          isSearchMode={state.isSearchMode}
          onCategory={state.setCategory}
          onAuthor={state.setAuthor}
          onSort={state.setSort}
        />

        {/* Article grid */}
        <ArticleList
          articles={state.articles}
          searchResponse={state.searchResponse}
          isSearchMode={state.isSearchMode}
          loading={state.loading}
          error={state.error}
          total={state.total}
          onView={openView}
          onEdit={openEdit}
          onDelete={openDelete}
        />

        {/* Pagination (list mode only) */}
        {!state.isSearchMode && !state.loading && !state.error && (
          <Pagination
            page={state.page}
            totalPages={state.totalPages}
            onPage={state.setPage}
          />
        )}
      </main>

      {/* Modals */}
      {modal?.type === "detail" && (
        <ArticleDetailModal
          article={modal.article}
          onClose={closeModal}
          onEdit={handleDetailEdit}
          onDelete={handleDetailDelete}
        />
      )}

      {modal?.type === "form" && (
        <ArticleFormModal
          article={modal.article}
          onClose={closeModal}
          onSaved={handleSaved}
        />
      )}

      {modal?.type === "confirm-delete" && (
        <ConfirmDialog
          title="Delete article?"
          message={`"${modal.article.title}" will be permanently removed. This action cannot be undone.`}
          confirmLabel={deleting ? "Deleting…" : "Delete"}
          onConfirm={handleDeleteConfirm}
          onCancel={closeModal}
        />
      )}
    </div>
  );
}
