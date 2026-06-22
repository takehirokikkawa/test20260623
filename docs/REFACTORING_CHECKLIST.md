# リファクタリング チェックリスト（コードレビュー対応）

レビュー（69/100）の指摘を、優先度付きチェックリストに落としたもの。
各項目はテスト保護下（変更前グリーン → 変更 → テスト）で対応する。

優先度: 🔴 CRITICAL / 🟠 MAJOR / 🟡 MEDIUM / 🟢 改善 / ⚪️ 任意

> ステータス: Phase 1–5 完了。バックエンド単体テスト 41 / E2E 7 = **48 green**、ruff クリーン、frontend `tsc --noEmit` クリーン、docker 実機で再検証済み。

## Phase 1 — Backend 正しさ（最優先）
- [x] 🔴 A1: 非同期ハンドラ内の同期埋め込みを `asyncio.to_thread` でオフロード（create/update/search、`embeddings.a*` ヘルパ）
- [x] 🟠 B1: 検索のベクトル渡しを `str()` から `Vector` 型バインド（`bindparam(type_=Vector(384))`）へ
- [x] 🟡 B5: fuzzy 検索を `title % :q`（GIN trgm 活用）+ `ORDER BY similarity`
- [x] 🟡 B6: `/health` は DB 障害時 503
- [x] 🟡 B4: `updated_at` を DBトリガに一本化（ORM onupdate 削除）
- [x] 🟠 A3: トランザクションをサービス層に集約（ルーターの commit を撤去）
- [x] 🟡 A4: `db.py` のエンジンを遅延生成（import 副作用を解消）
- [x] 🟢 A2: 埋め込みプロバイダを Protocol 化 + 埋め込みテキスト（`document_text`）を一元化

## Phase 2 — DB / API
- [x] 🔴 D1: category に CHECK 制約（migration 0002）+ 保存時 trim
- [x] 🟢 論理削除（`deleted_at`）+ 一覧/検索/取得で除外
- [x] 🟢 複合索引 `(category, published_at desc)` + 生存行の部分索引
- [x] 🟢 facets エンドポイント（`GET /api/articles/facets`）
- [x] 🟢 一覧に出版日レンジ絞り込み（published_from / published_to）

## Phase 3 — Frontend
- [x] 🔴 F1: 検索のデバウンス（300ms）
- [x] 🟡 F2: AbortController の signal を fetch に伝播（AbortError は無視）
- [x] 🟢 F5: 検索結果のクライアント側ページネーション（limit=50 取得 → 12件/頁）
- [x] 🟢 F6: 著者フィルタを facets 由来のセレクトに
- [x] 🟢 F3: `Icon` コンポーネント化（重複 SVG 解消）
- [x] ⚪️ F4: `globals.css` の line-clamp 重複定義を削除

## Phase 4 — チーム開発 / 品質
- [x] 🟢 CI（GitHub Actions: backend unit+ruff / frontend tsc+lint / integration は workflow_dispatch）
- [x] 🟢 テスト拡充（import 検証の純関数テスト 9 件 + E2E API テスト 7 件）
- [x] 🟢 lint 設定をコミット（ruff: `pyproject.toml`, prettier: `.prettierrc`）
- [x] 🟢 OpenAPI からの型生成スクリプト（`npm run gen:types`）
- [x] 🟢 `frontend/package-lock.json` をコミット
- [x] ⚪️ E2E テスト（`tests/test_api_e2e.py`、未起動時は自動 skip）

## Phase 5 — AI / ML
- [x] 🔴 AI1: クエリ埋め込みの LRU キャッシュ
- [x] 🔴 AI2: 精度評価ハーネス（`backend/eval/`：Recall@k / Precision@k / MRR / nDCG@k）
- [x] 🟡 AI3: ドキュメント埋め込みテキストの一元化（content に統一）

## 方針として「対応せず／文書化して見送り」とするもの（理由付き）
- ⚪️ 著者・カテゴリの完全なマスタテーブル正規化（FK）: 今回は CHECK 制約 + facets で実用上の表記ゆれ防止と選択肢提供を担保。完全な FK 正規化は影響範囲（ingest/import/検索/API）とリスクが大きく、別PRに切り出す。
- ⚪️ 検索用テーブルの分離（embedding/tsv を別テーブル）: レビューでも「deferred で対応済み」と評価。再インデックス容易性のメリットに対し再設計コストが大きいため見送り。
- ⚪️ content への trigram インデックス: 現状 title のみで要件充足。本文部分一致要件が出た時点で追加。
- ⚪️ AI4: 事前計算ベクトルの同梱: 初回起動の高速化策だが、実 CSV 差し替えの単純さとトレードオフ。起動は数分以内で許容範囲のため見送り。
