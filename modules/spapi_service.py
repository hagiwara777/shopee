# /modules/spapi_service.py (修正版 - testブロックのAttributeError修正)

import os
from dotenv import load_dotenv
from sp_api.api import CatalogItems
from sp_api.base import SellingApiException, Marketplaces, SellingApiForbiddenException
import traceback
import time

# .envファイルから環境変数を読み込む
load_dotenv()

# 認証情報を環境変数から取得
credentials = dict(
    refresh_token=os.getenv("SPAPI_REFRESH_TOKEN"),
    lwa_app_id=os.getenv("SPAPI_LWA_APP_ID"),
    lwa_client_secret=os.getenv("SPAPI_LWA_CLIENT_SECRET"),
)

# 日本マーケットプレイスを指定
try:
    marketplace = Marketplaces.JP # 日本の場合 .JP
except AttributeError:
    print("警告: Marketplaces.JP が見つかりません。ライブラリのバージョンを確認してください。")
    marketplace = None


def search_amazon_catalog(keywords: list, brand: str = None):
    """
    指定されたキーワードとブランドでAmazonカタログを検索し、
    条件に合う商品のASINなどを返す（※現在はダミー実装）。
    """
    print(f"SP-API: Searching for keywords={keywords}, brand={brand}")
    asin_list = []

    required_creds = ['refresh_token', 'lwa_app_id', 'lwa_client_secret']
    missing_creds = [cred for cred in required_creds if not credentials.get(cred)]
    if missing_creds:
        print(f"エラー: SP-APIの必須認証情報が .env ファイルに設定されていません: {', '.join(missing_creds)}")
        print(f"       プロジェクトルートの .env ファイルを確認してください。")
        return None

    if marketplace is None:
        print("エラー: マーケットプレイスが正しく設定されていません。")
        return None

    try:
        catalog_client = CatalogItems(credentials=credentials, marketplace=marketplace)
        print("SP-API クライアント初期化成功 (LWA)")

        # --- ここからAPI呼び出しと結果処理の実装 ---
        print("SP-API: Calling search_catalog_items...")
        search_params = {
            'keywords': keywords,
            'marketplaceIds': [marketplace.marketplace_id]
        }
        if brand:
            search_params['brandNames'] = [brand]
            print(f"  (Using brand filter: {brand})")

        # response = catalog_client.search_catalog_items(**search_params)
        # print("SP-API Response:", response.payload)

        # 現時点ではダミーの値を返す
        if keywords:
             print("SP-API: (Dummy response) Found ASIN B00TESTCODE")
             asin_list = ["B00TESTCODE"]
        # --- ここまでAPI呼び出しと結果処理の実装 ---

    except SellingApiForbiddenException as e:
        print("SP-API 権限エラー (403 Forbidden):"); print(f"  Message: {e}"); print(f"  Body: {e.body}")
        print("  考えられる原因: LWA Appロール未承認 / LWA認証情報無効 / NW設定")
    except SellingApiException as e:
        print(f"SP-API Error:"); print(f"  Status Code: {e.status_code}"); print(f"  Reason: {e.reason}"); print(f"  Body: {e.body}")
    except Exception as e:
        print(f"An unexpected error occurred during SP-API call or processing: {e}")
        traceback.print_exc()

    return asin_list[0] if asin_list else None


# モジュール単体でテストする場合のコード
if __name__ == '__main__':
    print("--- SP-API Service Module Test ---")
    print("Checking loaded credentials (partial):")
    print(f"  LWA App ID: {credentials.get('lwa_app_id')[:5] if credentials.get('lwa_app_id') else 'Not Set'}...")
    print(f"  LWA Client Secret: {'Set' if credentials.get('lwa_client_secret') else 'Not Set'}")
    print(f"  Refresh Token: {'Set' if credentials.get('refresh_token') else 'Not Set'}")

    if marketplace:
      print(f"  Marketplace ID: {marketplace.marketplace_id}")
      # print(f"  Marketplace Country: {marketplace.country_code}") # <- Error line removed/commented
      # marketplaceオブジェクトから取得できる他の情報を表示（例: endpoint）
      try:
          print(f"  Marketplace Endpoint: {marketplace.endpoint}")
      except AttributeError:
          print("  Marketplace Endpoint: (Attribute not found)") # endpoint属性もない場合に備える
    else:
      print("  Marketplace: Not Set")

    print("\nRunning dummy search test...")
    test_asin = search_amazon_catalog(keywords=["テスト", "商品"], brand="テストブランド")
    print(f"\nTest Search Result (ASIN): {test_asin}")
    print("--- Test End ---")