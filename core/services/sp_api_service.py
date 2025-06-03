# sp_api_service.py - Prime+出品者情報統合フルコード版（Phase 4.0対応版）
import time
import os
from dotenv import load_dotenv
import re
import pandas as pd
import json
import unicodedata
from pathlib import Path
import numpy as np
import traceback
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 🆕 Phase 4.0: 設定管理システム統合
CONFIG_MANAGER_AVAILABLE = False
try:
    from config_manager import create_threshold_config_manager
    config_manager = create_threshold_config_manager()
    CONFIG_MANAGER_AVAILABLE = True
    logger.info("✅ config_manager.py 統合成功 - 動的スコア調整が利用可能")
    
    # 現在の設定情報を表示
    current_preset = config_manager.current_config.get("applied_preset", "カスタム")
    last_updated = config_manager.current_config.get("last_updated", "不明")
    logger.info(f"⚙️ 現在の設定: プリセット='{current_preset}', 最終更新={last_updated}")
    
except ImportError as e:
    logger.warning(f"⚠️ config_manager.py インポート失敗: {e}")
    logger.info("📋 フォールバック: ハードコーディングされたスコア設定を使用")

def get_config_value(category: str, key: str, fallback_value):
    """
    設定値の取得（フォールバック対応）
    
    Args:
        category: 設定カテゴリ
        key: 設定キー
        fallback_value: フォールバック値
        
    Returns:
        設定値またはフォールバック値
    """
    if CONFIG_MANAGER_AVAILABLE:
        try:
            value = config_manager.get_threshold(category, key, fallback_value)
            logger.debug(f"設定値取得: {category}.{key} = {value}")
            return value
        except Exception as e:
            logger.error(f"⚠️ 設定値取得エラー {category}.{key}: {e}")
            return fallback_value
    else:
        return fallback_value

# .env読み込み
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
env_path = parent_dir / '.env'

if not env_path.exists():
    env_path_alt = Path.cwd() / '.env'
    if env_path_alt.exists():
        env_path = env_path_alt
    else:
        logger.warning(f"Warning: .env file not found at {env_path} or {env_path_alt}")
load_dotenv(env_path)

def get_japanese_name_from_gpt4o(clean_title):
    """GPT-4oによる高品質日本語化"""
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None, "OpenAI API Key not found"
        client = openai.OpenAI(api_key=api_key)
        prompt = f"次の英語の商品名を、日本のECサイトで通じる自然な日本語の商品名に翻訳してください。各単語は半角スペースで区切り、ブランドや容量も日本語で表記し、説明や余計な語句は不要：\n\n{clean_title}"
        response = client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": prompt}], max_tokens=64, temperature=0.3,
        )
        japanese_name = response.choices[0].message.content.strip()
        return japanese_name, "GPT-4o"
    except Exception as e:
        return None, f"GPT-4o Error: {e}"

def get_japanese_name_from_gemini(clean_title):
    """Geminiによる日本語化（バックアップ用）"""
    try:
        import google.generativeai as genai
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return None, "Gemini API Key not found"
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = f"次の英語の商品名を、日本語の商品名に自然に翻訳してください。ブランドや容量も自然な日本語で。余計な説明不要：\n\n{clean_title}"
        response = model.generate_content(prompt)
        japanese_name = response.text.strip()
        return japanese_name, "Gemini"
    except Exception as e:
        return None, f"Gemini Error: {e}"

def get_japanese_name_hybrid(clean_title):
    """ハイブリッド日本語化（GPT-4o + Geminiバックアップ）"""
    jp_name, source = get_japanese_name_from_gpt4o(clean_title)
    if jp_name and not jp_name.isspace() and "変換不可" not in jp_name:
        return jp_name, source
    jp_name, source = get_japanese_name_from_gemini(clean_title)
    if jp_name and not jp_name.isspace() and "変換不可" not in jp_name:
        return jp_name, source
    return clean_title, "Original"

def load_brand_dict():
    """高品質ブランド辞書の読み込み"""
    try:
        base_path = Path.cwd() if not Path(__file__).parent.exists() else Path(__file__).parent
        brands_file_path = base_path.parent / 'data' / 'brands.json'
        if not brands_file_path.exists():
             brands_file_path = base_path / 'data' / 'brands.json'
        if brands_file_path.exists():
            with open(brands_file_path, 'r', encoding='utf-8') as f: 
                existing_brands = json.load(f)
            print(f"📚 既存brands.jsonから読み込み: {len(existing_brands)}ブランド (Path: {brands_file_path})")
            return existing_brands
        else: 
            print(f"⚠️ brands.jsonファイルが見つかりません: {brands_file_path}")
    except Exception as e:
        print(f"⚠️ brands.json読み込みエラー: {e}。フォールバック辞書を使用します。")
    
    fallback_brands = {"FANCL": ["ファンケル", "fancl"], "ORBIS": ["オルビス", "orbis"], "SK-II": ["エスケーツー", "SK2", "SK-2"], "SHISEIDO": ["資生堂", "shiseido"], "KANEBO": ["カネボウ", "kanebo"], "KOSE": ["コーセー", "kose"], "POLA": ["ポーラ", "pola"], "ALBION": ["アルビオン", "albion"], "HABA": ["ハーバー", "haba"], "DHC": ["ディーエイチシー", "dhc"], "MILBON": ["ミルボン", "milbon"], "LEBEL": ["ルベル", "lebel"], "YOLU": ["ヨル", "yolu"], "TSUBAKI": ["椿", "tsubaki"], "LISSAGE": ["リサージ", "lissage"], "KERASTASE": ["ケラスターゼ", "kerastase"], "PANASONIC": ["パナソニック", "panasonic"], "PHILIPS": ["フィリップス", "philips"], "KOIZUMI": ["コイズミ", "koizumi"], "HITACHI": ["日立", "hitachi"], "SUNTORY": ["サントリー", "suntory"], "ASAHI": ["アサヒ", "asahi"], "MEIJI": ["明治", "meiji"], "MORINAGA": ["森永", "morinaga"],}
    print(f"📚 フォールバック辞書使用: {len(fallback_brands)}ブランド")
    return fallback_brands

def load_beauty_terms_dict():
    """美容・化粧品専門用語の英日マッピング辞書"""
    return {
        # 基本スキンケア用語
        "oil": ["オイル", "油"],
        "cream": ["クリーム"],
        "lotion": ["ローション", "化粧水"],
        "serum": ["セラム", "美容液"],
        "essence": ["エッセンス", "美容液"],
        "toner": ["トナー", "化粧水", "収れん化粧水"],
        "cleanser": ["クレンザー", "洗顔料"],
        "cleansing": ["クレンジング", "洗浄"],
        "facial": ["フェイシャル", "顔用", "洗顔"],
        "moisturizer": ["モイスチャライザー", "保湿剤", "保湿クリーム"],
        "emulsion": ["エマルジョン", "乳液"],
        "gel": ["ジェル"],
        "foam": ["フォーム", "泡"],
        "scrub": ["スクラブ"],
        "mask": ["マスク", "パック"],
        "pack": ["パック", "マスク"],
        "sheet": ["シート"],
        "patch": ["パッチ"],
        
        # ヘアケア用語
        "shampoo": ["シャンプー"],
        "conditioner": ["コンディショナー", "リンス"],
        "treatment": ["トリートメント", "ヘアトリートメント"],
        "hair": ["ヘア", "髪", "毛髪"],
        "scalp": ["スカルプ", "頭皮"],
        "repair": ["リペア", "修復"],
        "moisture": ["モイスチャー", "保湿"],
        "volume": ["ボリューム"],
        "smooth": ["スムース", "滑らか"],
        "silky": ["シルキー", "絹のような"],
        "straight": ["ストレート", "直毛"],
        "curl": ["カール", "巻き髪"],
        "wave": ["ウェーブ"],
        
        # メイクアップ用語
        "foundation": ["ファンデーション", "下地"],
        "concealer": ["コンシーラー"],
        "powder": ["パウダー", "粉"],
        "blush": ["チーク", "頬紅"],
        "eyeshadow": ["アイシャドウ"],
        "eyeliner": ["アイライナー"],
        "mascara": ["マスカラ"],
        "lipstick": ["リップスティック", "口紅"],
        "lip": ["リップ", "唇"],
        "gloss": ["グロス", "つや"],
        "rouge": ["ルージュ", "口紅"],
        "primer": ["プライマー", "下地"],
        "highlighter": ["ハイライター"],
        "bronzer": ["ブロンザー"],
        
        # 効果・特性用語
        "hydrating": ["ハイドレーティング", "保湿", "潤い"],
        "moisturizing": ["モイスチャライジング", "保湿"],
        "nourishing": ["ナリシング", "栄養", "滋養"],
        "anti-aging": ["アンチエイジング", "エイジングケア", "老化防止"],
        "brightening": ["ブライトニング", "美白", "明るく"],
        "whitening": ["ホワイトニング", "美白"],
        "firming": ["ファーミング", "引き締め"],
        "lifting": ["リフティング", "リフトアップ"],
        "regenerating": ["リジェネレーティング", "再生"],
        "revitalizing": ["リバイタライジング", "活性化"],
        "soothing": ["スージング", "鎮静", "落ち着かせる"],
        "calming": ["カーミング", "鎮静"],
        "sensitive": ["センシティブ", "敏感"],
        "gentle": ["ジェントル", "やさしい", "穏やか"],
        "mild": ["マイルド", "穏やか", "やさしい"],
        "deep": ["ディープ", "深い", "濃厚"],
        "intensive": ["インテンシブ", "集中"],
        "ultra": ["ウルトラ", "超"],
        "super": ["スーパー", "超"],
        "premium": ["プレミアム", "高級"],
        "professional": ["プロフェッショナル", "プロ用"],
        "organic": ["オーガニック", "有機"],
        "natural": ["ナチュラル", "天然"],
        
        # 肌質・髪質用語
        "oily": ["オイリー", "脂性"],
        "dry": ["ドライ", "乾燥"],
        "combination": ["コンビネーション", "混合肌"],
        "normal": ["ノーマル", "普通肌"],
        "mature": ["マチュア", "成熟肌"],
        "damaged": ["ダメージ", "傷んだ"],
        "colored": ["カラー", "染めた"],
        "bleached": ["ブリーチ", "脱色した"],
        "fine": ["ファイン", "細い"],
        "thick": ["シック", "太い"],
        "thin": ["シン", "薄い"],
        
        # 容器・形状用語
        "pump": ["ポンプ"],
        "tube": ["チューブ"],
        "bottle": ["ボトル"],
        "jar": ["ジャー", "壺"],
        "compact": ["コンパクト"],
        "palette": ["パレット"],
        "stick": ["スティック"],
        "pen": ["ペン"],
        "pencil": ["ペンシル"],
        "brush": ["ブラシ"],
        "sponge": ["スポンジ"],
        "applicator": ["アプリケーター"],
        
        # ブランド・シリーズ用語
        "collection": ["コレクション"],
        "series": ["シリーズ"],
        "line": ["ライン"],
        "range": ["レンジ"],
        "edition": ["エディション"],
        "limited": ["リミテッド", "限定"],
        "special": ["スペシャル", "特別"],
        "deluxe": ["デラックス", "豪華"],
        "mini": ["ミニ", "小さい"],
        "travel": ["トラベル", "旅行用"],
        "set": ["セット"],
        "kit": ["キット"],
        "duo": ["デュオ", "2個セット"],
        "trio": ["トリオ", "3個セット"]
    }

def advanced_product_name_cleansing(text):
    """高品質商品名クレンジング"""
    if not text: return ""
    text = unicodedata.normalize('NFKC', text)
    remove_patterns = [r'[🅹🅿🇯🇵★☆※◎○●▲△▼▽■□◆◇♦♢♠♣♥♡]', r'[\u2600-\u26FF\u2700-\u27BF]', r'\[.*?stock.*?\]', r'\[.*?在庫.*?\]', r'送料無料', r'配送無料', r'Free shipping', r'100% Authentic', r'made in japan', r'original', r'Direct from japan', r'Guaranteed authentic', r'正規品', r'本物', r'新品', r'未使用', r'@.*', r'by.*store', r'shop.*', r'hair care liquid', r'beauty product', r'cosmetic',]
    for pattern in remove_patterns: text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(Japan|Global|Korean|China)\s+', '', text, flags=re.IGNORECASE)
    if '/' in text and len(text.split('/')) > 1: text = text.split('/')[0].strip()
    text = re.sub(r'\s+', ' ', text).strip(); text = re.sub(r'^[^\w\s]*|[^\w\s]*$', '', text)
    return text

def clean_product_name(title):
    """商品名のクレンジング処理"""
    if not title:
        return ""
    
    # 基本的なクレンジング
    title = title.strip()
    title = re.sub(r'\s+', ' ', title)  # 複数の空白を1つに
    
    # 特殊文字の正規化
    title = unicodedata.normalize('NFKC', title)
    
    # 不要な文字の削除
    title = re.sub(r'[^\w\s\-.,&()/]', '', title)
    
    # 大文字小文字の正規化
    title = title.lower()
    
    return title

def extract_brand_and_quantity(title, brand_dict):
    """商品名からブランド名と数量を抽出"""
    if not title:
        return None, None
    
    # 商品名のクレンジング
    cleaned_title = clean_product_name(title)
    
    # ブランド名の抽出
    brand_name = None
    for brand, variations in brand_dict.items():
        for variation in variations:
            if variation.lower() in cleaned_title:
                brand_name = brand
                break
        if brand_name:
            break
    
    # 数量の抽出
    quantity = None
    quantity_patterns = [
        r'(\d+)\s*(?:ml|g|oz|fl\.?\s*oz|piece|pcs|set|pack|bottle|tube|jar|box)',
        r'(?:ml|g|oz|fl\.?\s*oz|piece|pcs|set|pack|bottle|tube|jar|box)\s*(\d+)',
        r'(\d+)\s*(?:x|×)\s*\d+',
        r'(\d+)\s*(?:count|ct)'
    ]
    
    for pattern in quantity_patterns:
        match = re.search(pattern, cleaned_title, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            break
    
    return brand_name, quantity

def _calculate_prime_confidence_score_internal(prime_info_dict):
    """Prime情報の信頼性スコア計算 (内部ヘルパー、辞書を受け取る)"""
    confidence_score = 50; seller_name = str(prime_info_dict.get('seller_name', ''))
    if 'Amazon.co.jp' in seller_name or 'Amazon' == seller_name: confidence_score += 30
    elif '推定' in seller_name or 'Estimated' in seller_name: confidence_score -= 30
    elif seller_name and seller_name.lower() != 'nan': confidence_score += 10
    asin_val = str(prime_info_dict.get('asin', ''));
    if asin_val.startswith('B0DR') or asin_val.startswith('B0DS'): confidence_score -= 20
    elif asin_val.startswith('B00') or asin_val.startswith('B01'): confidence_score += 10
    seller_type = str(prime_info_dict.get('seller_type', '')).lower(); is_prime = prime_info_dict.get('is_prime', False)
    if is_prime and seller_type == 'amazon': confidence_score += 20
    elif is_prime and seller_type == 'official_manufacturer': confidence_score += 15
    elif is_prime and seller_type == 'third_party': confidence_score += 5
    elif not is_prime and seller_type == 'amazon': confidence_score -= 25
    ship_hours = prime_info_dict.get('ship_hours')
    if ship_hours is not None:
        if ship_hours <= 12: confidence_score += 15
        elif ship_hours <= 24: confidence_score += 10
        elif ship_hours <= 48: confidence_score += 5
    return max(0, min(100, confidence_score))

def get_prime_and_seller_info_v8_enhanced(asin, brand_name=''):
    """Prime情報と出品者情報を取得（Phase 4.0）"""
    logger.info(f"🔍 Prime情報取得開始: ASIN={asin}, brand={brand_name}")
    
    # 設定値の取得
    prime_confidence_threshold = get_config_value('prime', 'confidence_threshold', 0.7)
    ship_hours_threshold = get_config_value('prime', 'ship_hours_threshold', 48)
    seller_score_threshold = get_config_value('prime', 'seller_score_threshold', 0.8)
    
    logger.info(f"⚙️ 設定値: prime_confidence={prime_confidence_threshold}, "
                f"ship_hours={ship_hours_threshold}, seller_score={seller_score_threshold}")
    
    # ASINの検証
    if not asin or not re.match(r'^[A-Z0-9]{10}$', asin):
        logger.warning(f"⚠️ 無効なASIN: {asin}")
        return {
            'is_prime': False,
            'prime_confidence': 0.0,
            'prime_reason': 'Invalid ASIN',
            'seller_info': {},
            'shipping_info': {},
            'shopee_score_bonus': 0.0
        }
    
    try:
        # 出品者情報の取得
        seller_info = get_seller_info(asin)
        logger.info(f"👤 出品者情報: {seller_info}")
        
        # 配送情報の取得
        shipping_info = get_shipping_info(asin)
        logger.info(f"🚚 配送情報: {shipping_info}")
        
        # Prime判定ロジック
        prime_info = {
            'is_prime': False,
            'prime_confidence': 0.0,
            'prime_reason': '',
            'seller_info': seller_info,
            'shipping_info': shipping_info,
            'shopee_score_bonus': 0.0
        }
        
        # 出品者スコアの計算
        seller_score = 0.0
        if seller_info.get('is_amazon'):
            seller_score = 1.0
        elif seller_info.get('is_official'):
            seller_score = 0.9
        elif seller_info.get('is_authorized'):
            seller_score = 0.8
        elif seller_info.get('is_verified'):
            seller_score = 0.7
        elif seller_info.get('is_third_party'):
            seller_score = 0.5
        
        # 配送スコアの計算
        shipping_score = 0.0
        if shipping_info.get('is_prime'):
            shipping_score = 1.0
        elif shipping_info.get('is_fba'):
            shipping_score = 0.9
        elif shipping_info.get('ship_hours', float('inf')) <= ship_hours_threshold:
            shipping_score = 0.8
        else:
            shipping_score = 0.5
        
        # 総合スコアの計算
        total_score = (seller_score * 0.6) + (shipping_score * 0.4)
        prime_info['prime_confidence'] = total_score
        
        # Prime判定
        if total_score >= prime_confidence_threshold:
            prime_info['is_prime'] = True
            prime_info['prime_reason'] = 'High confidence score'
            prime_info['shopee_score_bonus'] = 0.1
        else:
            prime_info['prime_reason'] = 'Low confidence score'
        
        logger.info(f"✅ Prime判定完了: is_prime={prime_info['is_prime']}, "
                   f"confidence={prime_info['prime_confidence']:.2f}, "
                   f"reason={prime_info['prime_reason']}")
        
        return prime_info
        
    except Exception as e:
        logger.error(f"❌ Prime情報取得エラー: {str(e)}")
        return {
            'is_prime': False,
            'prime_confidence': 0.0,
            'prime_reason': f'Error: {str(e)}',
            'seller_info': {},
            'shipping_info': {},
            'shopee_score_bonus': 0.0
        }

def calculate_prime_score(prime_info):
    """ Primeスコアの計算（Phase 4.0対応版） """
    try:
        # 設定値の取得
        seller_weight = get_config_value("prime_settings", "seller_weight", 0.4)
        shipping_weight = get_config_value("prime_settings", "shipping_weight", 0.4)
        brand_weight = get_config_value("prime_settings", "brand_weight", 0.2)
        
        # 出品者スコアの計算
        seller_score = 0
        if prime_info.get('is_amazon_seller'):
            seller_score += 40
        if prime_info.get('is_official_seller'):
            seller_score += 30
        if prime_info.get('is_fba'):
            seller_score += 30
        
        # 配送スコアの計算
        shipping_score = 0
        ship_hours = prime_info.get('ship_hours')
        if ship_hours is not None:
            if ship_hours <= 24:
                shipping_score = 100
            elif ship_hours <= 48:
                shipping_score = 80
            elif ship_hours <= 72:
                shipping_score = 60
            else:
                shipping_score = 40
        
        # ブランドスコアの計算
        brand_score = 0
        if prime_info.get('seller_type') == 'official':
            brand_score = 100
        elif prime_info.get('seller_type') == 'authorized':
            brand_score = 80
        elif prime_info.get('seller_type') == 'verified':
            brand_score = 60
        
        # 総合スコアの計算
        total_score = (
            seller_score * seller_weight +
            shipping_score * shipping_weight +
            brand_score * brand_weight
        )
        
        logger.debug(f"📊 スコア計算: 出品者={seller_score}, 配送={shipping_score}, ブランド={brand_score}, 総合={total_score}")
        return round(total_score)
        
    except Exception as e:
        logger.error(f"❌ Primeスコア計算エラー: {e}")
        return 25  # エラー時のフォールバック値

def calculate_shopee_suitability_score(product_info, prime_info):
    """Shopee適性スコアの計算"""
    try:
        # 基本スコアの初期化
        base_score = 0.0
        
        # ブランドスコアの計算
        brand_score = 0.0
        if product_info.get('extracted_brand'):
            brand_score = 0.3  # ブランドが特定できた場合のボーナス
        
        # Primeスコアの計算
        prime_score = 0.0
        if prime_info.get('is_prime'):
            prime_score = 0.4  # Prime商品のボーナス
        prime_score += prime_info.get('shopee_score_bonus', 0.0)  # 追加ボーナス
        
        # 配送スコアの計算
        shipping_score = 0.0
        if prime_info.get('shipping_info', {}).get('is_prime'):
            shipping_score = 0.2
        elif prime_info.get('shipping_info', {}).get('is_fba'):
            shipping_score = 0.15
        elif prime_info.get('shipping_info', {}).get('ship_hours', float('inf')) <= 48:
            shipping_score = 0.1
        
        # 出品者スコアの計算
        seller_score = 0.0
        if prime_info.get('seller_info', {}).get('is_amazon'):
            seller_score = 0.1
        elif prime_info.get('seller_info', {}).get('is_official'):
            seller_score = 0.08
        elif prime_info.get('seller_info', {}).get('is_authorized'):
            seller_score = 0.05
        
        # 総合スコアの計算
        total_score = base_score + brand_score + prime_score + shipping_score + seller_score
        
        # スコアの正規化（0.0-1.0の範囲に）
        normalized_score = min(max(total_score, 0.0), 1.0)
        
        return normalized_score
        
    except Exception as e:
        logger.error(f"❌ Shopee適性スコア計算エラー: {str(e)}")
        return 0.0

def calculate_shopee_bonus(prime_info, brand_name):
    """ Shopeeスコアボーナスの計算（Phase 4.0対応版） """
    try:
        # 設定値の取得
        prime_bonus = get_config_value("shopee_settings", "prime_bonus", 20)
        shipping_bonus = get_config_value("shopee_settings", "shipping_bonus", 15)
        brand_bonus = get_config_value("shopee_settings", "brand_bonus", 10)
        
        bonus = 0
        
        # Primeボーナス
        if prime_info.get('is_prime'):
            bonus += prime_bonus
        
        # 配送ボーナス
        ship_hours = prime_info.get('ship_hours')
        if ship_hours is not None and ship_hours <= 24:
            bonus += shipping_bonus
        
        # ブランドボーナス
        if prime_info.get('seller_type') in ['official', 'authorized']:
            bonus += brand_bonus
        
        logger.debug(f"🎁 ボーナス計算: Prime={prime_bonus if prime_info.get('is_prime') else 0}, 配送={shipping_bonus if ship_hours and ship_hours <= 24 else 0}, ブランド={brand_bonus if prime_info.get('seller_type') in ['official', 'authorized'] else 0}, 総合={bonus}")
        return bonus
        
    except Exception as e:
        logger.error(f"❌ Shopeeボーナス計算エラー: {e}")
        return 0  # エラー時のフォールバック値

def process_batch_with_shopee_optimization(df, title_column='clean_title', limit=20):
    """ Shopee出品最適化処理（Phase 4.0対応版） """
    logger.info(f"🚀 Shopee最適化処理開始（Phase 4.0）: {len(df) if df is not None else 0}件 (制限: {limit}件)")
    
    if df is None or df.empty: 
        logger.error("❌ 入力データが空です")
        return pd.DataFrame()
    
    # バッチ処理制限の取得
    max_batch_size = get_config_value("system_settings", "batch_processing_limit", 100)
    if limit > max_batch_size:
        logger.warning(f"⚠️ 指定された制限({limit})が最大バッチサイズ({max_batch_size})を超えています。最大サイズに調整します。")
        limit = max_batch_size
    
    df_to_process = df.head(limit).copy() if limit and limit > 0 else df.copy()
    logger.info(f"📊 処理対象: {len(df_to_process)}件")
    
    # ブランド辞書の読み込み
    logger.info("📚 ブランド辞書読み込み中...")
    try:
        brand_dict = load_brand_dict()
        logger.info(f"✅ ブランド辞書読み込み成功: {len(brand_dict)}件")
    except Exception as e_brand:
        logger.error(f"⚠️ ブランド辞書読み込み失敗: {e_brand}. フォールバック辞書使用")
        brand_dict = {"FANCL": ["ファンケル"], "ORBIS": ["オルビス"]}
    
    results = []
    success_count = 0
    error_count = 0
    retry_count = 0
    
    # エラー処理統計
    error_stats = {
        'title_empty': 0,
        'brand_extraction_failed': 0,
        'llm_failed': 0,
        'prime_info_failed': 0,
        'scoring_failed': 0,
        'general_error': 0
    }
    
    # 最大リトライ回数の取得
    max_retries = get_config_value("system_settings", "max_retry_attempts", 2)
    logger.info(f"🔄 バッチ処理開始... (最大リトライ回数: {max_retries})")

    for idx, row_series in df_to_process.iterrows():
        row_processing_success = False
        retry_attempts = 0
        
        while not row_processing_success and retry_attempts <= max_retries:
            try:
                current_row_dict = row_series.to_dict() 
                logger.info(f"\n🔍 処理中 {success_count + error_count + 1}/{len(df_to_process)}: {current_row_dict.get(title_column, 'N/A')[:50]}...")
                if retry_attempts > 0:
                    logger.info(f"  🔄 リトライ {retry_attempts}/{max_retries}")
                    retry_count += 1

                # Step 1: タイトル検証
                clean_title_val = str(current_row_dict.get(title_column, '')).strip()
                if not clean_title_val or clean_title_val.lower() == 'nan':
                    logger.warning(f"⚠️ 行{idx}: 商品名が空または無効。")
                    error_stats['title_empty'] += 1
                    error_details = {
                        'search_status': 'error', 
                        'error_reason': '商品名が空または無効', 
                        'data_source': '入力エラー',
                        'error_category': 'title_empty',
                        'retry_attempted': retry_attempts
                    }
                    results.append({**current_row_dict, **error_details})
                    error_count += 1
                    break  # リトライ不要なエラー

                # Step 2: ブランド・数量抽出
                try:
                    extracted_info_val = extract_brand_and_quantity(clean_title_val, brand_dict)
                    brand_name_val = extracted_info_val[0]
                    cleaned_text_for_title_val = clean_title_val
                    logger.info(f"  🏷️ ブランド検出後: brand_name='{brand_name_val}'")
                except Exception as e_brand_extract:
                    logger.error(f"  ⚠️ ブランド抽出エラー: {e_brand_extract}")
                    error_stats['brand_extraction_failed'] += 1
                    # ブランド抽出失敗でも処理続行
                    brand_name_val = ''
                    cleaned_text_for_title_val = clean_title_val

                # Step 3: 日本語化
                japanese_name_val = clean_title_val  # フォールバック
                llm_source_val = "Original"
                try:
                    japanese_name_val, llm_source_val = get_japanese_name_hybrid(cleaned_text_for_title_val)
                    logger.info(f"  🇯🇵 日本語化後: japanese_name='{japanese_name_val}', llm_source='{llm_source_val}'")
                except Exception as e_llm:
                    logger.error(f"  ⚠️ LLM日本語化エラー: {e_llm}. 元タイトル使用")
                    error_stats['llm_failed'] += 1
                    japanese_name_val = cleaned_text_for_title_val
                    llm_source_val = "Error_Fallback"

                # Step 4: ASIN決定
                asin_val = current_row_dict.get('asin', current_row_dict.get('amazon_asin', f"GEN{str(success_count + error_count + 1).zfill(9)}V8K"))
                logger.info(f"  🔍 ASIN決定: '{asin_val}'")

                # Step 5: Prime情報取得
                prime_info_val = {}
                try:
                    prime_info_val = get_prime_and_seller_info_v8_enhanced(asin=asin_val, brand_name=brand_name_val)
                    logger.info(f"  🎯 prime_info取得後: is_prime={prime_info_val.get('is_prime')}, seller_type='{prime_info_val.get('seller_type')}', ship_hours={prime_info_val.get('ship_hours')}, prime_confidence_score={prime_info_val.get('prime_confidence')}")
                except Exception as e_prime:
                    logger.error(f"  ⚠️ Prime情報取得エラー: {e_prime}. フォールバック情報使用")
                    error_stats['prime_info_failed'] += 1
                    prime_info_val = {
                        'is_prime': False, 'seller_name': 'エラー時フォールバック出品者', 'seller_type': 'unknown',
                        'ship_hours': None, 'prime_confidence': 0.0, 'prime_reason': f'Error: {str(e_prime)}'
                    }

                # Step 6: Shopee適性スコア計算
                shopee_score_val = 30  # フォールバック値
                try:
                    shopee_score_val = calculate_shopee_suitability_score(current_row_dict, prime_info_val)
                    logger.info(f"  📊 Shopeeスコア計算後: shopee_score={shopee_score_val}")
                except Exception as e_score:
                    logger.error(f"  ⚠️ Shopeeスコア計算エラー: {e_score}. フォールバック値使用")
                    error_stats['scoring_failed'] += 1
                    shopee_score_val = 30

                # Step 7: 関連性スコア計算
                relevance_score_val = calculate_relevance_score(cleaned_text_for_title_val, japanese_name_val)
                match_percentage_val = calculate_match_percentage(cleaned_text_for_title_val, japanese_name_val)
                
                # Step 8: 結果データ構築
                result_data_to_update = {
                    'clean_title': cleaned_text_for_title_val,
                    'japanese_name': japanese_name_val,
                    'amazon_title': japanese_name_val,
                    'asin': asin_val,
                    'amazon_asin': asin_val,
                    'amazon_brand': brand_name_val,
                    'extracted_brand': brand_name_val,
                    'extracted_quantity': extracted_info_val[1],
                    'llm_source': llm_source_val,
                    'is_prime': prime_info_val.get('is_prime'),
                    'seller_name': prime_info_val.get('seller_name'),
                    'seller_type': prime_info_val.get('seller_type'),
                    'seller_id': prime_info_val.get('seller_id'),
                    'is_amazon_seller': prime_info_val.get('is_amazon_seller'),
                    'is_official_seller': prime_info_val.get('is_official_seller'),
                    'is_fba': prime_info_val.get('is_fba'),
                    'ship_hours': prime_info_val.get('ship_hours'),
                    'ship_confidence': prime_info_val.get('ship_confidence'),
                    'ship_bucket': prime_info_val.get('ship_bucket'),
                    'ship_category': prime_info_val.get('ship_category'),
                    'ship_source': prime_info_val.get('ship_source'),
                    'ship_priority': prime_info_val.get('ship_priority'),
                    'prime_confidence': prime_info_val.get('prime_confidence'),
                    'prime_reason': prime_info_val.get('prime_reason'),
                    'shopee_suitability_score': shopee_score_val,
                    'relevance_score': relevance_score_val,
                    'match_percentage': match_percentage_val,
                    'category': prime_info_val.get('category'),
                    'classification_reason': prime_info_val.get('classification_reason'),
                    'classification_confidence': prime_info_val.get('classification_confidence'),
                    'shopee_score_bonus': prime_info_val.get('shopee_score_bonus'),
                    'search_status': 'success',
                    'api_source': 'v8_enhanced',
                    'data_source': 'v8_ERROR_HANDLING_ENHANCED',
                    'v8_system_used': 'Phase 4.0',
                    'retry_attempted': retry_attempts,
                    'processing_notes': f"成功（リトライ{retry_attempts}回）" if retry_attempts > 0 else "成功"
                }
                
                final_result_row = current_row_dict.copy()
                final_result_row.update(result_data_to_update) 
                
                results.append(final_result_row)
                success_count += 1
                row_processing_success = True  # 成功フラグ
                
                logger.info(f"   ✅ 成功: ASIN={asin_val}, Prime={final_result_row.get('is_prime')}, ShipH={final_result_row.get('ship_hours')}, PrimeScore={final_result_row.get('prime_confidence')}, ShopeeScore={shopee_score_val}")

            except Exception as e_main_loop:
                retry_attempts += 1
                logger.error(f"❌ 行{idx} で一般エラー (試行{retry_attempts}/{max_retries+1}): {str(e_main_loop)}")
                
                if retry_attempts > max_retries:
                    # 最大リトライ回数に達した場合
                    logger.error(f"💥 行{idx} 最大リトライ回数超過。エラーデータとして記録。")
                    error_count += 1
                    error_stats['general_error'] += 1
                    error_details_loop = {
                        'search_status': 'error', 
                        'error_reason': f"最大リトライ後エラー: {str(e_main_loop)[:150]}", 
                        'data_source': '処理ループ内エラー',
                        'error_category': 'general_error',
                        'retry_attempted': retry_attempts-1,
                        'processing_notes': f"失敗（{retry_attempts-1}回リトライ後）"
                    }
                    results.append({**current_row_dict, **error_details_loop})
                    break
                else:
                    # リトライ継続
                    logger.info(f"  🔄 {retry_attempts}秒待機後リトライ...")
                    time.sleep(retry_attempts)  # 段階的待機時間
            
    # 処理結果サマリー
    logger.info(f"\n📊 バッチ処理完了:")
    logger.info(f"  ✅ 成功: {success_count}件")
    logger.info(f"  ❌ エラー: {error_count}件")
    logger.info(f"  🔄 リトライ実行: {retry_count}回")
    
    logger.info(f"\n📋 エラー内訳:")
    for error_type, count in error_stats.items():
        if count > 0:
            logger.info(f"  {error_type}: {count}件")
    
    if results:
        result_df = pd.DataFrame(results)
        logger.info(f"📋 結果DFカラム数: {len(result_df.columns)}")
        return result_df
    else:
        logger.error("❌ 処理結果が空です。")
        error_cols = ['search_status', 'error_reason', 'data_source', 'error_category', 'retry_attempted']
        df_cols = df.columns.tolist() if df is not None else []
        return pd.DataFrame(columns=list(set(df_cols + error_cols)))

def calculate_relevance_score(original, japanese):
    """関連性スコア計算（美容用語辞書対応版）"""
    if not original or not japanese: 
        return 0
    
    # 美容用語辞書の読み込み
    beauty_terms = load_beauty_terms_dict()
    
    # 英語の単語を小文字に、日本語は元のまま
    original_words = set(original.lower().split())
    japanese_words = set(japanese.split())
    
    if len(original_words) == 0:
        return 0
    
    # 基本的な語の一致度計算
    direct_common_words = original_words & japanese_words
    basic_similarity = len(direct_common_words) / len(original_words)
    
    # 美容用語マッピングによる高度一致判定
    beauty_matches = 0
    total_beauty_terms = 0
    
    for eng_word in original_words:
        if eng_word in beauty_terms:
            total_beauty_terms += 1
            jp_variations = beauty_terms[eng_word]
            
            # 日本語の各バリエーションとの一致チェック
            for jp_variation in jp_variations:
                if jp_variation in japanese:
                    beauty_matches += 1
                    print(f"    ✅ 美容用語一致: '{eng_word}' → '{jp_variation}'")
                    break
    
    # スコア計算（美容用語重視）
    if total_beauty_terms > 0:
        # 美容用語がある場合: 美容用語一致度を重視
        beauty_similarity = beauty_matches / total_beauty_terms
        # 基本一致度と美容用語一致度の加重平均
        enhanced_similarity = (basic_similarity * 0.3) + (beauty_similarity * 0.7)
        print(f"    📊 美容用語強化: 基本{basic_similarity:.2f} + 美容{beauty_similarity:.2f} = {enhanced_similarity:.2f}")
    else:
        # 美容用語がない場合: 基本一致度のみ
        enhanced_similarity = basic_similarity
        print(f"    📊 基本一致度のみ: {enhanced_similarity:.2f}")
    
    similarity_score = int(enhanced_similarity * 100)
    
    # 修正: オフセットなしの純粋な一致度を返す
    final_score = min(max(similarity_score, 0), 100)
    print(f"    🎯 最終relevance_score: {final_score}%")
    
    return final_score

def calculate_match_percentage(original, japanese):
    """一致率計算（美容用語辞書対応版）"""
    if not original or not japanese:
        return 0
    
    # 美容用語辞書の読み込み
    beauty_terms = load_beauty_terms_dict()
    
    # 英語の単語を小文字に、日本語は元のまま
    original_words = set(original.lower().split())
    japanese_words = set(japanese.split())
    
    if len(original_words) == 0:
        return 0
    
    # 基本的な語の一致度計算
    direct_common_words = original_words & japanese_words
    basic_similarity = len(direct_common_words) / len(original_words)
    
    # 美容用語マッピングによる高度一致判定
    beauty_matches = 0
    total_beauty_terms = 0
    
    for eng_word in original_words:
        if eng_word in beauty_terms:
            total_beauty_terms += 1
            jp_variations = beauty_terms[eng_word]
            
            # 日本語の各バリエーションとの一致チェック
            for jp_variation in jp_variations:
                if jp_variation in japanese:
                    beauty_matches += 1
                    print(f"    ✅ 美容用語一致: '{eng_word}' → '{jp_variation}'")
                    break
    
    # スコア計算（美容用語重視）
    if total_beauty_terms > 0:
        # 美容用語がある場合: 美容用語一致度を重視
        beauty_similarity = beauty_matches / total_beauty_terms
        # 基本一致度と美容用語一致度の加重平均
        enhanced_similarity = (basic_similarity * 0.3) + (beauty_similarity * 0.7)
        print(f"    📊 美容用語強化: 基本{basic_similarity:.2f} + 美容{beauty_similarity:.2f} = {enhanced_similarity:.2f}")
    else:
        # 美容用語がない場合: 基本一致度のみ
        enhanced_similarity = basic_similarity
        print(f"    📊 基本一致度のみ: {enhanced_similarity:.2f}")
    
    similarity_score = int(enhanced_similarity * 100)
    
    # 修正: オフセットなしの純粋な一致度を返す
    final_score = min(max(similarity_score, 0), 100)
    print(f"    🎯 最終match_percentage: {final_score}%")
    
    return final_score

def analyze_beauty_terms_coverage(text):
    """美容用語のカバレッジ分析"""
    if not text:
        return {
            'total_terms': 0,
            'matched_terms': 0,
            'coverage_percentage': 0,
            'matched_details': []
        }
    
    # 美容用語辞書の読み込み
    beauty_terms = load_beauty_terms_dict()
    
    # テキストを単語に分割
    words = set(text.lower().split())
    
    # 美容用語のマッチング分析
    matched_terms = []
    for eng_word in words:
        if eng_word in beauty_terms:
            jp_variations = beauty_terms[eng_word]
            matched_terms.append({
                'english': eng_word,
                'japanese_variations': jp_variations
            })
    
    # 結果の集計
    total_terms = len(beauty_terms)
    matched_count = len(matched_terms)
    coverage = (matched_count / total_terms * 100) if total_terms > 0 else 0
    
    return {
        'total_terms': total_terms,
        'matched_terms': matched_count,
        'coverage_percentage': round(coverage, 2),
        'matched_details': matched_terms
    }

def get_seller_info(asin):
    """ 出品者情報の取得（Phase 4.0対応版） """
    logger.info(f"🔍 出品者情報取得開始: ASIN={asin}")
    
    try:
        # 設定値の取得
        api_timeout = get_config_value("api_settings", "timeout", 30)
        max_retries = get_config_value("api_settings", "max_retries", 3)
        
        # APIリクエストの実行
        for attempt in range(max_retries):
            try:
                # TODO: 実際のAPIリクエストを実装
                # 現在はダミーデータを返す
                seller_types = ['amazon', 'official', 'authorized', 'verified', 'third_party', 'unknown']
                seller_type = np.random.choice(seller_types, p=[0.3, 0.2, 0.2, 0.1, 0.15, 0.05])
                
                seller_info = {
                    'seller_name': '',
                    'seller_type': seller_type,
                    'seller_id': f"SID_{np.random.randint(1000, 9999)}",
                    'is_amazon_seller': seller_type == 'amazon',
                    'is_official_seller': seller_type in ['official', 'authorized'],
                    'is_fba': np.random.choice([True, False], p=[0.7, 0.3])
                }
                
                if seller_type == 'amazon':
                    seller_info['seller_name'] = 'Amazon.co.jp'
                elif seller_type in ['official', 'authorized']:
                    seller_info['seller_name'] = f'公式出品者{np.random.randint(1, 100)}'
                else:
                    seller_info['seller_name'] = f'出品者{np.random.randint(1, 1000)}'
                
                logger.info(f"✅ 出品者情報取得成功: {seller_info['seller_name']} ({seller_info['seller_type']})")
                return seller_info
                
            except Exception as e_api:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ APIリクエスト失敗 (試行{attempt + 1}/{max_retries}): {e_api}")
                    time.sleep(attempt + 1)  # 段階的待機
                else:
                    raise e_api
        
    except Exception as e:
        logger.error(f"❌ 出品者情報取得エラー: {e}")
        return None

def get_shipping_info(asin):
    """ 配送情報の取得（Phase 4.0対応版） """
    logger.info(f"🔍 配送情報取得開始: ASIN={asin}")
    
    try:
        # 設定値の取得
        api_timeout = get_config_value("api_settings", "timeout", 30)
        max_retries = get_config_value("api_settings", "max_retries", 3)
        
        # APIリクエストの実行
        for attempt in range(max_retries):
            try:
                # TODO: 実際のAPIリクエストを実装
                # 現在はダミーデータを返す
                ship_hours = np.random.choice([12, 18, 24, 36, 48, 72, 96, None], p=[0.1, 0.2, 0.3, 0.15, 0.1, 0.05, 0.05, 0.05])
                
                if ship_hours is None:
                    ship_info = {
                        'ship_hours': None,
                        'ship_confidence': 0,
                        'ship_bucket': '不明',
                        'ship_category': 'C',
                        'ship_source': 'unknown',
                        'ship_priority': 99
                    }
                else:
                    if ship_hours <= 12:
                        bucket, category, priority = "12h以内", "超高速", 1
                    elif ship_hours <= 24:
                        bucket, category, priority = "24h以内", "高速", 2
                    elif ship_hours <= 48:
                        bucket, category, priority = "48h以内", "標準", 3
                    elif ship_hours <= 72:
                        bucket, category, priority = "72h以内", "やや低速", 4
                    else:
                        bucket, category, priority = "72h超", "低速", 5
                    
                    ship_info = {
                        'ship_hours': ship_hours,
                        'ship_confidence': np.random.randint(50, 100),
                        'ship_bucket': bucket,
                        'ship_category': category,
                        'ship_source': 'API取得',
                        'ship_priority': priority
                    }
                
                logger.info(f"✅ 配送情報取得成功: {ship_info['ship_hours']}時間 ({ship_info['ship_category']})")
                return ship_info
                
            except Exception as e_api:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ APIリクエスト失敗 (試行{attempt + 1}/{max_retries}): {e_api}")
                    time.sleep(attempt + 1)  # 段階的待機
                else:
                    raise e_api
        
    except Exception as e:
        logger.error(f"❌ 配送情報取得エラー: {e}")
        return None