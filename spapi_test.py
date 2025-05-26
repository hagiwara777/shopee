# 現在のファイルをバックアップ
cp modules/spapi_service.py modules/spapi_service_old.py

# 修正版を作成
cat > modules/spapi_service.py << 'EOF'
from sp_api.api import CatalogItems
from sp_api.base import Marketplaces, SellingApiException
import time
import os
from dotenv import load_dotenv

# 環境変数を確実に読み込み
load_dotenv()

def search_asin_by_title(jp_title, max_retries=3, delay=1):
    """
    日本語商品名でAmazon商品を検索してASINを取得
    
    Args:
        jp_title (str): 日本語商品名
        max_retries (int): 最大リトライ回数
        delay (float): リトライ間隔(秒)
    
    Returns:
        str: ASIN (見つからない場合は空文字)
    """
    if not jp_title or not jp_title.strip():
        return ""
    
    # 環境変数の確認とデバッグ
    lwa_app_id = os.getenv("LWA_APP_ID")
    lwa_client_secret = os.getenv("LWA_CLIENT_SECRET") 
    refresh_token = os.getenv("SP_API_REFRESH_TOKEN")
    
    # デバッグ用（一度だけ表示）
    if not hasattr(search_asin_by_title, "_debug_shown"):
        print(f"🔑 環境変数確認:")
        print(f"  LWA_APP_ID: {'設定済み' if lwa_app_id else '未設定'}")
        print(f"  LWA_CLIENT_SECRET: {'設定済み' if lwa_client_secret else '未設定'}")
        print(f"  SP_API_REFRESH_TOKEN: {'設定済み' if refresh_token else '未設定'}")
        search_asin_by_title._debug_shown = True
    
    if not all([lwa_app_id, lwa_client_secret, refresh_token]):
        print(f"❌ 環境変数が不足しています")
        return ""
    
    for attempt in range(max_retries):
        try:
            # 明示的に認証情報を設定
            credentials = {
                "lwa_app_id": lwa_app_id,
                "lwa_client_secret": lwa_client_secret,
                "refresh_token": refresh_token
            }
            
            # CatalogItems初期化（日本マーケットプレイス）
            catalog = CatalogItems(
                marketplace=Marketplaces.JP,
                credentials=credentials
            )
            
            # 商品検索実行
            result = catalog.search_catalog_items(
                keywords=jp_title.strip(),
                pageSize=5  # 上位5件を取得
            )
            
            # レスポンス解析
            if result.payload:
                # 辞書型レスポンスの場合
                if isinstance(result.payload, dict):
                    items = result.payload.get("items", [])
                # リスト型レスポンスの場合  
                elif isinstance(result.payload, list):
                    items = result.payload
                else:
                    print(f"予期しないレスポンス形式: {type(result.payload)}")
                    return ""
                
                # 最初の商品のASINを返す
                if items and len(items) > 0:
                    first_item = items[0]
                    asin = first_item.get("asin", "")
                    if asin:
                        print(f"ASIN検索成功: {jp_title[:30]}... → {asin}")
                        return asin
                
                # 商品が見つからない場合
                print(f"ASIN検索結果なし: {jp_title[:30]}...")
                return ""
            
            else:
                print(f"ASIN検索レスポンスなし: {jp_title[:30]}...")
                return ""
                
        except SellingApiException as e:
            print(f"SP-API エラー (試行{attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                return ""
                
        except Exception as e:
            print(f"ASIN検索エラー (試行{attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                return ""
    
    return ""

def search_multiple_asins(jp_titles, progress_callback=None):
    """
    複数の日本語商品名でASIN検索（進捗表示対応）
    
    Args:
        jp_titles (list): 日本語商品名のリスト
        progress_callback (callable): 進捗コールバック関数
    
    Returns:
        list: ASINのリスト
    """
    asins = []
    total = len(jp_titles)
    
    for i, title in enumerate(jp_titles):
        asin = search_asin_by_title(title)
        asins.append(asin)
        
        # 進捗表示
        if progress_callback:
            progress_callback(i + 1, total)
        elif i % 10 == 0:  # 10件ごとに進捗表示
            print(f"ASIN検索進捗: {i+1}/{total}")
    
    return asins

def test_sp_api_connection():
    """
    SP-API接続テスト用関数
    """
    print("🧪 SP-API接続テスト開始...")
    
    # 環境変数確認
    load_dotenv()
    lwa_app_id = os.getenv("LWA_APP_ID")
    lwa_client_secret = os.getenv("LWA_CLIENT_SECRET")
    refresh_token = os.getenv("SP_API_REFRESH_TOKEN")
    
    print(f"環境変数確認:")
    print(f"  LWA_APP_ID: {'✅' if lwa_app_id else '❌'}")
    print(f"  LWA_CLIENT_SECRET: {'✅' if lwa_client_secret else '❌'}")
    print(f"  SP_API_REFRESH_TOKEN: {'✅' if refresh_token else '❌'}")
    
    if not all([lwa_app_id, lwa_client_secret, refresh_token]):
        print("❌ 必要な環境変数が不足しています")
        return False
    
    # 実際の検索テスト
    test_result = search_asin_by_title("ファンケル マイルドクレンジングオイル")
    
    if test_result:
        print(f"✅ 接続テスト成功: ASIN={test_result}")
        return True
    else:
        print("❌ 接続テスト失敗")
        return False

if __name__ == "__main__":
    test_sp_api_connection()
EOF