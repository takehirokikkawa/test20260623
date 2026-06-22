# TechInsight — Frontend

Next.js 14 (App Router) · TypeScript · Tailwind CSS

## Dev setup

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Open <http://localhost:3000>.

## Build (matches Dockerfile)

```bash
npm run build   # produces .next/standalone
node .next/standalone/server.js
```

The Dockerfile does this automatically via `docker compose up --build`.

## Key architecture

| Layer | File(s) |
|---|---|
| Types | `src/types/api.ts` — mirrors API_DESIGN.md exactly |
| API client | `src/lib/api.ts` — typed fetch wrappers (listArticles, getArticle, createArticle, updateArticle, deleteArticle, search) |
| State hook | `src/hooks/useArticles.ts` — unified list/search state, pagination, optimistic helpers |
| Page | `src/app/page.tsx` — client component wiring all pieces together |
| Components | `src/components/` — see below |

## Component map

- `Header` — sticky top bar, "New Article" button
- `SearchBar` — natural-language input; shows hybrid-search explainer when active
- `Facets` — category select + author text filter + sort (list mode)
- `ArticleList` — responsive card grid, loading skeletons, empty state, error state
- `ArticleCard` — title, author, category badge, date, snippet; renders `SearchSignals` when in search mode
- `SearchSignals` — **FR-8**: per-result lexical / fuzzy / semantic badges + RRF score + ts_rank / vector_distance values
- `Pagination` — ellipsis-aware page navigator
- `ArticleDetailModal` — full content + metadata; Esc-closable
- `ArticleFormModal` — create / edit form with client-side validation; calls API and notifies via toast
- `ConfirmDialog` — delete confirmation; Esc-closable
- `Toast / ToastProvider` — success/error/info notifications (bottom-right, auto-dismiss 3.5 s)

## Environment

| Variable | Default | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Passed as build arg in docker-compose |

All API calls are **client-side** (no server-side fetch) to avoid container-to-container URL mismatches in the browser.
