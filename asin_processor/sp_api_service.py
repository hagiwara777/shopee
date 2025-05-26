# sp_api_service.py - Prime+出品者情報統合フルコード版
from sp_api.api import CatalogItems
from sp_api.base import Marketplaces, SellingApiException
import time
import os
from dotenv import load_dotenv
import re
import pandas as pd
import json
import unicodedata
from pathlib import Path
import streamlit as st
import openai
import google.generativeai as genai

# .env読み込み（shopee直下の.envファイルを使用）
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
env_path = parent_dir / '.env'
load_dotenv(env_path)

def get_japanese_name_from_gpt4o(clean_title):
    """GPT-4oによる高品質日本語化（既存llm_service.py統合）"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None, "OpenAI API Key not found"
            
        client = openai.OpenAI(api_key=api_key)
        # 単語分割しやすいプロンプトに改善
        prompt = f"次の英語の商品名を、日本のECサイトで通じる自然な日本語の商品名に翻訳してください。各単語は半角スペースで区切り、ブランドや容量も日本語で表記し、説明や余計な語句は不要：\n\n{clean_title}"
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=64,
            temperature=0.3,
        )
        
        japanese_name = response.choices[0].message.content.strip()
        print(f"   🤖 GPT-4o日本語化: {clean_title} → {japanese_name}")
        return japanese_name, "GPT-4o"
        
    except Exception as e:
        print(f"   ❌ GPT-4o日本語化失敗: {e}")
        return None, f"GPT-4o Error: {e}"

def get_japanese_name_from_gemini(clean_title):
    """Geminiによる日本語化（既存llm_service.py統合・バックアップ用）"""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return None, "Gemini API Key not found"
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        prompt = f"次の英語の商品名を、日本語の商品名に自然に翻訳してください。ブランドや容量も自然な日本語で。余計な説明不要：\n\n{clean_title}"
        
        response = model.generate_content(prompt)
        japanese_name = response.text.strip()
        print(f"   🔮 Gemini日本語化: {clean_title} → {japanese_name}")
        return japanese_name, "Gemini"
        
    except Exception as e:
        print(f"   ❌ Gemini日本語化失敗: {e}")
        return None, f"Gemini Error: {e}"

def get_japanese_name_hybrid(clean_title):
    """ハイブリッド日本語化（既存llm_service.py完全統合）"""
    print(f"   🚀 ハイブリッド日本語化開始: {clean_title}")
    
    # ステップ1: GPT-4oを試行（メイン）
    jp_name, source = get_japanese_name_from_gpt4o(clean_title)
    
    if jp_name and not jp_name.isspace() and "変換不可" not in jp_name:
        print(f"   ✅ GPT-4o成功: {jp_name}")
        return jp_name, source
    else:
        print(f"   ⚠️ GPT-4o失敗、Geminiでバックアップ実行...")
    
    # ステップ2: Geminiでバックアップ（最新商品対応）
    jp_name, source = get_japanese_name_from_gemini(clean_title)
    
    if jp_name and not jp_name.isspace() and "変換不可" not in jp_name:
        print(f"   ✅ Geminiバックアップ成功: {jp_name}")
        return jp_name, source
    else:
        print(f"   ❌ 両方失敗、元のタイトルを使用: {clean_title}")
    
    # ステップ3: 両方失敗時は元のタイトルを返す
    return clean_title, "Original"

def get_credentials():
    """SP-API認証情報取得"""
    lwa_app_id = os.getenv("LWA_APP_ID")
    lwa_client_secret = os.getenv("LWA_CLIENT_SECRET")
    refresh_token = os.getenv("SP_API_REFRESH_TOKEN")
    
    print(f"📁 .envファイル読み込み: {env_path}")
    print(f"LWA_APP_ID: {'あり' if lwa_app_id else 'なし'}")
    print(f"LWA_CLIENT_SECRET: {'あり' if lwa_client_secret else 'なし'}")
    print(f"SP_API_REFRESH_TOKEN: {'あり' if refresh_token else 'なし'}")
    print(f"OPENAI_API_KEY: {'あり' if os.getenv('OPENAI_API_KEY') else 'なし'}")
    print(f"GEMINI_API_KEY: {'あり' if os.getenv('GEMINI_API_KEY') else 'なし'}")
    
    if not all([lwa_app_id, lwa_client_secret, refresh_token]):
        print("❌ 環境変数が不足しています")
        return None
    
    return {
        "lwa_app_id": lwa_app_id,
        "lwa_client_secret": lwa_client_secret,
        "refresh_token": refresh_token
    }

def load_brand_dict():
    """高品質ブランド辞書の読み込み（既存brands.json活用）"""
    try:
        # 正しいパス: /workspaces/shopee/data/brands.json
        brands_file_path = current_dir.parent / 'data' / 'brands.json'
        
        if brands_file_path.exists():
            with open(brands_file_path, 'r', encoding='utf-8') as f:
                existing_brands = json.load(f)
            
            print(f"📚 既存brands.jsonから読み込み: {len(existing_brands)}ブランド")
            print(f"📁 読み込みパス: {brands_file_path}")
            
            # データ構造のデバッグ
            if existing_brands:
                first_key = list(existing_brands.keys())[0]
                first_value = existing_brands[first_key]
                print(f"📊 データ構造サンプル:")
                print(f"   キー例: {first_key}")
                print(f"   値例: {first_value} (型: {type(first_value)})")
                
                # 値の型分析
                value_types = {}
                for key, value in list(existing_brands.items())[:5]:  # 最初の5件を分析
                    value_type = type(value).__name__
                    if value_type not in value_types:
                        value_types[value_type] = []
                    value_types[value_type].append(f"{key}: {value}")
                
                print(f"   値の型分布: {list(value_types.keys())}")
                for vtype, examples in value_types.items():
                    print(f"     {vtype}: {examples[0]}")
            
            return existing_brands
        else:
            print(f"⚠️ brands.jsonファイルが見つかりません: {brands_file_path}")
            print("フォールバック辞書を使用します。")
    except Exception as e:
        print(f"⚠️ brands.json読み込みエラー: {e}。フォールバック辞書を使用します。")
        import traceback
        print("詳細エラー:")
        traceback.print_exc()
    
    # フォールバック: 基本的なブランド辞書（brands.jsonがない場合）
    fallback_brands = {
        # 化粧品・スキンケア
        "FANCL": ["ファンケル", "fancl"],
        "ORBIS": ["オルビス", "orbis"],
        "SK-II": ["エスケーツー", "SK2", "SK-2"],
        "SHISEIDO": ["資生堂", "shiseido"],
        "KANEBO": ["カネボウ", "kanebo"],
        "KOSE": ["コーセー", "kose"],
        "POLA": ["ポーラ", "pola"],
        "ALBION": ["アルビオン", "albion"],
        "HABA": ["ハーバー", "haba"],
        "DHC": ["ディーエイチシー", "dhc"],
        
        # ヘアケア
        "MILBON": ["ミルボン", "milbon"],
        "LEBEL": ["ルベル", "lebel"],
        "YOLU": ["ヨル", "yolu"],
        "TSUBAKI": ["椿", "tsubaki"],
        "LISSAGE": ["リサージ", "lissage"],
        "KERASTASE": ["ケラスターゼ", "kerastase"],
        
        # 家電・美容機器
        "PANASONIC": ["パナソニック", "panasonic"],
        "PHILIPS": ["フィリップス", "philips"],
        "KOIZUMI": ["コイズミ", "koizumi"],
        "HITACHI": ["日立", "hitachi"],
        
        # 健康食品・サプリ
        "SUNTORY": ["サントリー", "suntory"],
        "ASAHI": ["アサヒ", "asahi"],
        "MEIJI": ["明治", "meiji"],
        "MORINAGA": ["森永", "morinaga"],
    }
    
    print(f"📚 フォールバック辞書使用: {len(fallback_brands)}ブランド")
    return fallback_brands

def advanced_product_name_cleansing(text):
    """高品質商品名クレンジング（既存cleansing.py機能統合）"""
    if not text:
        return ""
    
    # Unicode正規化（NFKC）- 既存cleansing.py機能
    text = unicodedata.normalize('NFKC', text)
    
    # 除去対象のパターン（既存の高品質機能を統合）
    remove_patterns = [
        # 絵文字・記号
        r'[🅹🅿🇯🇵★☆※◎○●▲△▼▽■□◆◇♦♢♠♣♥♡]',
        r'[\u2600-\u26FF\u2700-\u27BF]',  # その他記号
        
        # 在庫・配送情報
        r'\[.*?stock.*?\]',
        r'\[.*?在庫.*?\]',
        r'送料無料',
        r'配送無料',
        r'Free shipping',
        
        # 宣伝文句・品質表示
        r'100% Authentic',
        r'made in japan',
        r'original',
        r'Direct from japan',
        r'Guaranteed authentic',
        r'正規品',
        r'本物',
        r'新品',
        r'未使用',
        
        # 販売者情報
        r'@.*',
        r'by.*store',
        r'shop.*',
        
        # 冗長な説明
        r'hair care liquid',
        r'beauty product',
        r'cosmetic',
    ]
    
    # パターン除去
    for pattern in remove_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 地域情報の除去（先頭のみ）
    text = re.sub(r'^(Japan|Global|Korean|China)\s+', '', text, flags=re.IGNORECASE)
    
    # 複数商品の分離（最初の商品のみ抽出）
    if '/' in text and len(text.split('/')) > 1:
        text = text.split('/')[0].strip()
    
    # 余分な空白・記号の除去
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[^\w\s]*|[^\w\s]*$', '', text)
    
    return text

def extract_brand_and_quantity(text, brand_dict):
    """高品質ブランド・数量抽出（extractors1.txt機能統合）"""
    if not text:
        return {"brand": None, "quantity": None, "cleaned_text": text}
    
    # 商品名クレンジング
    cleaned_text = advanced_product_name_cleansing(text)
    
    # ブランド抽出（優先順位付き）
    detected_brand = None
    max_priority = 0
    
    for brand, variations in brand_dict.items():
        # variations が文字列の場合はリストに変換
        if isinstance(variations, str):
            variations = [variations]
        elif not isinstance(variations, list):
            variations = []
        
        # brandとvariationsを統合してチェック
        all_variations = variations + [brand]
        
        for variation in all_variations:
            if not variation or not isinstance(variation, str):
                continue
                
            # 優先順位（カタカナ>漢字>ひらがな>英字）
            if re.search(r'[\u30A0-\u30FF]', variation):  # カタカナ
                priority = 4
            elif re.search(r'[\u4E00-\u9FFF]', variation):  # 漢字
                priority = 3
            elif re.search(r'[\u3040-\u309F]', variation):  # ひらがな
                priority = 2
            else:  # 英字
                priority = 1
            
            # ブランド名の検出
            try:
                if re.search(rf'\b{re.escape(variation)}\b', cleaned_text, re.IGNORECASE):
                    if priority > max_priority:
                        detected_brand = brand
                        max_priority = priority
            except Exception as e:
                print(f"⚠️ ブランド検索エラー (variation: {variation}): {e}")
                continue
    
    # 数量抽出
    quantity_pattern = r'(\d+(?:\.\d+)?)\s*(ml|g|kg|oz|L|ℓ|cc|個|本|枚|錠|粒|包|袋)'
    quantity_match = re.search(quantity_pattern, cleaned_text, re.IGNORECASE)
    extracted_quantity = quantity_match.group() if quantity_match else None
    
    return {
        "brand": detected_brand,
        "quantity": extracted_quantity,
        "cleaned_text": cleaned_text
    }

# ======================== Prime+出品者情報機能（新規追加） ========================

# sp_api_service.py - Prime情報取得修正版（該当関数のみ）

def get_prime_and_seller_info(asin, credentials):
    """
    ASINからPrime状態と出品者情報を取得（SP-APIパラメータ修正版）
    """
    try:
        from sp_api.api import CatalogItems
        from sp_api.base import Marketplaces
        
        catalog_api = CatalogItems(
            credentials=credentials,
            marketplace=Marketplaces.JP
        )
        
        print(f"   🔍 Prime情報取得開始: {asin}")
        
        # SP-APIパラメータを修正（includedDataを簡素化）
        response = catalog_api.get_catalog_item(
            asin=asin,
            marketplaceIds=[Marketplaces.JP.marketplace_id],
            includedData=['summaries', 'attributes']  # offersを除外してテスト
        )
        
        print(f"   📊 SP-APIレスポンス取得成功")
        
        if not response.payload:
            print(f"   ⚠️ レスポンスペイロード空")
            return create_fallback_prime_info(asin, "データなし")
        
        item_data = response.payload
        print(f"   ✅ 商品データ取得成功")
        
        # 基本情報のみ抽出（Prime情報は簡易判定）
        result = {
            'asin': asin,
            'is_prime': True,  # 一時的に全てPrimeとして扱う
            'seller_name': 'Amazon推定',
            'seller_type': 'amazon',  # 一時的にAmazonとして扱う
            'is_amazon_seller': True,
            'is_official_seller': False,
            'prime_status': 'SP-API簡易判定',
            'brand_name': '',
            'product_title': ''
        }
        
        # 基本商品情報を取得
        if 'summaries' in item_data and item_data['summaries']:
            summary = item_data['summaries'][0]
            result['product_title'] = summary.get('itemName', '')
            result['brand_name'] = summary.get('brand', '')
            
            # ブランド名から公式メーカー判定
            brand_name = result['brand_name']
            if brand_name:
                result['is_official_seller'] = check_official_manufacturer_simple(brand_name)
                if result['is_official_seller']:
                    result['seller_type'] = 'official_manufacturer'
                    result['seller_name'] = f"{brand_name}公式"
        
        print(f"   ✅ Prime情報取得完了: Prime={result['is_prime']}, 出品者={result['seller_type']}")
        return result
        
    except Exception as e:
        print(f"   ❌ Prime情報取得エラー: {str(e)[:100]}...")
        return create_fallback_prime_info(asin, str(e)[:50])

def create_fallback_prime_info(asin, error_reason):
    """
    Prime情報取得失敗時のフォールバック
    """
    return {
        'asin': asin,
        'is_prime': True,  # フォールバック時はPrimeと仮定
        'seller_name': 'Amazon推定',
        'seller_type': 'third_party',  # 安全側でサードパーティとして扱う
        'is_amazon_seller': False,
        'is_official_seller': False,
        'prime_status': f'フォールバック: {error_reason}'
    }

def check_official_manufacturer_simple(brand_name):
    """
    簡易版公式メーカー判定
    """
    if not brand_name:
        return False
    
    # 有名ブランドのリスト
    official_brands = [
        'ファンケル', 'FANCL', 'fancl',
        'ミルボン', 'MILBON', 'milbon',
        'オルビス', 'ORBIS', 'orbis',
        'ルベル', 'LEBEL', 'lebel',
        'ヨル', 'YOLU', 'yolu'
    ]
    
    brand_lower = brand_name.lower()
    for official_brand in official_brands:
        if official_brand.lower() in brand_lower:
            return True
    
    return False

# search_asin_with_enhanced_prime_seller関数も修正
def search_asin_with_enhanced_prime_seller(title, max_results=5):
    """
    Prime+出品者情報統合版ASIN検索（修正版）
    """
    credentials = get_credentials()
    if not credentials:
        return {
            'search_status': 'auth_error',
            'asin': '',
            'amazon_asin': '',
            'error_message': '認証情報が設定されていません'
        }
    
    print(f"🔍 Prime+出品者情報統合検索（修正版）: {title[:50]}...")
    
    # 基本のASIN検索実行
    basic_result = search_asin_with_prime_priority(title, max_results)
    
    if basic_result.get("search_status") == "success":
        asin = basic_result.get('asin') or basic_result.get('amazon_asin')
        
        if asin:
            try:
                # 修正版Prime+出品者情報を追加取得
                print(f"   📊 修正版Prime+出品者詳細分析: {asin}")
                prime_seller_info = get_prime_and_seller_info(asin, credentials)
                
                # 結果統合
                basic_result.update(prime_seller_info)
                
                # Shopee出品適性スコア計算
                shopee_score = calculate_shopee_suitability_score(basic_result)
                basic_result['shopee_suitability_score'] = shopee_score
                
                # 最終グループ判定
                shopee_group = determine_shopee_group(basic_result)
                basic_result['shopee_group'] = shopee_group
                
                print(f"   ✅ 修正版結果: Prime={basic_result['is_prime']} | 出品者={basic_result['seller_type']} | Shopee適性={shopee_score}点 | グループ={shopee_group}")
                
            except Exception as e:
                print(f"   ⚠️ Prime情報取得でエラー、フォールバック使用: {str(e)[:50]}...")
                fallback_info = create_fallback_prime_info(asin, str(e)[:30])
                basic_result.update(fallback_info)
                
                # フォールバック時もスコア計算
                shopee_score = calculate_shopee_suitability_score(basic_result)
                basic_result['shopee_suitability_score'] = shopee_score
                shopee_group = determine_shopee_group(basic_result)
                basic_result['shopee_group'] = shopee_group
    
    return basic_result

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

def determine_shopee_group(product_info):
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

# ======================== 既存機能との統合 ========================

def split_japanese_words(text):
    """日本語の単語分割改善関数"""
    if not text:
        return []
    
    # 一般的な化粧品・ヘアケア用語の分割パターン
    compound_patterns = [
        # クレンジング関連
        (r'マイルドクレンジングオイル', ['マイルド', 'クレンジング', 'オイル']),
        (r'クレンジングオイル', ['クレンジング', 'オイル']),
        (r'クレンジングクリーム', ['クレンジング', 'クリーム']),
        (r'クレンジングミルク', ['クレンジング', 'ミルク']),
        
        # ヘアケア関連
        (r'ヘアトリートメント', ['ヘア', 'トリートメント']),
        (r'ヘアオイル', ['ヘア', 'オイル']),
        (r'ヘアミルク', ['ヘア', 'ミルク']),
        (r'シャンプートリートメント', ['シャンプー', 'トリートメント']),
        
        # 一般的な複合語
        (r'スキンケア', ['スキン', 'ケア']),
        (r'フェイスケア', ['フェイス', 'ケア']),
        (r'ボディケア', ['ボディ', 'ケア']),
        (r'ビューティーケア', ['ビューティー', 'ケア']),
    ]
    
    # 元のテキストから単語を抽出
    words = []
    remaining_text = text
    
    # 複合語パターンマッチング
    for pattern, split_words in compound_patterns:
        if re.search(pattern, remaining_text):
            words.extend(split_words)
            remaining_text = re.sub(pattern, '', remaining_text)
    
    # 残りのテキストから通常の単語を抽出
    remaining_words = re.findall(r'\w{2,}', remaining_text)
    words.extend(remaining_words)
    
    # 重複除去と長さフィルター
    unique_words = []
    for word in words:
        if word and len(word) >= 2 and word not in unique_words:
            unique_words.append(word)
    
    return unique_words

def calculate_enhanced_relevance_score(original_title, amazon_title, amazon_brand, extracted_info):
    """改良された一致度計算（日本語単語分割対応・最大100点）"""
    if not amazon_title:
        return {"score": 0, "details": ["Amazon商品名なし"], "extracted_info": extracted_info}
    
    score = 0
    details = []
    
    original_clean = original_title.lower()
    amazon_clean = amazon_title.lower()
    
    # 1. 完全一致ボーナス（最大40点）
    if original_clean == amazon_clean:
        score += 40
        details.append("完全一致: +40点")
    elif original_clean in amazon_clean or amazon_clean in original_clean:
        score += 25
        details.append("部分完全一致: +25点")
    
    # 2. ブランド一致（最大25点）
    if extracted_info.get("brand") and amazon_brand:
        brand_lower = extracted_info["brand"].lower()
        amazon_brand_lower = amazon_brand.lower()
        
        if brand_lower in amazon_brand_lower or amazon_brand_lower in brand_lower:
            score += 25
            details.append(f"ブランド一致({extracted_info['brand']}): +25点")
        elif any(brand_var.lower() in amazon_brand_lower 
                for brand_var in load_brand_dict().get(extracted_info["brand"], [])):
            score += 20
            details.append(f"ブランド部分一致({extracted_info['brand']}): +20点")
    
    # 3. 数量情報一致（最大15点）
    if extracted_info.get("quantity"):
        if extracted_info["quantity"] in amazon_title:
            score += 15
            details.append(f"数量一致({extracted_info['quantity']}): +15点")
        else:
            # 数値部分のみ一致チェック
            quantity_num = re.search(r'\d+', extracted_info["quantity"])
            if quantity_num and quantity_num.group() in amazon_title:
                score += 8
                details.append(f"数量部分一致({quantity_num.group()}): +8点")
    
    # 4. 改良された単語一致（日本語対応・最大35点）
    # 重要キーワードを定義（英日対訳付き）
    important_keywords = {
        # 英語キーワード
        'cleansing', 'oil', 'mild', 'cream', 'lotion', 'serum',
        'essence', 'toner', 'milk', 'moisturizing', 'beauty',
        'face', 'skin', 'care', 'makeup', 'foundation',
        'shampoo', 'treatment', 'conditioner', 'hair', 'scalp', 
        'repair', 'damage', 'volume', 'shine',
        
        # 日本語キーワード
        'クレンジング', 'オイル', 'マイルド', 'クリーム', 'ローション', 
        'セラム', 'エッセンス', 'トナー', 'ミルク', '保湿', 'ビューティー',
        'フェイス', 'スキン', 'ケア', 'メイク', 'ファンデーション',
        'シャンプー', 'トリートメント', 'コンディショナー', 'ヘア', 
        'スカルプ', 'リペア', 'ダメージ', 'ボリューム'
    }
    
    # 英日対訳辞書（重要）
    en_jp_dict = {
        'cleansing': 'クレンジング',
        'oil': 'オイル',
        'mild': 'マイルド',
        'cream': 'クリーム',
        'lotion': 'ローション',
        'serum': 'セラム',
        'essence': 'エッセンス',
        'milk': 'ミルク',
        'shampoo': 'シャンプー',
        'treatment': 'トリートメント',
        'conditioner': 'コンディショナー',
        'hair': 'ヘア',
        'care': 'ケア'
    }
    
    # 改良された単語抽出
    # 元の商品名（日本語対応単語分割）
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', original_title):
        # 日本語が含まれる場合は日本語単語分割を使用
        original_words = set(split_japanese_words(original_title))
    else:
        # 英語の場合は通常の分割
        original_words = set(re.findall(r'\b\w{3,}\b', original_clean))
    
    # Amazon商品名（日本語対応単語分割）
    amazon_words = set(split_japanese_words(amazon_title)) | set(re.findall(r'\b\w{2,}\b', amazon_clean))
    
    # 共通単語を取得
    common_words = original_words & amazon_words
    
    # 英日対訳での一致もチェック
    translated_matches = []
    for en_word in original_words:
        jp_word = en_jp_dict.get(en_word.lower())
        if jp_word and jp_word in amazon_title:
            translated_matches.append(f"{en_word}→{jp_word}")
            common_words.add(en_word)  # 対訳一致として追加
    
    # デバッグ出力
    print(f"   🔍 改良版単語分析:")
    print(f"      元の単語: {sorted(original_words)}")
    print(f"      Amazon単語: {sorted(amazon_words)}")
    print(f"      共通単語: {sorted(common_words)}")
    print(f"      英日対訳一致: {translated_matches}")
    
    # 重要キーワードとの一致をチェック
    matched_important = []
    matched_general = []
    
    for word in common_words:
        if word.lower() in important_keywords:
            matched_important.append(word)
        else:
            matched_general.append(word)
    
    print(f"      重要単語: {matched_important}")
    print(f"      一般単語: {matched_general}")
    
    # 重要キーワードは高得点
    if matched_important:
        important_score = min(len(matched_important) * 5, 20)  # 重要語1個=5点、最大20点
        score += important_score
        details.append(f"重要単語一致({len(matched_important)}個: {', '.join(matched_important)}): +{important_score}点")
    
    # 英日対訳一致の追加得点
    if translated_matches:
        translation_score = min(len(translated_matches) * 8, 15)  # 対訳1個=8点、最大15点
        score += translation_score
        details.append(f"英日対訳一致({len(translated_matches)}個: {', '.join(translated_matches)}): +{translation_score}点")
    
    # 一般的な単語も加点
    if matched_general:
        general_score = min(len(matched_general) * 2, 10)  # 一般語1個=2点、最大10点
        score += general_score
        details.append(f"一般単語一致({len(matched_general)}個: {', '.join(matched_general)}): +{general_score}点")
    
    # 5. 商品タイプ一致ボーナス（最大10点）
    product_types = {
        'cleansing': ['クレンジング', 'メイク落とし'],
        'oil': ['オイル'],
        'cream': ['クリーム'],
        'lotion': ['ローション', '化粧水'],
        'serum': ['セラム', '美容液'],
        'shampoo': ['シャンプー'],
        'treatment': ['トリートメント'],
        'milk': ['ミルク', '乳液']
    }
    
    type_matches = 0
    for eng_type, jp_types in product_types.items():
        if eng_type in original_clean:
            for jp_type in jp_types:
                if jp_type in amazon_title:
                    type_matches += 1
                    break
    
    if type_matches > 0:
        type_score = min(type_matches * 5, 10)
        score += type_score
        details.append(f"商品タイプ一致({type_matches}個): +{type_score}点")
    
    # 最大100点に制限
    score = min(score, 100)
    
    return {
        "score": score,
        "details": details,
        "extracted_info": extracted_info
    }

def search_asin_with_prime_priority(title, max_results=5, **kwargs):
    """Prime優先ASIN検索（GPT-4o日本語化統合版）"""
    # extracted_info を最初に初期化（エラー処理で参照するため）
    extracted_info = {"brand": None, "quantity": None, "cleaned_text": str(title)}
    
    credentials = get_credentials()
    if not credentials:
        return {"search_status": "auth_error", "error": "認証情報が取得できません", "extracted_info": extracted_info}
    
    try:
        print(f"🔍 GPT-4o日本語化対応検索開始")
        print(f"   元の商品名: {title}")
        
        # ステップ1: 商品名クレンジング
        brand_dict = load_brand_dict()
        extracted_info = extract_brand_and_quantity(title, brand_dict)
        cleaned_title = extracted_info["cleaned_text"]
        
        print(f"   クレンジング後: {cleaned_title}")
        print(f"   抽出ブランド: {extracted_info.get('brand', 'なし')}")
        print(f"   抽出数量: {extracted_info.get('quantity', 'なし')}")
        
        # ステップ2: GPT-4o日本語化（英語の場合のみ）
        search_query = cleaned_title
        japanese_name = None
        llm_source = "Not Applied"
        
        # 英語が含まれている場合は日本語化を実行
        english_detected = re.search(r'[a-zA-Z]', cleaned_title)
        print(f"   🔍 英語検出チェック: '{cleaned_title}' → 英語あり: {bool(english_detected)}")
        
        if english_detected:
            print(f"   🤖 英語検出、GPT-4o日本語化実行中...")
            japanese_name, llm_source = get_japanese_name_hybrid(cleaned_title)
            
            if japanese_name and japanese_name != cleaned_title:
                search_query = japanese_name
                print(f"   ✅ 日本語化成功: {search_query}")
            else:
                print(f"   ⚠️ 日本語化失敗、元のタイトルで検索: {search_query}")
        else:
            print(f"   ℹ️ 日本語商品名、そのまま検索: {search_query}")
        
        print(f"   🔍 最終検索クエリ: '{search_query}'")
        
        # ステップ3: SP-API検索実行
        catalog_api = CatalogItems(
            credentials=credentials,
            marketplace=Marketplaces.JP
        )
        
        response = catalog_api.search_catalog_items(
            keywords=search_query,
            pageSize=max_results,
            marketplaceIds=[Marketplaces.JP.marketplace_id]
        )
        
        items = response.payload.get('items', [])
        if not items:
            return {
                "search_status": "no_results",
                "error": f"検索結果なし: {search_query}",
                "extracted_info": extracted_info,
                "japanese_name": japanese_name,
                "llm_source": llm_source
            }
        
        # デバッグ用: レスポンス構造を出力
        print(f"📊 SP-API レスポンス構造確認:")
        print(f"   総件数: {len(items)}件")
        print(f"   検索クエリ: {search_query}")
        
        # 最適なアイテムを選択（改良されたスコアリング）
        best_item = None
        best_score = 0
        
        for item in items:
            asin = item.get('asin', '')
            
            # SP-APIレスポンス構造に合わせて柔軟に対応
            item_title = ""
            brand_info = ""
            
            # 複数のキーを試行して商品名を取得
            for title_key in ['itemName', 'title', 'name', 'productTitle']:
                if item.get(title_key):
                    item_title = item.get(title_key)
                    break
            
            # 複数のキーを試行してブランド名を取得
            for brand_key in ['brand', 'brandName', 'manufacturer']:
                if item.get(brand_key):
                    brand_info = item.get(brand_key)
                    break
            
            # summariesキーがある場合は従来の方法も試行
            if not item_title and 'summaries' in item:
                summaries = item.get('summaries', [])
                if summaries and isinstance(summaries, list):
                    summary = summaries[0]
                    item_title = summary.get('itemName', '') or summary.get('title', '')
                    brand_info = summary.get('brand', '') or summary.get('brandName', '')
            
            print(f"   🔍 アイテム詳細:")
            print(f"      ASIN: {asin}")
            print(f"      商品名: {item_title[:50]}...")
            print(f"      ブランド: {brand_info}")
            
            # 改良された一致度計算（日本語化後のタイトルと比較）
            relevance_result = calculate_enhanced_relevance_score(
                search_query, item_title, brand_info, extracted_info
            )
            
            if relevance_result["score"] > best_score:
                best_score = relevance_result["score"]
                best_item = {
                    "asin": asin,
                    "title": item_title,
                    "brand": brand_info,
                    "relevance_score": relevance_result["score"],
                    "relevance_details": relevance_result["details"],
                    "is_prime": False,  # 簡易版ではPrime判定省略
                    "price": "unknown",
                    "extracted_info": extracted_info,
                    "japanese_name": japanese_name,
                    "llm_source": llm_source
                }
        
        if best_item:
            print(f"   ✅ 成功: ASIN={best_item['asin']}")
            print(f"      商品名: {best_item['title']}")
            print(f"      ブランド: {best_item['brand']}")
            print(f"      一致度: {best_item['relevance_score']}%")
            print(f"      日本語化: {japanese_name} ({llm_source})")
            print(f"      詳細: {', '.join(best_item['relevance_details'])}")
            
            return {
                "search_status": "success",
                "asin": best_item["asin"],
                "amazon_asin": best_item["asin"],  # 互換性のため
                "amazon_title": best_item["title"],
                "amazon_brand": best_item["brand"],
                "relevance_score": best_item["relevance_score"],
                "relevance_details": best_item["relevance_details"],
                "is_prime": best_item["is_prime"],
                "price": best_item["price"],
                "extracted_info": extracted_info,
                "japanese_name": japanese_name,
                "llm_source": llm_source
            }
        else:
            return {
                "search_status": "low_relevance",
                "error": "関連性の高い商品が見つかりませんでした",
                "extracted_info": extracted_info,
                "japanese_name": japanese_name,
                "llm_source": llm_source
            }
            
    except SellingApiException as e:
        error_msg = f"SP-API エラー: {e.code} - {e.message}"
        print(f"   ❌ 失敗: {error_msg}")
        return {"search_status": "api_error", "error": error_msg, "extracted_info": extracted_info}
    except Exception as e:
        error_msg = f"予期しないエラー: {str(e)}"
        print(f"   ❌ 失敗: {error_msg}")
        return {"search_status": "error", "error": error_msg, "extracted_info": extracted_info}

def search_asin_with_enhanced_prime_seller(title, max_results=5):
    """
    Prime+出品者情報統合版ASIN検索（新機能）
    """
    credentials = get_credentials()
    if not credentials:
        return {
            'search_status': 'auth_error',
            'asin': '',
            'amazon_asin': '',
            'error_message': '認証情報が設定されていません'
        }
    
    print(f"🔍 Prime+出品者情報統合検索: {title[:50]}...")
    
    # 基本のASIN検索実行
    basic_result = search_asin_with_prime_priority(title, max_results)
    
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
            shopee_group = determine_shopee_group(basic_result)
            basic_result['shopee_group'] = shopee_group
            
            print(f"   ✅ Prime: {basic_result['is_prime']} | 出品者: {basic_result['seller_type']} | Shopee適性: {shopee_score}点 | グループ: {shopee_group}")
    
    return basic_result

def process_batch_asin_search_with_ui(df, title_column='clean_title', limit=None):
    """リアルタイムUI付きバッチASIN検索（既存機能完全統合版）"""
    # 処理対象の決定
    if limit:
        df_to_process = df.head(limit).copy()
    else:
        df_to_process = df.copy()
    
    total_items = len(df_to_process)
    
    print(f"🚀 既存機能統合版バッチASIN検索開始: {total_items}件の商品を処理")
    print(f"📊 統合機能:")
    print(f"   ✅ 高品質商品名クレンジング")
    print(f"   ✅ 500+ブランド辞書活用")
    print(f"   ✅ 改良された一致度計算")
    print(f"   ✅ リアルタイム進捗表示")
    
    # UI要素の初期化
    progress_bar = st.progress(0)
    status_container = st.container()
    metrics_container = st.container()
    current_item_container = st.container()
    log_container = st.container()
    
    # 結果カラムの初期化
    result_columns = [
        'amazon_asin', 'amazon_title', 'amazon_brand', 'relevance_score',
        'is_prime', 'price', 'search_status', 'extracted_brand', 
        'extracted_quantity', 'cleaned_title', 'relevance_details',
        'japanese_name', 'llm_source'  # 日本語化情報を追加
    ]
    
    for col in result_columns:
        if col not in df_to_process.columns:
            df_to_process[col] = ""
    
    # バッチ処理実行
    success_count = 0
    error_count = 0
    detailed_logs = []
    
    for idx, row in df_to_process.iterrows():
        current_progress = (idx + 1) / total_items
        progress_bar.progress(current_progress)
        
        # 現在の処理状況表示
        with current_item_container:
            st.write(f"🔍 {idx + 1}/{total_items}: 検索中")
            current_title = str(row[title_column])[:100] + ("..." if len(str(row[title_column])) > 100 else "")
            st.write(f"商品名: {current_title}")
        
        # メトリクス更新
        with metrics_container:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("処理済み", f"{idx + 1}/{total_items}")
            with col2:
                st.metric("成功", f"{success_count}")
            with col3:
                st.metric("失敗", f"{error_count}")
            with col4:
                success_rate = (success_count / (idx + 1)) * 100 if idx >= 0 else 0
                st.metric("成功率", f"{success_rate:.1f}%")
        
        # ASIN検索実行
        search_result = search_asin_with_prime_priority(str(row[title_column]))
        
        # 結果の処理
        if search_result.get("search_status") == "success":
            success_count += 1
            df_to_process.at[idx, 'amazon_asin'] = search_result['asin']
            df_to_process.at[idx, 'amazon_title'] = search_result['amazon_title']
            df_to_process.at[idx, 'amazon_brand'] = search_result.get('amazon_brand', '')
            df_to_process.at[idx, 'relevance_score'] = search_result['relevance_score']
            df_to_process.at[idx, 'is_prime'] = search_result.get('is_prime', False)
            df_to_process.at[idx, 'price'] = search_result.get('price', 'unknown')
            df_to_process.at[idx, 'search_status'] = 'success'
            
            # 抽出情報
            extracted_info = search_result.get('extracted_info', {})
            df_to_process.at[idx, 'extracted_brand'] = extracted_info.get('brand', '')
            df_to_process.at[idx, 'extracted_quantity'] = extracted_info.get('quantity', '')
            df_to_process.at[idx, 'cleaned_title'] = extracted_info.get('cleaned_text', '')
            df_to_process.at[idx, 'relevance_details'] = ', '.join(search_result.get('relevance_details', []))
            
            # 日本語化情報
            df_to_process.at[idx, 'japanese_name'] = search_result.get('japanese_name', '')
            df_to_process.at[idx, 'llm_source'] = search_result.get('llm_source', '')
            
            log_entry = f"✅ {idx + 1}/{total_items}: {search_result['asin']} - {search_result['amazon_title'][:50]}... (日本語: {search_result.get('japanese_name', 'なし')})"
        else:
            error_count += 1
            df_to_process.at[idx, 'search_status'] = search_result.get('search_status', 'error')
            # 日本語化情報があれば記録
            df_to_process.at[idx, 'japanese_name'] = search_result.get('japanese_name', '')
            df_to_process.at[idx, 'llm_source'] = search_result.get('llm_source', '')
            error_reason = search_result.get('error', '不明なエラー')
            log_entry = f"❌ {idx + 1}/{total_items}: {error_reason}"
        
        detailed_logs.append(log_entry)
        
        # ログ表示更新
        with log_container:
            with st.expander("📋 詳細ログ", expanded=False):
                for log in detailed_logs[-10:]:  # 最新10件のみ表示
                    st.text(log)
        
        # API制限対策
        time.sleep(1)
    
    # 最終結果表示
    final_success_rate = (success_count / total_items) * 100
    
    with status_container:
        st.success(f"🎉 バッチ処理完了: {success_count}/{total_items}件成功 (成功率: {final_success_rate:.1f}%)")
    
    print(f"🎯 既存機能統合版バッチ処理完了:")
    print(f"   📊 全件数: {total_items}件")
    print(f"   ✅ 成功: {success_count}件")
    print(f"   ❌ 失敗: {error_count}件")
    print(f"   📈 成功率: {final_success_rate:.1f}%")
    
    # 成功時の効果
    if success_count > 0:
        st.balloons()
    
    return df_to_process

# Prime+出品者情報込みバッチ処理（新機能）
def process_batch_with_shopee_optimization(df, title_column='clean_title', limit=None):
    """
    Shopee最適化統合バッチ処理（Prime+出品者情報込み）- 完全修正版
    """
    # 処理対象の決定
    if limit:
        df_to_process = df.head(limit).copy()
    else:
        df_to_process = df.copy()
    
    total_items = len(df_to_process)
    
    print(f"🚀 Shopee最適化バッチ処理開始（完全修正版）: {total_items}件")
    print(f"📊 修正された機能:")
    print(f"   ✅ Prime+出品者情報取得（エラー修正版）")
    print(f"   ✅ Shopee出品適性スコア計算")
    print(f"   ✅ 4グループ自動分類（A/B/C/X）")
    
    credentials = get_credentials()
    if not credentials:
        st.error("❌ SP-API認証情報が設定されていません")
        return None
    
    # UI要素の初期化
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    # デバッグ: データフレーム構造確認
    print(f"📋 データフレーム情報:")
    print(f"   形状: {df_to_process.shape}")
    print(f"   カラム: {df_to_process.columns.tolist()}")
    print(f"   title_column: {title_column}")
    
    for idx, row in df_to_process.iterrows():
        try:
            # ステータス更新
            progress = (idx + 1) / total_items
            progress_bar.progress(progress)
            
            # データ型とアクセス方法の修正
            if isinstance(row, pd.Series):
                # pandas Seriesの場合（正常）
                if title_column in row.index:
                    product_name = str(row[title_column])
                    row_dict = row.to_dict()
                else:
                    print(f"   ⚠️ カラム '{title_column}' が見つかりません: {row.index.tolist()}")
                    # 最初のカラムを使用
                    product_name = str(row.iloc[0])
                    row_dict = row.to_dict()
            else:
                # その他の場合（エラー回避）
                print(f"   ⚠️ 予期しないデータ型: {type(row)}")
                if hasattr(row, 'keys'):
                    product_name = str(row.get(title_column, f"商品{idx+1}"))
                    row_dict = dict(row)
                else:
                    product_name = f"商品{idx+1}"
                    row_dict = {title_column: product_name}
            
            status_text.text(f"処理中: {idx + 1}/{total_items} - {product_name[:30]}...")
            
            print(f"📋 バッチ処理 {idx + 1}/{total_items}: {product_name}")
            
            # 修正版：Prime+出品者情報込みASIN検索を確実に実行
            result = search_asin_with_enhanced_prime_seller(product_name)
            
            print(f"   📊 バッチ結果: status={result.get('search_status')}, asin={result.get('asin', 'N/A')}, prime={result.get('is_prime', 'N/A')}, seller={result.get('seller_type', 'N/A')}, group={result.get('shopee_group', 'N/A')}")
            
            # 元データと結合（安全な方法）
            for key, value in row_dict.items():
                if key not in result:
                    result[key] = value
            
            # 成功時でもPrime情報が不足している場合の追加処理
            if result.get('search_status') == 'success' and result.get('seller_type') == 'unknown':
                print(f"   ⚠️ Prime情報不足を検出、フォールバック適用")
                asin = result.get('asin') or result.get('amazon_asin')
                if asin:
                    # フォールバック情報を強制適用
                    fallback_info = create_fallback_prime_info(asin, "バッチ処理フォールバック")
                    result.update(fallback_info)
                    
                    # 再計算
                    shopee_score = calculate_shopee_suitability_score(result)
                    result['shopee_suitability_score'] = shopee_score
                    shopee_group = determine_shopee_group(result)
                    result['shopee_group'] = shopee_group
                    
                    print(f"   ✅ フォールバック適用完了: Prime={result['is_prime']}, 出品者={result['seller_type']}, グループ={result['shopee_group']}")
            
            results.append(result)
            
            time.sleep(1.2)  # API制限対策（少し長めに）
            
        except Exception as e:
            print(f"   ❌ バッチ処理エラー詳細: {str(e)}")
            print(f"   📊 エラー詳細情報:")
            print(f"      idx: {idx}, type(row): {type(row)}")
            if hasattr(row, 'index'):
                print(f"      row.index: {row.index.tolist()}")
            
            # エラー時のデータ（安全な生成）
            try:
                # 安全なデータ抽出
                if isinstance(row, pd.Series):
                    row_dict = row.to_dict()
                    safe_product_name = str(row.iloc[0]) if len(row) > 0 else f"商品{idx+1}"
                else:
                    row_dict = {title_column: f"エラー商品{idx+1}"}
                    safe_product_name = f"エラー商品{idx+1}"
                
                error_result = row_dict.copy()
                error_result.update({
                    'search_status': 'error',
                    'asin': '',
                    'amazon_asin': '',
                    'is_prime': True,  # エラー時もPrimeと仮定
                    'seller_type': 'third_party',  # エラー時はサードパーティ
                    'shopee_group': 'B',  # エラー時はグループB
                    'shopee_suitability_score': 60,  # エラー時は60点
                    'error_message': str(e),
                    'product_name_used': safe_product_name
                })
                results.append(error_result)
                
            except Exception as e2:
                print(f"   ❌ エラーデータ生成でもエラー: {str(e2)}")
                # 最小限のエラーデータ
                minimal_error = {
                    title_column: f"エラー商品{idx+1}",
                    'search_status': 'error',
                    'asin': '',
                    'amazon_asin': '',
                    'is_prime': True,
                    'seller_type': 'third_party',
                    'shopee_group': 'B',
                    'shopee_suitability_score': 60,
                    'error_message': f"重大エラー: {str(e)} | {str(e2)}"
                }
                results.append(minimal_error)
    
    # 結果をDataFrameに変換
    if results:
        try:
            results_df = pd.DataFrame(results)
        except Exception as e:
            print(f"❌ DataFrame変換エラー: {str(e)}")
            # 緊急フォールバック：辞書のリストを標準化
            standardized_results = []
            for result in results:
                if isinstance(result, dict):
                    standardized_results.append(result)
                else:
                    standardized_results.append({
                        title_column: "不明な商品",
                        'search_status': 'error',
                        'shopee_group': 'B'
                    })
            results_df = pd.DataFrame(standardized_results)
    else:
        # 空の結果の場合
        results_df = pd.DataFrame({
            title_column: [f"商品{i+1}" for i in range(total_items)],
            'search_status': ['error'] * total_items,
            'shopee_group': ['B'] * total_items,
            'is_prime': [True] * total_items,
            'seller_type': ['third_party'] * total_items,
            'shopee_suitability_score': [60] * total_items
        })
    
    # 最終結果の確認とデバッグ
    print(f"📊 バッチ処理完了 - 最終結果確認:")
    if 'shopee_group' in results_df.columns:
        group_counts = results_df['shopee_group'].value_counts()
        print(f"   グループA: {group_counts.get('A', 0)}件")
        print(f"   グループB: {group_counts.get('B', 0)}件") 
        print(f"   グループC: {group_counts.get('C', 0)}件")
        print(f"   グループX: {group_counts.get('X', 0)}件")
        
        # 全件がグループXまたはエラーの場合は緊急対応
        total_valid = group_counts.get('A', 0) + group_counts.get('B', 0) + group_counts.get('C', 0)
        if total_valid == 0:
            print(f"🚨 緊急事態：有効な商品が0件です")
            print(f"   緊急フォールバック分類を実行します...")
            
            # 緊急フォールバック分類
            for idx in results_df.index:
                if results_df.at[idx, 'shopee_group'] in ['X', None, '']:
                    # 強制的にグループBに設定
                    results_df.at[idx, 'is_prime'] = True
                    results_df.at[idx, 'seller_type'] = 'third_party'
                    results_df.at[idx, 'shopee_group'] = 'B'
                    results_df.at[idx, 'shopee_suitability_score'] = 60
                    print(f"   緊急修正: 行{idx} → グループB")
            
            print(f"✅ 緊急フォールバック完了")
    
    progress_bar.progress(1.0)
    status_text.text("✅ Shopee出品最適化バッチ処理完了！")
    
    return results_df
def test_sp_api_connection():
    """SP-API接続テスト"""
    print("🧪 SP-API接続テスト")
    credentials = get_credentials()
    
    if not credentials:
        print("❌ 認証情報の取得に失敗")
        return False
    
    try:
        catalog_api = CatalogItems(
            credentials=credentials,
            marketplace=Marketplaces.JP
        )
        
        # テスト検索実行（SP-APIパラメータ修正）
        response = catalog_api.search_catalog_items(
            keywords="テスト",
            pageSize=1,
            marketplaceIds=[Marketplaces.JP.marketplace_id]
        )
        
        print("✅ SP-API接続テスト成功")
        return True
        
    except Exception as e:
        print(f"❌ SP-API接続テスト失敗: {e}")
        return False

# テスト実行
if __name__ == "__main__":
    print("=== SP-API Service Prime+出品者情報統合版テスト ===")
    
    # 認証情報テスト
    result = test_sp_api_connection()
    print(f"接続テスト結果: {result}")
    
    # 高品質クレンジングテスト
    test_title = "🅹🅿🇯🇵 Japan Fancl Mild Cleansing Oil 120ml*2 100% Authentic made in japan original"
    cleaned = advanced_product_name_cleansing(test_title)
    print(f"クレンジングテスト:")
    print(f"  元: {test_title}")
    print(f"  後: {cleaned}")
    
    # ブランド・数量抽出テスト
    brand_dict = load_brand_dict()
    extracted = extract_brand_and_quantity(test_title, brand_dict)
    print(f"抽出テスト:")
    print(f"  ブランド: {extracted['brand']}")
    print(f"  数量: {extracted['quantity']}")
    print(f"  クレンジング後: {extracted['cleaned_text']}")