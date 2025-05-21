"""
SP-API 資格情報が .env に入っているか確認し、
CatalogItems API でキーワード検索を 1 回実行してみる簡易テスト。
"""

import os
from dotenv import load_dotenv
from sp_api.api import CatalogItems
from sp_api.base import Marketplaces, SellingApiException

load_dotenv()  # .env を読み込む

creds = {
    "refresh_token":     os.getenv("SPAPI_REFRESH_TOKEN"),
    "lwa_app_id":        os.getenv("SPAPI_LWA_APP_ID"),
    "lwa_client_secret": os.getenv("SPAPI_LWA_CLIENT_SECRET"),
}

# 必須 3項目が無い場合は警告して終了
missing = [k for k, v in creds.items() if not v]
if missing:
    raise RuntimeError(f"環境変数が足りません: {', '.join(missing)}")

try:
    client = CatalogItems(credentials=creds, marketplace=Marketplaces.JP)
    print("✅ CatalogItems クライアント初期化 OK")

    # キーワード "テスト" で 1件だけ検索してみる
    resp = client.search_catalog_items(
        keywords="テスト",
        marketplaceIds=[Marketplaces.JP.marketplace_id],
        pageSize=1
    )
    items = resp.payload.get("items", [])
    if items:
        print("🔍 取得結果 ASIN =", items[0]["asin"])
        print("　　タイトル =", items[0]['attributes']["item_name"][0])
    else:
        print("⚠️ アイテムが返ってきませんでした")

except SellingApiException as e:
    print("❌ SellingApiException:", e.status_code, e.reason)
    print("body:", e.body)
except Exception as e:
    print("❌ その他の例外:", e)
