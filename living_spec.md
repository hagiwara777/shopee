# Shopee AI Automation Suite – Living Specification

> **最終更新**: 2025-05-29  
> **編集ルール**:  
> - 大項目は `#`, 小項目は `##` / `###`  
> - 変更したら必ず `## 変更履歴` に1行追記  
> - "❓未決" と書かれた行は決まり次第消す

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
```
┌─ブラウザダッシュボード (Streamlit/Next.js)────────────┐
│ ├─ASIN抽出                    │                    │
│ ├─出品数スケール              │  AWS (Fargate) n8n │
│ ├─リスト編集                  │◄────────┐    ↖︎cron │
│ ├─在庫+価格                   │         │         │
│ ├─注文管理+仕入れ              │         │         │
│ └─チャットツール               │         │         │
└───────────────────────────────┘         │
           │Shopee OpenAPI│Amazon SP-API│Keepa│LLM APIs
```

---

## 3. モジュール別仕様

### 3.1 ASIN抽出 ⭐ **(開発中)**

| 項目 | 内容 |
|---|---|
| **目的** | 発送可能・需要確定の商品を初期登録 |
| **入力** | Market Lens 生成 Excel |
| **分類基準** | **ShippingTime最優先システム v7** |
| **ロジック** | 1. **ShippingTime ≤ 24h = A（即座出品）**<br>2. **それ以外 = B（在庫管理制御）**<br>3. NG ワード除外 |
| **UI表示** | **A**: "24時間以内発送 - DTS規約クリア確実"<br>**B**: "Aの条件外は全部ここ（後の有在庫候補）" |
| **出力** | `asin_candidates.xlsx` |
| **戦略転換** | Prime重視 → ShippingTime最優先（Shopee DTS規約準拠） |

#### 3.1.1 ShippingTime取得・分類システム
- **API設定**: `includedData="ShippingTime"` 必須指定
- **取得率**: 80-90% 目標（10-20%欠損想定）
- **フォールバック**: 取得不可時はPrime情報で代替
- **分類関数**: `shopee_classify_shipping_simple()`

#### 3.1.2 在庫管理ツール連携
- **目的**: B グループ商品の出品制御
- **連携機能**: "自己発送の即日発送のみ在庫あり"ボタン
- **効果**: セール時遅延対策、リスク管理の自動化
- **親和性**: ShippingTime戦略と完全連携

#### 3.1.3 監視・分析機能  
- **ShippingTime取得率監視**: リアルタイム表示
- **カテゴリ別分析**: 出品者タイプ・商品カテゴリ別取得率
- **フォールバック統計**: Prime/FBA代替処理の成功率
- **改良計画**: バッチAPI活用、リトライ処理（Phase2）

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
- `shipping_rule.py` : **ShippingTime最優先判定**
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
| **LLM** | OpenAI GPT-4o, Google Gemini | 日本語化・分析用 |
| **CI/CD** | GitHub Actions (Docker build & deploy) |

---

## 6. 未決事項リスト
- [x] **ASIN抽出分類基準** → **2グループ制確定（ShippingTime ≤ 24h基準）**
- [x] **戦略方針** → **ShippingTime最優先システム確定**
- [ ] 一致度閾値の微調整（現在≥50）
- [ ] Keepa トークンプランを決める
- [ ] 出品数スケールの専門性スコア係数
- [ ] ShippingTime取得率向上策の段階的実装
- [ ] 在庫管理システムを自作か外部連携か

---

## 7. 実装フェーズ計画

### Phase 1 (即座実行)
- [x] 戦略確定: ShippingTime最優先システム
- [ ] 2グループ分類実装（A: ≤24h / B: それ以外）
- [ ] ShippingTime取得機能追加
- [ ] UI更新（2タブ表示）
- [ ] 基本監視機能

### Phase 2 (1-2週間後)
- [ ] ShippingTime取得率向上（バッチAPI・リトライ）
- [ ] 詳細分析・監視機能
- [ ] カテゴリ別しきい値調整
- [ ] 在庫管理ツール完全連携

### Phase 3 (将来)
- [ ] ML予測による欠損データ補完
- [ ] 需要予測との統合最適化

---

## 8. 変更履歴
| 日付 | 変更 | 版 |
|------|------|---|
| 2025-05-29 | initial draft | v0.1 |
| 2025-05-29 | **ShippingTime最優先システム反映、2グループ分類確定** | **v0.2** |