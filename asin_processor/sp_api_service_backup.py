# sp_api_service.py - Prime+出品者情報取得実装（既存機能に追加）

import time
import re
from sp_api.api import CatalogItems
from sp_api.base import Marketplaces

def get_prime_and_seller_info(asin, credentials):
    """
    ASINからPrime状態と出品者情報を取得（Shopee出品特化）
    """
    try:
        catalog_api = CatalogItems(
            credentials=credentials,
            marketplace=Marketplaces.JP
        )
        
        # 詳細商品情報を取得
        response = catalog_api.get_catalog_item(
            asin=asin,
            marketplaceIds=[Marketplaces.JP.marketplace_id],
            includedData=[
                'summaries',
                'attributes', 
                'offers',
                'images'
            ]
        )
        
        if not response.payload:
            return {
                'asin': asin,
                'is_prime': False,
                'seller_name': 'Unknown',
                'seller_type': 'unknown',
                'is_amazon_seller': False,
                'is_official_seller': False,
                'prime_status': 'データ取得失敗'
            }
        
        item_data = response.payload
        
        # Prime情報と出品者情報を抽出
        prime_seller_info = extract_prime_seller_details(item_data, asin)
        
        return prime_seller_info
        
    except Exception as e:
        print(f"❌ Prime+出品者情報取得エラー ({asin}): {str(e)[:100]}...")
        return {
            'asin': asin,
            'is_prime': False,
            'seller_name': 'エラー',
            'seller_type': 'error',
            'is_amazon_seller': False,
            'is_official_seller': False,
            'prime_status': f'エラー: {str(e)[:50]}...'
        }

def extract_prime_seller_details(item_data, asin):
    """
    商品データからPrime・出品者詳細情報を抽出
    """
    result = {
        'asin': asin,
        'is_prime': False,
        'seller_name': 'Unknown',
        'seller_type': 'unknown',
        'is_amazon_seller': False,
        'is_official_seller': False,
        'prime_status': '情報なし',
        'brand_name': '',
        'product_title': ''
    }
    
    # 基本商品情報
    if 'summaries' in item_data and item_data['summaries']:
        summary = item_data['summaries'][0]
        result['product_title'] = summary.get('itemName', '')
        result['brand_name'] = summary.get('brand', '')
    
    # オファー情報からPrime状態と出品者を確認
    if 'offers' in item_data and item_data['offers']:
        main_offer = item_data['offers'][0]  # メインオファー（通常は最も条件の良いもの）
        
        # Prime判定
        prime_detected = detect_prime_status(main_offer)
        result['is_prime'] = prime_detected['is_prime']
        result['prime_status'] = prime_detected['status_detail']
        
        # 出品者情報抽出
        seller_info = extract_seller_information(main_offer, result['brand_name'])
        result.update(seller_info)
    
    return result

def detect_prime_status(offer_data):
    """
    オファーデータからPrime状態を検出
    """
    prime_indicators = {
        'is_prime': False,
        'status_detail': '非Prime'
    }
    
    try:
        # 方法1: primeInformation直接確認
        if 'primeInformation' in offer_data:
            prime_info = offer_data['primeInformation']
            if prime_info.get('isPrime', False):
                prime_indicators['is_prime'] = True
                prime_indicators['status_detail'] = 'Prime対応'
                return prime_indicators
        
        # 方法2: deliveryInfo内のPrime情報確認  
        if 'deliveryInfo' in offer_data:
            delivery = offer_data['deliveryInfo']
            if isinstance(delivery, dict):
                # 配送オプションからPrime判定
                if 'isPrimeMember' in delivery or 'primeEligible' in delivery:
                    prime_indicators['is_prime'] = True
                    prime_indicators['status_detail'] = 'Prime対応'
                    return prime_indicators
        
        # 方法3: 配送情報のテキスト解析
        if 'shippingCharges' in offer_data:
            shipping = offer_data['shippingCharges']
            if isinstance(shipping, list) and len(shipping) > 0:
                shipping_text = str(shipping[0]).lower()
                if 'prime' in shipping_text or '無料' in shipping_text:
                    prime_indicators['is_prime'] = True
                    prime_indicators['status_detail'] = 'Prime推定'
                    return prime_indicators
        
        # 方法4: その他の配送関連情報
        delivery_related_fields = ['fulfillmentChannel', 'shippingTime', 'availability']
        for field in delivery_related_fields:
            if field in offer_data:
                field_value = str(offer_data[field]).lower()
                if 'amazon' in field_value or 'prime' in field_value:
                    prime_indicators['is_prime'] = True
                    prime_indicators['status_detail'] = 'Prime推定（配送情報）'
                    return prime_indicators
        
        prime_indicators['status_detail'] = '非Prime確認'
        
    except Exception as e:
        prime_indicators['status_detail'] = f'Prime判定エラー: {str(e)[:30]}...'
    
    return prime_indicators

def extract_seller_information(offer_data, brand_name):
    """
    出品者情報を抽出・分析
    """
    seller_info = {
        'seller_name': 'Unknown',
        'seller_type': 'unknown',
        'is_amazon_seller': False,
        'is_official_seller': False
    }
    
    try:
        # 出品者名の取得
        seller_name = 'Unknown'
        
        # 方法1: merchantInfo から取得
        if 'merchantInfo' in offer_data:
            merchant = offer_data['merchantInfo']
            if isinstance(merchant, dict):
                seller_name = merchant.get('name', merchant.get('merchantName', 'Unknown'))
        
        # 方法2: その他のフィールドから取得
        if seller_name == 'Unknown':
            seller_fields = ['sellerName', 'merchant', 'seller', 'soldBy']
            for field in seller_fields:
                if field in offer_data and offer_data[field]:
                    seller_name = str(offer_data[field])
                    break
        
        seller_info['seller_name'] = seller_name
        
        # Amazon出品者判定
        amazon_indicators = [
            'amazon', 'amazon.co.jp', 'amazon japan', 'amazon.com',
            'アマゾン', 'amazon jp', 'amazon inc'
        ]
        
        seller_name_lower = seller_name.lower()
        is_amazon = any(indicator in seller_name_lower for indicator in amazon_indicators)
        seller_info['is_amazon_seller'] = is_amazon
        
        # 公式メーカー判定
        is_official = False
        if brand_name and len(brand_name) > 2:
            is_official = check_official_manufacturer(seller_name, brand_name)
        
        seller_info['is_official_seller'] = is_official
        
        # 出品者タイプの決定
        if is_amazon:
            seller_info['seller_type'] = 'amazon'
        elif is_official:
            seller_info['seller_type'] = 'official_manufacturer'
        else:
            seller_info['seller_type'] = 'third_party'
        
    except Exception as e:
        seller_info['seller_name'] = f'エラー: {str(e)[:30]}...'
        seller_info['seller_type'] = 'error'
    
    return seller_info

def check_official_manufacturer(seller_name, brand_name):
    """
    公式メーカー判定ロジック
    """
    if not seller_name or not brand_name:
        return False
    
    seller_lower = seller_name.lower().strip()
    brand_lower = brand_name.lower().strip()
    
    # 完全一致チェック
    if seller_lower == brand_lower:
        return True
    
    # ブランド名が出品者名に含まれているかチェック
    if brand_lower in seller_lower or seller_lower in brand_lower:
        return True
    
    # 単語レベルでの一致チェック
    seller_words = set(re.findall(r'\w+', seller_lower))
    brand_words = set(re.findall(r'\w+', brand_lower))
    
    if brand_words and seller_words:
        # 共通単語の割合
        common_words = seller_words & brand_words
        brand_coverage = len(common_words) / len(brand_words)
        
        # 50%以上の単語が一致すれば公式とみなす
        if brand_coverage >= 0.5:
            return True
    
    # 日本語ブランド特有のチェック
    japanese_brand_patterns = [
        (brand_lower.replace(' ', ''), seller_lower.replace(' ', '')),
        (brand_lower.replace('-', ''), seller_lower.replace('-', '')),
    ]
    
    for brand_pattern, seller_pattern in japanese_brand_patterns:
        if brand_pattern in seller_pattern or seller_pattern in brand_pattern:
            return True
    
    return False

def enhanced_search_with_prime_seller(title, credentials):
    """
    Prime+出品者情報込みの拡張ASIN検索
    """
    print(f"🔍 Prime+出品者情報込み検索: {title[:50]}...")
    
    # 基本のASIN検索実行
    basic_result = search_asin_with_prime_priority(title, credentials)
    
    if basic_result.get("search_status") == "success":
        asin = basic_result.get('asin') or basic_result.get('amazon_asin')
        
        if asin:
            # Prime+出品者情報を追加取得
            print(f"   📊 Prime+出品者詳細分析: {asin}")
            prime_seller_info = get_prime_and_seller_info(asin, credentials)
            
            # 結果統合
            basic_result.update(prime_seller_info)
            
            # Shopee出品適性スコア計算
            shopee_score = calculate_shopee_suitability_score(basic_result)
            basic_result['shopee_suitability_score'] = shopee_score
            
            # 最終グループ判定
            shopee_group = determine_final_shopee_group(basic_result)
            basic_result['shopee_group'] = shopee_group
            
            print(f"   ✅ Prime: {basic_result['is_prime']} | 出品者: {basic_result['seller_type']} | Shopee適性: {shopee_score}点 | グループ: {shopee_group}")
    
    return basic_result

def calculate_shopee_suitability_score(product_info):
    """
    Shopee出品適性スコア計算（100点満点）
    Prime(50) + 出品者(30) + 一致度(20)
    """
    score = 0
    
    # Prime評価（50点満点）
    if product_info.get('is_prime', False):
        score += 50
    
    # 出品者評価（30点満点）
    seller_type = product_info.get('seller_type', 'unknown')
    if seller_type == 'amazon':
        score += 30
    elif seller_type == 'official_manufacturer':
        score += 25
    elif seller_type == 'third_party':
        score += 10
    # unknown/errorは0点
    
    # 一致度評価（20点満点）
    relevance_score = product_info.get('relevance_score', 0)
    score += min(relevance_score * 0.2, 20)
    
    return min(int(score), 100)

def determine_final_shopee_group(product_info):
    """
    最終的なShopeeグループ判定
    """
    is_prime = product_info.get('is_prime', False)
    seller_type = product_info.get('seller_type', 'unknown')
    relevance_score = product_info.get('relevance_score', 0)
    asin = product_info.get('asin') or product_info.get('amazon_asin')
    
    # ASIN無しは除外
    if not asin or asin == '':
        return 'X'
    
    # Prime + Amazon/公式メーカー = グループA（最優秀）
    if is_prime and seller_type in ['amazon', 'official_manufacturer']:
        return 'A'
    
    # Prime + サードパーティ = グループB（良好）
    elif is_prime and seller_type == 'third_party':
        return 'B'
    
    # 非Prime（一致度で細分化）
    elif not is_prime:
        if relevance_score >= 70:
            return 'C'  # 非Prime高一致度
        else:
            return 'X'  # 非Prime低一致度（除外）
    
    # その他（エラーなど）
    else:
        return 'X'

# 既存の search_asin_with_prime_priority 関数に統合する修正版
def search_asin_with_enhanced_prime_seller(title, credentials, max_results=5):
    """
    Prime+出品者情報統合版ASIN検索
    """
    japanese_title = process_title_with_hybrid_llm(title)
    
    if not japanese_title or japanese_title == title:
        print(f"   ⚠️ 日本語化スキップ: {title}")
        japanese_title = title
    else:
        print(f"   ✅ 日本語化完了: {japanese_title}")
    
    try:
        catalog_api = CatalogItems(
            credentials=credentials,
            marketplace=Marketplaces.JP
        )
        
        response = catalog_api.search_catalog_items(
            keywords=japanese_title,
            pageSize=max_results,
            marketplaceIds=[Marketplaces.JP.marketplace_id]
        )
        
        if response.payload and 'items' in response.payload:
            items = response.payload['items']
            
            if items:
                best_item = items[0]  # 最初のアイテムを選択
                asin = best_item.get('asin')
                
                if asin:
                    # 基本情報
                    basic_info = {
                        'search_status': 'success',
                        'asin': asin,
                        'amazon_asin': asin,
                        'amazon_title': best_item.get('summaries', [{}])[0].get('itemName', ''),
                        'amazon_brand': best_item.get('summaries', [{}])[0].get('brand', ''),
                        'japanese_name': japanese_title,
                        'llm_source': 'GPT-4o'  # または使用したLLM
                    }
                    
                    # 一致度計算
                    relevance_score = calculate_enhanced_relevance_score(
                        title, basic_info['amazon_title'], basic_info['amazon_brand']
                    )
                    basic_info['relevance_score'] = relevance_score
                    
                    # Prime+出品者情報取得
                    prime_seller_info = get_prime_and_seller_info(asin, credentials)
                    basic_info.update(prime_seller_info)
                    
                    # Shopee適性評価
                    shopee_score = calculate_shopee_suitability_score(basic_info)
                    shopee_group = determine_final_shopee_group(basic_info)
                    
                    basic_info.update({
                        'shopee_suitability_score': shopee_score,
                        'shopee_group': shopee_group
                    })
                    
                    return basic_info
        
        return {
            'search_status': 'no_results',
            'asin': '',
            'amazon_asin': '',
            'japanese_name': japanese_title,
            'error_message': '検索結果なし'
        }
        
    except Exception as e:
        return {
            'search_status': 'error',
            'asin': '',
            'amazon_asin': '',
            'japanese_name': japanese_title,
            'error_message': str(e)
        }

# デバッグ・テスト用関数
def test_prime_seller_detection(test_asins):
    """
    Prime+出品者検出機能のテスト
    """
    credentials = get_credentials()
    if not credentials:
        print("❌ 認証情報が設定されていません")
        return
    
    print("🧪 Prime+出品者検出テスト開始")
    
    for asin in test_asins:
        print(f"\n🔍 テスト対象: {asin}")
        result = get_prime_and_seller_info(asin, credentials)
        
        print(f"   Prime状態: {result['is_prime']} ({result['prime_status']})")
        print(f"   出品者名: {result['seller_name']}")
        print(f"   出品者タイプ: {result['seller_type']}")
        print(f"   Amazon出品者: {result['is_amazon_seller']}")
        print(f"   公式メーカー: {result['is_official_seller']}")
        
        time.sleep(1)  # API制限対策
    
    print("\n✅ Prime+出品者検出テスト完了")

# 統合テスト
if __name__ == "__main__":
    # テスト用ASIN（実際のASINに置き換えてください）
    test_asins = [
        "B07SXD81XN",  # 無印良品の商品
        "B09J53D9LV",  # ファンケルの商品  
        "B0B8XYZ123"   # その他のテスト用ASIN
    ]
    
    test_prime_seller_detection(test_asins)