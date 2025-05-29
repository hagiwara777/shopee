# sp_api_service.py - Prime+出品者情報統合フルコード版
from sp_api.api import CatalogItems
from sp_api.api import Products as ProductPricing
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
import jellyfish

# .env読み込み（shopee直下の.envファイルを使用）
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
env_path = parent_dir / '.env'
load_dotenv(env_path)

# 公式メーカーID ホワイトリスト（必要に応じて追加）
WHITELIST_OFFICIAL_IDS = {
    'A1234567890ABCDE',  # 例：ファンケル公式（実際のIDに要変更）
    'B0987654321XYZ12',  # 例：資生堂公式（実際のIDに要変更）
    # TODO: 実際の公式メーカーセラーIDを追加
}

def similar(a, b, threshold=0.85):  # 0.9 → 0.85 に変更
    """Jaro-Winkler類似度による文字列比較（日本語対応調整版）"""
    if not a or not b:
        return False
    return jellyfish.jaro_winkler_similarity(a.lower().strip(), b.lower().strip()) > threshold

def is_official_seller(seller_id, seller_name, brand_name):
    """
    公式メーカー判定（3つの方法）- 正規表現パターン調整版
    """
    if not seller_name:
        return False
    # 方法1: ホワイトリストID判定
    if seller_id in WHITELIST_OFFICIAL_IDS:
        print(f"     ✅ 公式メーカー判定: ホワイトリストID ({seller_id})")
        return True
    # 方法2: Jaro-Winkler類似度判定（閾値調整）
    if brand_name and similar(brand_name, seller_name, 0.85):  # 閾値を0.85に調整
        similarity_score = jellyfish.jaro_winkler_similarity(brand_name.lower(), seller_name.lower())
        print(f"     ✅ 公式メーカー判定: 類似度{similarity_score:.3f} ({brand_name} ≈ {seller_name})")
        return True
    # 方法3: 正規表現判定（パターン拡張）
    official_patterns = [
        r'(official|公式|直営|_jp)$',     # 末尾パターン
        r'(official|公式|直営)',          # 任意位置パターン（新規追加）
        r'^\w+公式',                      # 先頭ブランド名+公式パターン
    ]
    for pattern in official_patterns:
        if re.search(pattern, seller_name.lower()):
            print(f"     ✅ 公式メーカー判定: 正規表現マッチ ({seller_name}) - パターン: {pattern}")
            return True
    print(f"     ❌ 公式メーカー判定: 非該当 ({seller_name})")
    return False

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
    """SP-API認証情報取得（2023年10月以降LWA専用版）"""
    # LWA認証情報のみ取得（AWS認証は2023年10月以降不要）
    lwa_app_id = os.getenv("SP_API_LWA_APP_ID")
    lwa_client_secret = os.getenv("SP_API_LWA_CLIENT_SECRET")
    refresh_token = os.getenv("SP_API_LWA_REFRESH_TOKEN")
    
    print(f"📁 .envファイル読み込み: {env_path}")
    print(f"SP_API_LWA_APP_ID: {'あり' if lwa_app_id else 'なし'}")
    print(f"SP_API_LWA_CLIENT_SECRET: {'あり' if lwa_client_secret else 'なし'}")
    print(f"SP_API_LWA_REFRESH_TOKEN: {'あり' if refresh_token else 'なし'}")
    print(f"🆕 2023年10月以降: AWS認証情報は不要（LWAのみ）")
    print(f"OPENAI_API_KEY: {'あり' if os.getenv('OPENAI_API_KEY') else 'なし'}")
    print(f"GEMINI_API_KEY: {'あり' if os.getenv('GEMINI_API_KEY') else 'なし'}")
    
    if not all([lwa_app_id, lwa_client_secret, refresh_token]):
        missing = []
        if not lwa_app_id: missing.append("SP_API_LWA_APP_ID")
        if not lwa_client_secret: missing.append("SP_API_LWA_CLIENT_SECRET")
        if not refresh_token: missing.append("SP_API_LWA_REFRESH_TOKEN")
        
        print(f"❌ LWA認証情報が不足: {', '.join(missing)}")
        return None
    
    # LWA認証のみで十分（AWS署名は2023年10月以降無視される）
    credentials = {
        "lwa_app_id": lwa_app_id,
        "lwa_client_secret": lwa_client_secret,
        "refresh_token": refresh_token,
        "use_aws_auth": False  # 明示的にAWS認証を無効化
    }
    
    print("✅ SP-API認証情報取得成功（LWAのみ）")
    return credentials

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

def create_safe_fallback_step4(asin, error_reason, brand_name=None):
    """
    Prime判定失敗時の安全なデフォルト情報を返す（グループC/unknownで統一, brand_nameも付与）
    """
    return {
        "asin": asin,
        "is_prime": False,
        "is_national_prime": False,
        "seller_name": "Unknown",
        "seller_id": "",
        "seller_type": "unknown",
        "is_amazon_seller": False,
        "is_official_seller": False,
        "category": "C",
        "prime_status": "NotPrime",
        "api_source": "ProductPricing_Fixed",
        "brand_used": brand_name,
        "error_reason": error_reason
    }

# ======================== Prime+出品者情報機能（新規追加） ========================

# sp_api_service.py - Prime情報取得修正版（該当関数のみ）

def check_official_manufacturer_simple(seller_name: str, brand: str) -> bool:
    """
    seller_name が公式メーカーかどうかを簡易推定
    - brand と seller_name が Jaro-Winkler > 0.9
    - seller_name が 'official'・'公式'・'直営'・'_jp' で終わる
    - WHITELIST_OFFICIAL_IDS に含まれる
    """
    import jellyfish, re
    WHITELIST_OFFICIAL_IDS = {"A1234567890ABCDE", "B0987654321XYZ"}
    if seller_name in WHITELIST_OFFICIAL_IDS:
        return True
    if brand and jellyfish.jaro_winkler_similarity(brand.lower(), seller_name.lower()) > 0.9:
        return True
    return bool(re.search(r"(official|公式|直営|_jp)$", seller_name.lower()))

def get_prime_and_seller_info(asin: str, credentials: dict, brand_name: str = "") -> dict:
    """
    最終修正版：正しいitem_conditionパラメータ使用
    """
    print(f"🔍 get_prime_and_seller_info開始: {asin}")
    
    try:
        from sp_api.base import SellingApiException
        
        # ProductPricingインスタンス作成（2023年10月以降AWS認証不要）
        pp = ProductPricing(
            credentials=credentials, 
            marketplace=Marketplaces.JP
        )
        print(f"   ✅ ProductPricingインスタンス作成成功（LWA認証のみ）")
        
        # 正しいパラメータ名で呼び出し
        print(f"   📞 get_item_offers呼び出し: {asin}")
        
        # テスト結果に基づく正しい呼び出し
        offers_response = pp.get_item_offers(
            asin=asin,
            item_condition="New"  # 正しいパラメータ名（小文字）
        )
        
        print(f"   ✅ get_item_offers呼び出し成功")
        
        # レスポンス処理
        offers = offers_response.payload.get("Offers", [])
        print(f"   📊 オファー数: {len(offers)}")
        
        if not offers:
            print(f"   ⚠️ {asin}: オファー情報なし")
            return create_safe_fallback_step4(asin, "オファー情報なし", brand_name)

        # デバッグ: offers[0]の構造を表示
        import json
        print(f"   🔍 デバッグ: offers[0]の構造:")
        print(json.dumps(offers[0], indent=2, ensure_ascii=False))
        
        # Prime情報抽出
        top_offer = offers[0]
        prime_info = top_offer.get("PrimeInformation", {})
        is_prime = prime_info.get("IsPrime", False)
        is_national_prime = prime_info.get("IsNationalPrime", False)
        
        print(f"   🎯 Prime判定: IsPrime={is_prime}, IsNationalPrime={is_national_prime}")
        
        # 出品者情報抽出
        seller_id = offers[0].get("SellerId", "")
        seller_name = offers[0].get("Name", "Unknown")
        
        print(f"   👤 出品者: ID={seller_id}, Name={seller_name}")
        
        # Amazon本体判定
        AMAZON_JP_SELLER_ID = 'A1VC38T7YXB528'
        is_amazon_seller = (seller_id == AMAZON_JP_SELLER_ID)
        
        # 公式メーカー判定
        is_official_seller_flag = is_official_seller(seller_id, seller_name, brand_name)
        
        # A/B/C分類
        if not is_prime:
            category = "C"
        elif is_amazon_seller or is_official_seller_flag:
            category = "A"
        else:
            category = "B"
        
        # セラータイプ決定
        if is_amazon_seller:
            seller_type = 'amazon'
        elif is_official_seller_flag:
            seller_type = 'official_manufacturer'
        else:
            seller_type = 'third_party'
        
        result = {
            "asin": asin,
            "is_prime": is_prime,
            "is_national_prime": is_national_prime,
            "seller_name": seller_name,
            "seller_id": seller_id,
            "seller_type": seller_type,
            "is_amazon_seller": is_amazon_seller,
            "is_official_seller": is_official_seller_flag,
            "category": category,
            "prime_status": "Prime" if is_prime else "NotPrime",
            "api_source": "ProductPricing_Fixed_Final",
            "brand_used": brand_name
        }
        
        print(f"   ✅ {asin}完了: Prime={is_prime}, Category={category}, Seller={seller_type}")
        return result
        
    except SellingApiException as exc:
        print(f"   ❌ SP-API SellingApiException詳細:")
        print(f"      Code: {exc.code}")
        payload = getattr(exc, "payload", None)
        print(f"      Payload: {payload}")
        print(f"      Headers: {getattr(exc, 'headers', 'N/A')}")
        
        # エラーコード別対処法（2023年10月以降対応）
        if exc.code == 401:
            print(f"      🔧 LWA認証エラー: LWA_APP_ID/SECRET/TOKENを確認")
        elif exc.code == 403:
            print(f"      🔧 権限エラー: アプリケーションのロール/権限を確認")
        elif exc.code == 429:
            print(f"      🔧 レート制限: 間隔を空けてリトライ（0.5RPS制限）")
        elif exc.code == 404:
            print(f"      🔧 商品未発見: ASIN {asin} が存在しないか削除済み")
        
        return create_safe_fallback_step4(asin, f"SP-API-{exc.code}: {str(payload)[:100]}", brand_name)
        
    except Exception as exc:
        print(f"   ❌ 予期しないエラー: {exc}")
        return create_safe_fallback_step4(asin, str(exc)[:60], brand_name)

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
            df_to_process.at[idx, 'price'] = search_result.get('price', '')
            df_to_process.at[idx, 'search_status'] = search_result['search_status']
            
            # ブランド・数量抽出結果を統合
            brand_info = extract_brand_and_quantity(search_result.get('amazon_title', ''), load_brand_dict())
            df_to_process.at[idx, 'extracted_brand'] = brand_info['brand'] or ''
            df_to_process.at[idx, 'extracted_quantity'] = brand_info['quantity'] or ''
            df_to_process.at[idx, 'cleaned_title'] = brand_info['cleaned_text'] or ''
            
            # 日本語化処理
            if df_to_process.at[idx, 'cleaned_title']:
                japanese_name, llm_source = get_japanese_name_hybrid(df_to_process.at[idx, 'cleaned_title'])
                df_to_process.at[idx, 'japanese_name'] = japanese_name
                df_to_process.at[idx, 'llm_source'] = llm_source
            
            # 詳細ログ
            detailed_logs.append(f"成功: {search_result['asin']} - ブランド: {df_to_process.at[idx, 'extracted_brand']} - タイトル: {df_to_process.at[idx, 'cleaned_title']}")
        else:
            error_count += 1
            df_to_process.at[idx, 'search_status'] = search_result.get('error_message', '不明なエラー')
            detailed_logs.append(f"失敗: {search_result.get('error_message', '不明なエラー')}")
        
        # 現在の詳細ログ表示
        with log_container:
            st.write("詳細ログ:")
            for log in detailed_logs[-10:]:  # 最新の10件を表示
                st.write(f"- {log}")
    
    # 最終結果の表示
    st.write(f"✅ バッチ処理完了: {success_count}件成功, {error_count}件失敗")
    
    return df_to_process

def search_asin_with_prime_priority(title, max_results=5):
    """
    ダミー: Prime優先ASIN検索（循環参照防止のため再帰呼び出しなし）
    """
    # 本番では実装を差し替え
    return {
        'search_status': 'not_implemented',
        'asin': '',
        'amazon_asin': '',
        'error_message': 'search_asin_with_prime_priorityはダミーです'
    }

def calculate_shopee_suitability_score(product_info):
    """
    ダミー: Shopee適性スコア計算（本番ではasin_helpers等で実装）
    """
    return 80

def determine_shopee_group(product_info):
    """
    ダミー: Shopeeグループ判定（A/B/C）
    """
    return product_info.get('category', 'C')