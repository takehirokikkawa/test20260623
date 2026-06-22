# TechInsight — AI-Powered Technical Knowledge Base

技術記事を管理し、**自然言語クエリによるセマンティック検索**ができるフルスタック・ナレッジベースです。
記事の CRUD と、全文検索・あいまい検索・ベクトル検索を統合した **ハイブリッド検索**（RRF）を提供します。

> **評価者向け要点**: `docker compose up --build` のワンコマンドだけで、DB・API・フロントエンドが起動し、
> 1,000件の記事が自動投入されます。**APIキーは一切不要**です（埋め込みはローカルモデルで生成）。

---

## クイックスタート

前提: Docker / Docker Compose が動作する環境のみ。

```bash
git clone <this-repo>
cd techinsight   # （本リポジトリのルート）
docker compose up --build
```

初回はイメージのビルド（PyTorch CPU 版・埋め込みモデルの取り込みを含む）で数分かかります。
ビルド後、以下が自動で行われます:

1. PostgreSQL（pgvector 拡張つき）が起動
2. `migrate` ジョブが Alembic マイグレーション → CSV(1,000件) を取り込み（埋め込み生成つき・冪等）
3. Backend(FastAPI) が起動
4. Frontend(Next.js) が起動

起動後のアクセス先:

| サービス | URL |
|---|---|
| フロントエンド | http://localhost:3000 |
| API ドキュメント (Swagger) | http://localhost:8000/docs |
| ヘルスチェック | http://localhost:8000/health |

停止: `docker compose down` ／ データも消す場合: `docker compose down -v`

---

## アーキテクチャ

```
┌──────────────┐      ┌──────────────────┐      ┌────────────────────────┐
│  Frontend    │ ───▶ │   Backend API    │ ───▶ │  PostgreSQL 16         │
│  Next.js     │ HTTP │   FastAPI        │ SQL  │  + pgvector            │
│  (port 3000) │      │   (port 8000)    │      │  + pg_trgm             │
└──────────────┘      └────────┬─────────┘      └────────────────────────┘
                               │
                      ┌────────▼─────────┐
                      │ sentence-        │  ローカル埋め込み生成
                      │ transformers     │  (all-MiniLM-L6-v2, 384次元)
                      │ (APIキー不要)     │  ※イメージに同梱
                      └──────────────────┘
```

- **ハイブリッド検索**: 全文検索(`tsvector`)＋あいまい一致(`pg_trgm`)＋ベクトル近傍(`pgvector` HNSW) を
  **Reciprocal Rank Fusion (RRF)** で統合。各結果に「どの要因でヒットしたか」(lexical / fuzzy / semantic)を付与。
- **埋め込みはローカル完結**: モデルをDockerイメージにビルド時同梱し、実行時は `TRANSFORMERS_OFFLINE=1` で
  ネットワーク非依存。評価者はAPIキー不要で完全再現可能。

詳細な設計は以下を参照:
- [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) — 要件定義（SSOT）
- [docs/DB_DESIGN.md](docs/DB_DESIGN.md) — 簡易DB設計書
- [docs/API_DESIGN.md](docs/API_DESIGN.md) — 簡易API設計書
- [docs/IMPLEMENTATION_NOTES.md](docs/IMPLEMENTATION_NOTES.md) — 実装の説明・工夫した点（UI/UX・DB・チーム開発・保守運用/スケーラビリティ）

---

## 技術スタック

| レイヤ | 技術 |
|---|---|
| Frontend | Next.js 14 (App Router) / TypeScript / React 18 / Tailwind CSS |
| Backend | Python 3.12 / FastAPI / SQLAlchemy 2 (async) / Pydantic v2 |
| DB | PostgreSQL 16 + pgvector + pg_trgm |
| 埋め込み | sentence-transformers `all-MiniLM-L6-v2`（384次元・ローカル） |
| マイグレーション | Alembic |
| インフラ | Docker / Docker Compose |

---

## ディレクトリ構成

```
.
├─ docker-compose.yml          # db / migrate / backend / frontend をワンコマンド起動
├─ .env.example                # 設定の既定値（コピー不要でも動作）
├─ data/
│  ├─ articles.csv             # 初期データ(1,000件)
│  └─ generate_sample_csv.py   # サンプルCSV生成スクリプト（実データに差し替え可）
├─ backend/
│  ├─ app/                     # FastAPI（routers / services / repositories / models）
│  │  ├─ services/search_service.py   # ハイブリッド検索（RRF）
│  │  └─ scripts/ingest_csv.py        # 冪等なCSV取り込み（埋め込みキャッシュ）
│  ├─ alembic/                 # スキーマ・マイグレーション
│  ├─ tests/                   # pytest（RRF・スキーマの単体テスト）
│  ├─ Dockerfile / entrypoint.sh
│  └─ requirements.txt
├─ frontend/
│  ├─ src/                     # app / components / hooks / lib / types
│  └─ Dockerfile
└─ docs/                       # 要件・DB設計・API設計・実装説明
```

---

## 主な機能

- 記事の一覧・ページング・カテゴリ/著者フィルタ・並び替え
- 自然言語クエリによるハイブリッド検索（ヒット要因バッジつき）
- 記事詳細（モーダル全文表示）
- 記事の投稿・編集・削除（管理UI、楽観的更新・トースト通知）

---

## 開発（コンテナを使わない場合）

```bash
# Backend
cd backend && python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# PostgreSQL を別途起動し DATABASE_URL を設定の上:
alembic upgrade head && python -m app.scripts.ingest_csv
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# テスト（DB不要の単体テスト）
cd backend && pytest tests/
```

---

## 実データ（articles.csv）の差し替え

`data/articles.csv`（ヘッダ: `id,title,content,author,category,published_at`）が初期データです（提供された1,000件）。
別のデータに差し替える場合は同じヘッダのCSVを置き、ボリュームをリセットして起動します:

```bash
docker compose down -v && docker compose up --build
```

取り込みは `legacy_id`(=CSVのid) に対して冪等です。**同じ legacy_id の内容を入れ替えたい場合は、上記のように
ボリュームを破棄**してください（冪等性のため、既存 legacy_id はスキップされ上書きされません）。

---

## トラブルシュート

- **ポート競合**: `.env` を作成し `BACKEND_PORT` / `FRONTEND_PORT` / `DB_PORT` を変更。
- **初回ビルドが遅い**: PyTorch とモデルの取得を含むため。2回目以降はキャッシュされます。
- **フロントからAPIに繋がらない**: `NEXT_PUBLIC_API_BASE_URL`（既定 `http://localhost:8000`）を確認。
