# TechInsight — 簡易DB設計書

DBMS: **PostgreSQL 16**（イメージ `pgvector/pgvector:pg16`）
拡張: `vector`（pgvector）, `pg_trgm`, `pgcrypto`（`gen_random_uuid()` 用）

---

## 1. ER 概要

現フェーズは単一テーブル `articles`。author / category は将来のマスタ正規化を見据え、現状は TEXT + 索引で保持する。

```
┌──────────────────────────── articles ────────────────────────────┐
│ id            UUID        PK   gen_random_uuid()                  │
│ legacy_id     INTEGER     UQ   (CSV元ID, nullable)                │
│ title         TEXT        NN                                      │
│ content       TEXT        NN                                      │
│ author        TEXT        NN                                      │
│ category      TEXT        NN                                      │
│ published_at  TIMESTAMPTZ NN                                      │
│ content_hash  TEXT        NN   sha256(content)                    │
│ embedding     vector(384) -    本文埋め込み (nullable)            │
│ search_tsv    tsvector    GEN  to_tsvector('english', title|content)│
│ created_at    TIMESTAMPTZ      now()                              │
│ updated_at    TIMESTAMPTZ      now() (トリガ更新)                 │
└───────────────────────────────────────────────────────────────────┘
```

## 2. DDL（Alembic で生成する内容と等価）

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE articles (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legacy_id     INTEGER UNIQUE,
    title         TEXT NOT NULL,
    content       TEXT NOT NULL,
    author        TEXT NOT NULL,
    category      TEXT NOT NULL,
    published_at  TIMESTAMPTZ NOT NULL,
    content_hash  TEXT NOT NULL,
    embedding     vector(384),
    search_tsv    tsvector GENERATED ALWAYS AS (
                     to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,''))
                  ) STORED,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ベクトル近傍（コサイン）
CREATE INDEX idx_articles_embedding_hnsw
    ON articles USING hnsw (embedding vector_cosine_ops);
-- 全文検索
CREATE INDEX idx_articles_tsv ON articles USING gin (search_tsv);
-- あいまい一致（タイトル）
CREATE INDEX idx_articles_title_trgm ON articles USING gin (title gin_trgm_ops);
-- フィルタ・ソート
CREATE INDEX idx_articles_category   ON articles (category);
CREATE INDEX idx_articles_author     ON articles (author);
CREATE INDEX idx_articles_published  ON articles (published_at DESC);

-- updated_at 自動更新トリガ
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_articles_updated
    BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

## 3. インデックス設計の根拠（1万件規模）

| インデックス | 種別 | 解決するクエリ | スケール時の効果 |
|---|---|---|---|
| `idx_articles_embedding_hnsw` | HNSW | ベクトルkNN（`<=>`） | 近似最近傍で O(log n) 相当。全件スキャン回避 |
| `idx_articles_tsv` | GIN | 全文検索 `@@` | 転置索引で語一致を高速化 |
| `idx_articles_title_trgm` | GIN(trgm) | `similarity()` / `ILIKE` | タイポ・部分一致を索引化 |
| `idx_articles_category/author` | btree | ファセット絞り込み | 選択率の高い絞り込みで有効 |
| `idx_articles_published` | btree desc | 既定ソート（新着順） | ソート用ソート回避 |

- HNSW のクエリ時再現率は `SET hnsw.ef_search` で調整可能（既定で十分、必要時に上げる）。
- 検索は「絞り込み（category/author）→ 各手段で候補取得 → RRF統合」の順。絞り込みを各サブクエリ内に押し込み、候補集合を小さく保つ。

## 4. 取り込み（ingest）設計

1. CSV を読み込み、`content_hash = sha256(content)` を計算。
2. ユニークな `content_hash` ごとに **一度だけ** 埋め込みを生成（本データは1,000行→449回計算）。
3. 各行へ UUID 採番、`legacy_id` に CSV の id を保持。
4. `ON CONFLICT (legacy_id) DO NOTHING` で**冪等**に投入（再起動・再実行で重複しない）。
5. バッチ INSERT（例: 500件単位）でラウンドトリップを削減。

## 4.5 スキーマ追補（migration 0002）

レビュー指摘を反映した追加分（`alembic/versions/0002_*`）。

| 変更 | 内容 | 目的 |
|---|---|---|
| 列追加 `deleted_at TIMESTAMPTZ` | NULL=生存 / 非NULL=削除時刻 | **論理削除**。物理削除せず復旧余地を残す。一覧/詳細/検索は `deleted_at IS NULL` で除外 |
| CHECK 制約 `ck_articles_category` | `category IN ('AI/ML','Backend','Frontend','DevOps')` | カテゴリの値域を DB レベルで保証（表記ゆれ・不正値の混入防止） |
| 複合索引 `idx_articles_category_published` | `(category, published_at DESC)` | 「カテゴリ絞り込み＋新着順」を高速化 |
| 部分索引 `idx_articles_live` | `(published_at DESC) WHERE deleted_at IS NULL` | 生存行スキャンを軽量に保つ |

## 4.6 著者・カテゴリの正規化（migration 0003）

自由文字列だった `category` / `author` を**マスタテーブル + FK** に正規化。

| テーブル | 列 |
|---|---|
| `categories` | `id SMALLINT PK (identity)`, `name TEXT UNIQUE` — 固定4種を seed |
| `authors` | `id INT PK (identity)`, `name TEXT UNIQUE` — ingest/import/作成時に upsert |
| `articles` | `category_id SMALLINT NOT NULL FK→categories`, `author_id INT NOT NULL FK→authors`（旧 text 列は削除） |

- **整合性**: 表記ゆれ・不正値を FK で構造的に排除（旧 CHECK 制約は不要になり 0003 で除去）。
- **索引**: `idx_articles_category_id` / `idx_articles_author_id` / 複合 `idx_articles_catid_published (category_id, published_at DESC)`。
- **カテゴリ一覧**: 小さな `categories` 表の参照で取得（記事テーブルのフルスキャン不要）。
- **API 互換**: レスポンスは従来どおり `category` / `author` を**文字列**で返す（ORM 側で join 済みリレーションの読み取り専用プロパティとして公開）。フロントは無改修。
- **facet の著者**: 生存記事を持つ著者のみ（`authors ⨝ live articles`）。論理削除のみの著者は出さない。

## 5. 将来拡張（スケーラビリティ）

- author / category のマスタテーブル化（FK 正規化）。
- 全文検索の言語別 tsvector、多言語埋め込みへの移行（次元数を 384 に揃えてあるため列変更不要）。
- パーティショニング（`published_at` レンジ）やリードレプリカ。
- 埋め込み生成の非同期キュー化（作成/更新時に即時計算 → バックグラウンドジョブへ）。
