# TechInsight 要件定義書

AI搭載型ナレッジベース「TechInsight」の設計・実装に関する要件定義書。
本ドキュメントは開発の基準（Single Source of Truth）であり、マイルストーンと完了条件（DoD）を含む。

- **ステータス**: Draft v1.0
- **最終更新**: 2026-06-22
- **対象システム**: TechInsight（技術記事ナレッジマネジメントシステム）

---

## 1. 目的とスコープ

### 1.1 目的

技術記事データを基盤に、**CRUD によるナレッジ管理**と**自然言語クエリに対するセマンティック検索**を提供するWebアプリケーションを構築する。評価者のローカル環境で `docker compose up` のワンコマンドで完全に再現・動作することを最優先要件とする。

### 1.2 スコープ

| 区分 | 含む | 含まない |
|---|---|---|
| 機能 | 記事のCRUD、ハイブリッド検索、管理UI、CSV初期取り込み | 認証・認可、ユーザー管理、多言語UI、CI/CDパイプライン構築 |
| データ | 提供CSV（1,000件）の取り込み、将来1万件規模を想定した設計 | 外部データソース連携、リアルタイムクロール |
| 運用 | ローカル完結のDocker環境、マイグレーション自動化 | クラウドデプロイ、本番監視基盤 |

### 1.3 前提条件・制約

- 評価者は**APIキーを保持しない**。よって埋め込み生成は**ローカルで完結する OSS モデル**を用い、外部API（OpenAI等）には依存しない。
- 全サービス（DB / API / Frontend）が `docker compose up` のみで起動し、マイグレーションとデータ投入まで自動完了すること。
- 一人開発だが、**チーム開発を前提とした構成**（責務分離・型共有・ドキュメント整備）とする。

---

## 2. データ分析サマリ（設計の根拠）

提供 `articles.csv`（1,000行 × 6列、欠損ゼロ）の分析結果。設計判断はこの特性に基づく。

| 項目 | 内容 | 設計への影響 |
|---|---|---|
| カラム | id, title, content, author, category, published_at | スキーマの基礎 |
| content 長 | 平均312文字・標準偏差8 と極めて均質 | 純ベクトル検索だと類似度が団子になる |
| ユニーク本文 | **1,000行中449種類のみ**（最大8回重複） | 埋め込みをハッシュ単位でキャッシュ→計算量を半減 |
| 言語 | 全て英語 | 英語特化の軽量埋め込みモデルで十分 |
| category | 4種（AI/ML, Backend, Frontend, DevOps）ほぼ均等 | ファセット絞り込みに利用 |
| author | 8名、ほぼ均等 | フィルタ・将来の正規化対象 |
| published_at | 2023-01〜2025-09、TZ情報なし | TIMESTAMPTZ で UTC 正規化して格納 |

**結論**: 本文が均質なためベクトル類似度だけでは識別力が不足する。**全文検索（語の一致）とベクトル検索（意味の近さ）を統合するハイブリッド検索**が品質・説明性の両面で最適。

---

## 3. 技術スタック

| レイヤ | 採用技術 | 補足 |
|---|---|---|
| Backend | Python 3.12 / FastAPI | 非同期、型ヒント、自動OpenAPIドキュメント |
| Frontend | Next.js (App Router) / TypeScript / React | SSR/CSRの併用、型安全 |
| Database | PostgreSQL 16 + `pgvector` + `pg_trgm` | ベクトル・全文検索・あいまい一致を単一DBで完結 |
| 埋め込み | `sentence-transformers` / `all-MiniLM-L6-v2`（384次元） | ローカル実行、APIキー不要。多言語が必要なら `paraphrase-multilingual-MiniLM-L12-v2`（同384次元）に差し替え可能 |
| ORM/マイグレーション | SQLAlchemy + Alembic | スキーマのバージョン管理 |
| コンテナ | Docker / Docker Compose | ワンコマンド起動 |

> モデルファイルはイメージビルド時に同梱（または初回ビルドで取得）し、起動後はネットワーク非依存で再現できるようにする。

---

## 4. 機能要件

### 4.1 記事CRUD（FR-CRUD）

| ID | 要件 | エンドポイント（案） |
|---|---|---|
| FR-1 | 記事一覧取得（ページング・category/authorフィルタ・並び替え対応） | `GET /api/articles` |
| FR-2 | 記事詳細取得 | `GET /api/articles/{id}` |
| FR-3 | 記事新規作成（作成時に埋め込みを自動生成） | `POST /api/articles` |
| FR-4 | 記事更新（title/content変更時に埋め込みを再生成） | `PUT /api/articles/{id}` |
| FR-5 | 記事削除 | `DELETE /api/articles/{id}` |

### 4.2 ハイブリッド検索（FR-SEARCH）

| ID | 要件 |
|---|---|
| FR-6 | 自然言語クエリを受け取り、**全文検索スコア**・**trigram類似度**・**ベクトル類似度**を統合した検索結果を返す |
| FR-7 | category / author によるファセット絞り込みを検索と併用できる |
| FR-8 | 各結果に統合スコアと、ヒット要因（語一致 / 意味的近接）が分かるメタ情報を返す |

**検索ロジック（推奨実装）**: Reciprocal Rank Fusion（RRF）

1. クエリを正規化し、3つの候補集合を取得する。
   - **全文検索**: `to_tsvector(content) @@ websearch_to_tsquery(query)` を `ts_rank` 順に取得。
   - **あいまい一致**: `pg_trgm` の `similarity(title, query)` 上位を取得（タイポ・部分一致に強い）。
   - **ベクトル検索**: クエリを埋め込み化し、`embedding <=> query_vec`（コサイン距離）のkNNをHNSWインデックスで取得。
2. 各候補のランクから RRF スコアを算出し統合する。
   `score = Σ ( weight_i / (k + rank_i) )` （`k≈60`、weightは検索手段ごとに調整可能）
3. 統合スコア降順で返却。

> RRF は**スコアの絶対値ではなく順位**で統合するため、本データのように埋め込み類似度が高位に密集していても安定して効く。重み付き線形結合（スコア正規化）は代替案として切り替え可能にしておく。

### 4.3 データ取り込み（FR-INGEST）

| ID | 要件 |
|---|---|
| FR-9 | `docker compose up` 時にマイグレーション実行後、CSVを自動取り込みする（冪等：再実行で重複投入しない） |
| FR-10 | **取り込み時に各記事へ UUID を採番する**（CSVの元IDは `legacy_id` として保持しトレーサビリティを確保） |
| FR-11 | content をハッシュ化し、**同一本文の埋め込みは一度だけ計算**してキャッシュ・再利用する（449回計算で1,000件を処理） |

---

## 5. 非機能要件

| 区分 | ID | 要件 |
|---|---|---|
| 再現性 | NFR-1 | クローン後 `docker compose up` のみで全機能がローカル動作。APIキー不要 |
| パフォーマンス | NFR-2 | 1万件規模で検索レスポンス 1秒以内を目標。HNSW / GIN / btree インデックスを事前付与 |
| スケーラビリティ | NFR-3 | 埋め込み生成はバッチ・非同期化可能な設計とし、件数増加に耐える |
| 保守運用 | NFR-4 | Alembicによるスキーマ変更管理、構造化ログ、`/health` ヘルスチェック |
| 品質 | NFR-5 | backendはpytest、frontendは型チェックを通す。lint/format（ruff, eslint, prettier）を整備 |
| チーム開発 | NFR-6 | レイヤ分離（router/service/repository）、OpenAPIからの型自動生成でFE/BE間の型を共有 |
| UX | NFR-7 | 検索中ローディング表示、空結果・エラーの明示、レスポンシブ対応、楽観的UI更新 |

---

## 6. データベース設計（確定スキーマ）

PostgreSQL に `pgvector`・`pg_trgm` 拡張を有効化。埋め込みは384次元。

### 6.1 articles テーブル

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` | 主キー。取り込み時採番 |
| `legacy_id` | INTEGER | UNIQUE, NULL可 | CSV元IDを保持（トレーサビリティ） |
| `title` | TEXT | NOT NULL | 記事タイトル |
| `content` | TEXT | NOT NULL | 本文 |
| `author` | TEXT | NOT NULL | 著者名 |
| `category` | TEXT | NOT NULL | カテゴリ |
| `published_at` | TIMESTAMPTZ | NOT NULL | 公開日時（UTC正規化） |
| `content_hash` | TEXT | NOT NULL | `sha256(content)`。埋め込みキャッシュのキー |
| `embedding` | `vector(384)` | NULL可 | 本文の埋め込みベクトル |
| `search_tsv` | tsvector | GENERATED | `to_tsvector('english', title || ' ' || content)` の生成列 |
| `created_at` | TIMESTAMPTZ | default `now()` | 作成日時 |
| `updated_at` | TIMESTAMPTZ | default `now()` | 更新日時（トリガで自動更新） |

### 6.2 インデックス

| インデックス | 対象 | 用途 |
|---|---|---|
| HNSW (`vector_cosine_ops`) | `embedding` | ベクトル近傍検索 |
| GIN | `search_tsv` | 全文検索 |
| GIN (`gin_trgm_ops`) | `title` | あいまい・部分一致 |
| btree | `category`, `author`, `published_at` | フィルタ・ソート |
| btree (unique) | `legacy_id` | 冪等な再取り込み |

### 6.3 設計上の判断

- **UUIDを主キーに採用**: 分散環境・マージ・外部公開時の安全性を考慮。元のCSV連番IDは `legacy_id` に退避し、移行元との突合を可能にする。
- **埋め込みキャッシュ**: 取り込み時は `content_hash` で重複本文を判定し、ユニーク本文（449件）のみ計算してから各行へ展開する。`embedding` 列はクエリ性能のため記事行にインライン保持する（読み取り最適化）。
- **author / category**: 現状はTEXTで保持しbtree索引を付与。将来の正規化（マスタテーブル化）を見据え、サービス層で値域を一元管理する。
- **生成列 `search_tsv`**: アプリ側で同期する手間を排し、常に最新の全文検索ベクトルをDBが保証する。

---

## 7. API設計（概要）

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/api/articles` | 一覧（`page`, `size`, `category`, `author`, `sort`） |
| GET | `/api/articles/{id}` | 詳細 |
| POST | `/api/articles` | 作成（埋め込み自動生成） |
| PUT | `/api/articles/{id}` | 更新（本文変更時に埋め込み再生成） |
| DELETE | `/api/articles/{id}` | 削除 |
| GET | `/api/search` | ハイブリッド検索（`q`, `category`, `author`, `limit`） |
| GET | `/health` | ヘルスチェック |

- レスポンスは Pydantic スキーマで型定義し、OpenAPI を自動生成。FrontendはこのスキーマからTypeScript型を生成して共有する。
- エラーは統一フォーマット（`{ "detail": ... }`）で返却。

---

## 8. フロントエンド要件

| 画面 | 要件 |
|---|---|
| 一覧・検索画面 | 記事カードの一覧表示、検索バー（自然言語）、category/authorファセット、ページング、ローディング・空状態の明示 |
| 記事詳細 | モーダルまたは詳細ビューで全文・メタ情報を表示 |
| 管理機能 | 投稿フォーム、編集フォーム、削除確認。作成/更新/削除後は一覧へ即時反映 |

UXの工夫として、検索結果のヒット要因（語一致 / 意味的近接）の可視化、楽観的更新、トースト通知を盛り込む。

---

## 9. システム構成（Docker Compose）

```
techinsight/
├─ docker-compose.yml          # db / backend / frontend / migrate
├─ backend/                    # FastAPI（router / service / repository / models）
│  ├─ app/
│  ├─ alembic/                 # マイグレーション
│  ├─ scripts/ingest_csv.py    # CSV→UUID採番→埋め込み→投入
│  └─ Dockerfile
├─ frontend/                   # Next.js / TypeScript
│  └─ Dockerfile
├─ data/articles.csv           # 初期データ
├─ docs/
│  ├─ REQUIREMENTS.md          # 本書
│  ├─ DB_DESIGN.md             # DB設計書
│  └─ API_DESIGN.md            # API設計書
└─ README.md
```

起動シーケンス: `db` 起動 → ヘルスチェック通過 → `migrate`（Alembic + CSV取り込み）完了 → `backend` 起動 → `frontend` 起動。

---

## 10. マイルストーン

各マイルストーンは独立して検証可能とし、完了条件（DoD）を満たした時点で次へ進む。

### M0: 環境構築・足場づくり
- **目標**: リポジトリ初期化とDocker Composeの骨組み、空のFastAPI / Next.js / PostgreSQL連携。
- **成果物**: `docker-compose.yml`、各Dockerfile、`/health` 応答、Next.js初期画面。
- **DoD**: `docker compose up` で3サービスが起動し、FEからBEの`/health`に到達できる。

### M1: データ基盤とマイグレーション
- **目標**: DBスキーマ確定、pgvector/pg_trgm有効化、CSV取り込み（UUID採番・埋め込みキャッシュ）。
- **成果物**: Alembicマイグレーション、`ingest_csv.py`、インデックス。
- **DoD**: `docker compose up` で1,000件が投入され、`legacy_id`保持・UUID採番・埋め込み生成が完了。再実行しても重複しない（冪等）。

### M2: CRUD API
- **目標**: FR-1〜FR-5の実装。作成・更新時の埋め込み連動。
- **成果物**: router/service/repositoryの3層、Pydanticスキーマ、pytest。
- **DoD**: 全CRUDがOpenAPI上で動作し、テストが通る。

### M3: ハイブリッド検索API
- **目標**: FR-6〜FR-8。全文検索 + trigram + ベクトルのRRF統合。
- **成果物**: `/api/search`、スコア統合ロジック、検索テスト。
- **DoD**: 自然言語クエリで意味的に妥当な順位の結果が返り、ファセット絞り込みが併用できる。

### M4: フロントエンド
- **目標**: 一覧・検索・詳細・管理UIの実装。OpenAPIからの型生成。
- **成果物**: 検索画面、詳細モーダル、投稿/編集/削除フォーム。
- **DoD**: ブラウザから検索・閲覧・CRUDが一通り完結し、ローディング/エラー/空状態が表示される。

### M5: 仕上げ・ドキュメント・チューニング
- **目標**: README整備、DB/API設計書、パフォーマンス確認、lint/format/テスト整備。
- **成果物**: `README.md`、`DB_DESIGN.md`、`API_DESIGN.md`、実装説明（UI/UX・DB・チーム開発・保守運用/スケーラビリティの観点）。
- **DoD**: クリーン環境で `git clone` → `docker compose up` のみで全機能が再現でき、提出物が揃う。

---

## 11. リスクと対応

| リスク | 影響 | 対応 |
|---|---|---|
| データが均質で純ベクトル検索の識別力が低い | 検索品質の低下 | ハイブリッド検索（RRF）で語一致シグナルを補完 |
| 埋め込みモデルのダウンロードがビルド時に必要 | オフライン再現性 | モデルをイメージに同梱し起動後はネットワーク非依存に |
| 1万件規模での検索遅延 | NFR-2未達 | HNSW/GINを事前付与、ページング、必要に応じ`ef_search`調整 |
| 日本語クエリ × 英語本文の精度 | 検索体験 | 必要時に多言語埋め込みモデルへ差し替え（次元数同一で移行容易） |

---

## 12. 完了の定義（プロジェクト全体）

1. `git clone` 後、`docker compose up` のみで全サービスが起動しCSVが投入される。
2. ブラウザから検索・閲覧・CRUDが完全動作する。
3. 検索がハイブリッド方式で意味的に妥当な結果を返す。
4. README・DB設計書・API設計書・実装説明が提出される。
