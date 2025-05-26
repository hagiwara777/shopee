# sp_api_service.py - 既存機能完全統合版（循環インポート修正）
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

# .env読み込み（shopee直下の.envファイルを使用）
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
env_path = parent_dir / '.env'
load_dotenv(env_path)

def get_credentials():
    """SP-API認証情報取得"""
    lwa_app_id = os.getenv("LWA_APP_ID")
    lwa_client_secret = os.getenv("LWA_CLIENT_SECRET")
    refresh_token = os.getenv("SP_API_REFRESH_TOKEN")
    
    print(f"📁 .envファイル読み込み: {env_path}")
    print(f"LWA_APP_ID: {'あり' if lwa_app_id else 'なし'}")
    print(f"LWA_CLIENT_SECRET: {'あり' if lwa_client_secret else 'なし'}")
    print(f"SP_API_REFRESH_TOKEN: {'あり' if refresh_token else 'なし'}")
    
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
        
        # 追加ブランド（brands.jsonからの主要ブランド）
        "SONY": ["ソニー", "sony"],
        "NINTENDO": ["任天堂", "nintendo"],
        "APPLE": ["アップル", "apple"],
        "SAMSUNG": ["サムスン", "samsung"],
        "LG": ["エルジー", "lg"],
        "SHARP": ["シャープ", "sharp"],
        "TOSHIBA": ["東芝", "toshiba"],
        "FUJITSU": ["富士通", "fujitsu"],
        "NEC": ["エヌイーシー", "nec"],
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

def calculate_enhanced_relevance_score(original_title, amazon_title, amazon_brand, extracted_info):
    """改良された一致度計算（最大100点）"""
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
    
    # 4. 重要単語一致（改良版・最大30点）
    # 重要キーワードを定義（小文字で統一）
    important_keywords = {
        # 化粧品・スキンケア
        'cleansing', 'oil', 'mild', 'cream', 'lotion', 'serum',
        'essence', 'toner', 'milk', 'moisturizing', 'beauty',
        'face', 'skin', 'care', 'makeup', 'foundation',
        
        # ヘアケア
        'shampoo', 'treatment', 'conditioner', 'hair', 'scalp', 
        'repair', 'damage', 'volume', 'shine',
        
        # 日本語キーワード
        'クレンジング', 'オイル', 'マイルド', 'クリーム', 'ローション', 
        'セラム', 'エッセンス', 'トナー', 'ミルク', '保湿', 'ビューティー',
        'フェイス', 'スキン', 'ケア', 'メイク', 'ファンデーション',
        'シャンプー', 'トリートメント', 'コンディショナー', 'ヘア', 
        'スカルプ', 'リペア', 'ダメージ', 'ボリューム'
    }
    
    # 元の商品名から単語を抽出（3文字以上）
    original_words = set(re.findall(r'\b\w{3,}\b', original_clean))
    amazon_words = set(re.findall(r'\b\w{3,}\b', amazon_clean))
    
    # 共通単語を取得
    common_words = original_words & amazon_words
    
    # デバッグ出力
    print(f"   🔍 単語分析:")
    print(f"      元の単語: {sorted(original_words)}")
    print(f"      Amazon単語: {sorted(amazon_words)}")
    print(f"      共通単語: {sorted(common_words)}")
    
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
    
    # 一般的な単語も加点
    if matched_general:
        general_score = min(len(matched_general) * 2, 10)  # 一般語1個=2点、最大10点
        score += general_score
        details.append(f"一般単語一致({len(matched_general)}個: {', '.join(matched_general)}): +{general_score}点")
    
    # 5. 商品タイプ一致ボーナス（新規追加・最大10点）
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
    """Prime優先ASIN検索（既存機能完全統合版）"""
    # extracted_info を最初に初期化（エラー処理で参照するため）
    extracted_info = {"brand": None, "quantity": None, "cleaned_text": str(title)}
    
    credentials = get_credentials()
    if not credentials:
        return {"search_status": "auth_error", "error": "認証情報が取得できません", "extracted_info": extracted_info}
    
    try:
        # 商品名の前処理（既存機能統合）
        brand_dict = load_brand_dict()
        extracted_info = extract_brand_and_quantity(title, brand_dict)
        search_query = extracted_info["cleaned_text"]
        
        print(f"🔍 検索開始")
        print(f"   元の商品名: {title}")
        print(f"   クレンジング後: {search_query}")
        print(f"   抽出ブランド: {extracted_info.get('brand', 'なし')}")
        print(f"   抽出数量: {extracted_info.get('quantity', 'なし')}")
        
        # SP-API検索実行
        catalog_api = CatalogItems(
            credentials=credentials,
            marketplace=Marketplaces.JP
        )
        
        # 基本的な商品検索（SP-APIパラメータ修正）
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
                "extracted_info": extracted_info
            }
        
        # デバッグ用: レスポンス構造を出力
        print(f"📊 SP-API レスポンス構造確認:")
        print(f"   総件数: {len(items)}件")
        if items:
            first_item = items[0]
            print(f"   最初のアイテムキー: {list(first_item.keys())}")
            print(f"   最初のアイテム構造: {json.dumps(first_item, indent=2, ensure_ascii=False)[:500]}...")
        
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
            
            # 改良された一致度計算
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
                    "extracted_info": extracted_info
                }
        
        if best_item:
            print(f"   ✅ 成功: ASIN={best_item['asin']}")
            print(f"      商品名: {best_item['title']}")
            print(f"      ブランド: {best_item['brand']}")
            print(f"      一致度: {best_item['relevance_score']}%")
            print(f"      詳細: {', '.join(best_item['relevance_details'])}")
            
            return {
                "search_status": "success",
                "asin": best_item["asin"],
                "title": best_item["title"],
                "brand": best_item["brand"],
                "relevance_score": best_item["relevance_score"],
                "relevance_details": best_item["relevance_details"],
                "is_prime": best_item["is_prime"],
                "price": best_item["price"],
                "extracted_info": extracted_info
            }
        else:
            return {
                "search_status": "low_relevance",
                "error": "関連性の高い商品が見つかりませんでした",
                "extracted_info": extracted_info
            }
            
    except SellingApiException as e:
        error_msg = f"SP-API エラー: {e.code} - {e.message}"
        print(f"   ❌ 失敗: {error_msg}")
        return {"search_status": "api_error", "error": error_msg, "extracted_info": extracted_info}
    except Exception as e:
        error_msg = f"予期しないエラー: {str(e)}"
        print(f"   ❌ 失敗: {error_msg}")
        return {"search_status": "error", "error": error_msg, "extracted_info": extracted_info}

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
        'extracted_quantity', 'cleaned_title', 'relevance_details'
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
            df_to_process.at[idx, 'amazon_title'] = search_result['title']
            df_to_process.at[idx, 'amazon_brand'] = search_result.get('brand', '')
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
            
            log_entry = f"✅ {idx + 1}/{total_items}: {search_result['asin']} - {search_result['title'][:50]}..."
        else:
            error_count += 1
            df_to_process.at[idx, 'search_status'] = search_result.get('search_status', 'error')
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

def process_batch_asin_search(df, title_column='clean_title', limit=None):
    """バッチASIN検索（下位互換性維持）"""
    return process_batch_asin_search_with_ui(df, title_column, limit)

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
    print("=== SP-API Service 既存機能統合版テスト ===")
    
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