# Shopee AI Automation Suite – Living Specification

> **最終更新**: 2025-05-29  
> **編集ルール**:  
> - 大項目は `#`, 小項目は `##` / `###`  
> - 変更したら必ず `## 変更履歴` に1行追記  
> - “❓未決” と書かれた行は決まり次第消す

---

## 1. ビジョン & KPI
- **目的**: 東南アジア Shopee 店舗運営を AI でほぼ自動化  
- **長期ゴール**: 各国 5,000 品 × 最大 3 店舗  
- **KPI**:  
  1. 出品総数  
  2. Late-Shipment Rate ≤ 1 %  
  3. 月次利益 ___円  ←❓未決

---

## 2. システム全体構成図
┌─ブラウザダッシュボード (Streamlit/Next.js)────────────┐
│ ├─ASIN抽出 │ │
│ ├─出品数スケール │ AWS (Fargate) n8n │
│ ├─リスト編集 │◄────────┐ ↖︎cron │
│ ├─在庫+価格 │ │ │
│ ├─注文管理+仕入れ │ │ │
│ └─チャットツール │ │ │
└───────────────────────────────┘
│Shopee OpenAPI│Amazon SP-API│Keepa│LLM APIs

yaml
コピーする
編集する

---

## 3. モジュール別仕様

### 3.1 ASIN抽出 ⭐ **(開発中)**

| 項目 | 内容 |
|---|---|
| **目的** | 発送可能・需要確定の商品を初期登録 |
| **入力** | Market Lens 生成 Excel |
| **ロジック** | 1. ShippingTime ≤ 24h = A, 25-48h = B<br>2. 一致度 ≥ 50<br>3. NG ワード除外 |
| **出力** | `asin_candidates.xlsx` |
| **未決** | NG ワード追加 UI ❓ |

### 3.2 出品数スケール

#### 3.2.1 候補ASINリスト作成
- 重複チェック: central_registry.db
- Keepa Rank > 10,000 は除外  ←❓閾値要調整

#### 3.2.2 View/Sold 監視
- Shopee API `get_item_base_info`毎日実行 (n8n cron)

#### 3.2.3 重複チェック
- ASINキー + タイトル Embedding 距離 < 0.15

### 3.3 リスト編集ツール
*(略)*

*(以降、在庫管理・チャットツール等同様にセクション追加)*

---

## 4. 共通ライブラリ
- `shipping_rule.py` : ShippingTime 判定
- `duplicator.py` : ASIN/TITLE 重複
- `registry.db`    : 商品状態テーブル

---

## 5. 技術スタック & 外部サービス
| レイヤ | 採用 | メモ |
|-------|------|------|
| **フロント** | Streamlit (暫定) | Next.js に移行❓ |
| **バックエンド** | FastAPI | マイクロサービス分割予定 |
| **DB** | SQLite → Postgres (Phase-2) |
| **API** | Shopee Open Platform, Amazon SP-API, Keepa |
| **CI/CD** | GitHub Actions (Docker build & deploy) |

---

## 6. 未決事項リスト
- [ ] Keepa トークンプランを決める
- [ ] 出品数スケールの専門性スコア係数
- [ ] 在庫管理システムを自作か外部連携か

---

## 7. 変更履歴
| 日付 | 変更 | 版 |
|------|------|---|
| 2025-05-29 | initial draft | v0.1 |