import os
from dotenv import load_dotenv; load_dotenv()
from sp_api.api import CatalogItems
from sp_api.base import Marketplaces, SellingApiException
import backoff

# 日本マーケットプレイス指定
JP = Marketplaces.JP

# 資格情報ロード（.env経由）
credentials = dict(
    refresh_token=os.getenv("SPAPI_REFRESH_TOKEN"),
    lwa_app_id=os.getenv("SPAPI_LWA_APP_ID"),
    lwa_client_secret=os.getenv("SPAPI_LWA_CLIENT_SECRET"),
)

def _real_call(keywords, brand=None, page=1):
    """CatalogItems API 1回呼び出し（内部関数）"""
    kw_string = " ".join(keywords)
    params = {
        "keywords": kw_string,
        "marketplaceIds": [JP.marketplace_id],
        "pageSize": 20,
        "page": page,
    }
    if brand:
        params["brandNames"] = [brand]
    resp = CatalogItems(credentials=credentials, marketplace=JP).search_catalog_items(**params)
    return resp.payload.get("items", [])

@backoff.on_exception(backoff.expo,
                      (SellingApiException, ConnectionError),
                      max_tries=5, factor=2)
def search_amazon_catalog(keywords, brand=None):
    """
    keywords: 商品検索用ワードリスト
    brand: ブランド名（日本語名など）
    ⇒ 最適なASIN(文字列)を1件返す。見つからなければNone。
    """
    try:
        items = _real_call(keywords, brand, page=1)

        # -------------------- スコアリング --------------------
        kw_lower = [k.lower() for k in keywords if k]
        def score(item):
            attr = item.get("attributes", {})
            # attributesがない場合も安全
            title = attr.get("item_name", [""])[0].lower() if "item_name" in attr else ""
            brand_attr = attr.get("brand", [""])[0] if "brand" in attr else ""
            score = 0
            if brand and brand_attr == brand:
                score += 3
            if all(k in title for k in kw_lower):
                score += 2
            return score

        if not items:
            return None

        best = sorted(items, key=score, reverse=True)[0]
        return best["asin"]
    except SellingApiException as e:
        if hasattr(e, "status_code") and e.status_code == 429:
            print("Rate-Limit 429: backoff が自動リトライします")
            raise
        print("SP-API Error:", e)
        return None
    except Exception as e:
        print("❌ その他の例外:", e)
        return None

# ==================== 動作テスト用 ====================
if __name__ == "__main__":
    print("✅ CatalogItems クライアント初期化 OK")
    # テスト用データ例
    keywords = ["ミルボン", "シャンプー", "500ml"]
    brand = "ミルボン"
    asin = search_amazon_catalog(keywords, brand)
    print("🔍 取得結果 ASIN =", asin)
