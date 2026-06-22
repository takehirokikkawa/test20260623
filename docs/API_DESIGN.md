# TechInsight — 簡易API設計書

Base URL: `http://localhost:8000`  ／  プレフィックス: `/api`
ドキュメント: FastAPI 自動生成 `/docs`（Swagger UI）, `/openapi.json`

すべての日時は ISO 8601 / UTC。エラーは `{ "detail": "<message>" }`（FastAPI標準）。
CORS は frontend (`http://localhost:3000`) を許可する。

---

## 共通スキーマ

### Article（レスポンス）
```jsonc
{
  "id": "f1c2...-uuid",
  "legacy_id": 12,               // null 可（手動作成記事は null）
  "title": "Understanding Vector Databases",
  "content": "Full body text ...",
  "author": "Alice Tanaka",
  "category": "AI/ML",           // "AI/ML" | "Backend" | "Frontend" | "DevOps"
  "published_at": "2024-05-01T00:00:00Z",
  "created_at": "2026-06-22T10:00:00Z",
  "updated_at": "2026-06-22T10:00:00Z"
}
```
> `content_hash` と `embedding` は内部項目でありレスポンスには含めない。

### ArticleCreate / ArticleUpdate（リクエストボディ）
```jsonc
{
  "title": "string (1..300)",
  "content": "string (1..)",
  "author": "string (1..120)",
  "category": "AI/ML | Backend | Frontend | DevOps",
  "published_at": "2024-05-01T00:00:00Z"   // 省略時はサーバ now()
}
```
- `ArticleUpdate` は全フィールド任意（部分更新）。`title` か `content` が変わった場合のみ埋め込みを再生成する。

### Page<Article>（一覧の包み）
```jsonc
{
  "items": [ /* Article[] */ ],
  "total": 1000,
  "page": 1,
  "size": 20,
  "pages": 50
}
```

---

## エンドポイント

### GET `/health`
- DB 疎通可: 200 → `{ "status": "ok", "db": "ok" }`
- DB 障害時: **503** → `{ "status": "error", "db": "error" }`（LB/オーケストレータが unhealthy 判定できる）

### GET `/api/articles/facets` — フィルタ選択肢
- 200 → `{ "categories": ["AI/ML","Backend","Frontend","DevOps"], "authors": ["...", ...] }`
- `categories` は固定の許可集合、`authors` は生存記事の distinct（フロントの著者セレクトに使用）。

### GET `/api/articles`  — 一覧
クエリパラメータ:
| 名前 | 型 | 既定 | 説明 |
|---|---|---|---|
| `page` | int ≥1 | 1 | ページ番号 |
| `size` | int 1..100 | 20 | 1ページ件数 |
| `category` | string | - | カテゴリ絞り込み |
| `author` | string | - | 著者絞り込み |
| `published_from` | datetime (ISO) | - | この日時以降に絞り込み |
| `published_to` | datetime (ISO) | - | この日時以前に絞り込み |
| `sort` | enum | `-published_at` | `published_at` / `-published_at` / `title` / `-title`（`-`は降順） |

- 200 → `Page<Article>`（論理削除された記事は含まれない）

### GET `/api/articles/{id}` — 詳細
- 200 → `Article` ／ 404 → `{ "detail": "Article not found" }`

### POST `/api/articles` — 作成
- body: `ArticleCreate`
- 201 → `Article`（埋め込みはサーバ側で自動生成）
- 422 → バリデーションエラー

### PUT `/api/articles/{id}` — 更新
- body: `ArticleUpdate`（部分更新）
- 200 → `Article` ／ 404

### DELETE `/api/articles/{id}` — 削除（論理削除）
- 204（body なし）／ 404
- **ソフトデリート**: 物理削除せず `deleted_at` を設定。以後 一覧/詳細/検索 から除外される（誤操作からの復旧余地を残す）。

### POST `/api/articles/import` — CSV 一括インポート
- `multipart/form-data` の `file`（CSV: `id,title,content,author,category,published_at`）
- 初期 ingest と同一パイプライン（content-hash 埋め込みキャッシュ／UUID＋legacy_id／`ON CONFLICT (legacy_id) DO NOTHING` で冪等）。行単位で検証。
- 200 → `ImportResult`:
```jsonc
{
  "total_rows": 6, "valid": 3, "invalid": 3,
  "inserted": 2, "skipped_existing": 1, "unique_embeddings": 3,
  "errors": [ { "row": 5, "error": "invalid category 'Marketing' ..." } ]
}
```
- 400 → ヘッダ不正・空ファイル・非CSV

### GET `/api/search` — ハイブリッド検索
クエリパラメータ:
| 名前 | 型 | 既定 | 説明 |
|---|---|---|---|
| `q` | string (1..) | 必須 | 自然言語クエリ |
| `category` | string | - | ファセット絞り込み |
| `author` | string | - | ファセット絞り込み |
| `limit` | int 1..50 | 20 | 返却件数 |

レスポンス `SearchResponse`:
```jsonc
{
  "query": "how to scale vector search",
  "count": 12,
  "results": [
    {
      "article": { /* Article */ },
      "score": 0.0489,            // RRF統合スコア（降順）
      "signals": {                // ヒット要因（FR-8: 説明性）
        "lexical": true,          // 全文検索でヒット
        "fuzzy": false,           // trigram でヒット
        "semantic": true,         // ベクトル近傍でヒット
        "vector_distance": 0.21,  // コサイン距離（取得できた場合）
        "ts_rank": 0.087          // 全文検索ランク（取得できた場合）
      }
    }
  ]
}
```
- 検索ロジックは RRF（Reciprocal Rank Fusion）。詳細は REQUIREMENTS.md §4.2。
- 200 を返す。クエリの埋め込み生成はサーバ側のローカルモデルで実行（APIキー不要）。

---

## FE/BE 型共有
- Backend は Pydantic v2 でスキーマを定義し OpenAPI を公開。
- Frontend は `openapi-typescript` で `/openapi.json` から型を生成（`frontend/src/types/api.ts`）。
  生成できない環境向けに、手書きの同等型 (`Article`, `Page`, `SearchResponse`) もコミットしておく。
