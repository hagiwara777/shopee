import re
import json
from pathlib import Path

BRANDS_PATH = Path("data/brands.json")

def load_brand_dict():
    """brands.jsonを読み込んでブランド辞書を返す"""
    if BRANDS_PATH.exists():
        try:
            with open(BRANDS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"brands.json読み込みエラー: {e}")
            return get_minimal_fallback_brands()
    else:
        print(f"brands.jsonが見つかりません: {BRANDS_PATH}")
        return get_minimal_fallback_brands()

def get_minimal_fallback_brands():
    """最小限のフォールバックブランド"""
    return {
        "FANCL": ["ファンケル", "FANCL"],
        "ORBIS": ["オルビス", "ORBIS"], 
        "LEBEL": ["ルベル", "LEBEL"],
        "MILBON": ["ミルボン", "MILBON"],
        "YOLU": ["ヨル", "YOLU"]
    }

def load_brands():
    """後方互換性のための関数（既存コード用）"""
    return load_brand_dict()

def get_preferred_brand_name(variations):
    """
    バリエーションリストから「カタカナ＞漢字＞ひらがな＞英字」優先でブランド名を返す
    """
    if not variations:
        return ""
    
    katakana_re = re.compile(r'[\u30A0-\u30FF]+')
    kanji_re = re.compile(r'[\u4E00-\u9FFF]+')
    hiragana_re = re.compile(r'[\u3040-\u309F]+')
    
    # カタカナ優先
    for name in variations:
        if katakana_re.search(name):
            return name
    
    # 漢字
    for name in variations:
        if kanji_re.search(name):
            return name
    
    # ひらがな
    for name in variations:
        if hiragana_re.search(name):
            return name
    
    # 英字（全て大文字を優先）
    upper_names = [name for name in variations if name.isupper() and name.isalpha()]
    if upper_names:
        return upper_names[0]
    
    # その他の英字
    for name in variations:
        if re.match(r'^[A-Za-z0-9\s\-&.()]+$', name):
            return name
    
    return variations[0] if variations else ""

def extract_brand(clean_title, brand_dict=None):
    """
    クリーンタイトルからブランド名を抽出
    """
    if not clean_title:
        return ""
    
    if brand_dict is None:
        brand_dict = load_brand_dict()
    
    clean_title_lower = clean_title.lower()
    
    # 除外単語（ブランドではない一般的な単語）
    exclude_words = {
        'clean', 'cleansing', 'cleaning', 'clear', 'cream', 'care', 'color',
        'natural', 'organic', 'professional', 'premium', 'luxury', 'beauty',
        'hair', 'skin', 'face', 'body', 'hand', 'nail', 'eye', 'lip',
        'shampoo', 'conditioner', 'treatment', 'serum', 'lotion', 'oil',
        'gel', 'foam', 'mask', 'scrub', 'toner', 'essence', 'foundation',
        'powder', 'lipstick', 'mascara', 'eyeliner', 'blush', 'concealer',
        'japan', 'japanese', 'korea', 'korean', 'global', 'international',
        'repair', 'night', 'day', 'morning', 'deep', 'mild', 'gentle',
        'moisture', 'hydrating', 'nourishing', 'purifying', 'brightening'
    }
    
    # 辞書ベースのブランド検索
    brand_matches = []
    
    for brand_key, variations in brand_dict.items():
        for variation in variations:
            variation_lower = variation.lower()
            
            # 除外単語をスキップ
            if variation_lower in exclude_words:
                continue
            
            # 精密な検索パターン
            patterns = [
                f"^{re.escape(variation_lower)}\\b",        # 先頭一致
                f"\\b{re.escape(variation_lower)}\\b",      # 完全一致
                f"\\b{re.escape(variation_lower)}$",        # 末尾一致
            ]
            
            for pattern_idx, pattern in enumerate(patterns):
                if re.search(pattern, clean_title_lower):
                    # マッチの質を評価（先頭一致 > 完全一致 > 末尾一致）
                    quality = 3 - pattern_idx
                    brand_matches.append((len(variation), quality, variation, brand_key))
                    break
    
    # 長さと質でソート
    if brand_matches:
        brand_matches.sort(key=lambda x: (x[0], x[1]), reverse=True)
        matched_brand_key = brand_matches[0][3]
        return get_preferred_brand_name(brand_dict[matched_brand_key])
    
    # フォールバック：パターンベースの検索
    words = clean_title.split()
    
    for i, word in enumerate(words):
        if word.lower() in exclude_words:
            continue
            
        if is_brand_like_word(word) and is_valid_brand_context(words, i):
            return word.upper()
    
    return ""

def is_brand_like_word(word):
    """単語がブランド名らしいかを判定"""
    if len(word) < 2:
        return False
    
    if word.isdigit():
        return False
    
    if re.match(r'^\d+(ml|mg|g|kg|oz|lb|inch|cm|mm|gb|tb)$', word.lower()):
        return False
    
    if word[0].isupper() or word.isupper():
        return True
    
    if re.match(r'^[A-Z][a-zA-Z0-9\-\.&]+$', word) and len(word) >= 3:
        return True
    
    return False

def is_valid_brand_context(words, index):
    """ブランド名として有効な文脈かを判定"""
    product_types = {
        'shampoo', 'conditioner', 'treatment', 'serum', 'oil', 'cream', 
        'lotion', 'gel', 'mask', 'cleanser', 'toner', 'essence',
        'foundation', 'powder', 'lipstick', 'mascara', 'eyeliner'
    }
    
    if index + 1 < len(words) and words[index + 1].lower() in product_types:
        return True
    
    if index == 0:
        return True
    
    if index > 0 and words[index - 1].lower() in ['japan', 'global', 'korean']:
        return True
    
    return True

def extract_quantity(clean_title):
    """商品名から数量・容量を抽出"""
    if not clean_title:
        return ""
    
    quantity_patterns = [
        r'(\d+(?:\.\d+)?)\s*ml\b',
        r'(\d+(?:\.\d+)?)\s*l\b',
        r'(\d+(?:\.\d+)?)\s*mg\b',
        r'(\d+(?:\.\d+)?)\s*g\b',
        r'(\d+(?:\.\d+)?)\s*kg\b',
        r'(\d+)\s*個\b',
        r'(\d+)\s*本\b',
        r'(\d+)\s*枚\b',
        r'(\d+)\s*袋\b',
        r'(\d+)\s*箱\b',
        r'(\d+)\s*セット\b',
        r'(\d+)\s*pack\b',
        r'(\d+)\s*piece\b',
        r'(\d+)\s*count\b',
        r'(\d+(?:\.\d+)?)\s*oz\b',
        r'(\d+(?:\.\d+)?)\s*fl\s*oz\b',
        r'(\d+(?:\.\d+)?)\s*lb\b',
        r'(\d+)\s*inch\b',
        r'(\d+)\s*cm\b',
        r'(\d+)\s*mm\b',
        r'(\d+)\s*gb\b',
        r'(\d+)\s*tb\b',
        r'(\d+ml\*\d+)',
        r'(\d+ml\s*×\s*\d+)',
        r'(\d+ml\s*x\s*\d+)',
    ]
    
    for pattern in quantity_patterns:
        match = re.search(pattern, clean_title.lower())
        if match:
            return match.group(0)
    
    return ""

def extract_product_name(clean_title, brand="", quantity=""):
    """商品名からブランドと数量を除いた本来の商品名を抽出"""
    if not clean_title:
        return ""
    
    product_name = clean_title
    
    if brand:
        brand_pattern = re.escape(brand.lower())
        product_name = re.sub(f"\\b{brand_pattern}\\b", "", product_name.lower(), flags=re.IGNORECASE)
    
    if quantity:
        quantity_pattern = re.escape(quantity.lower())
        product_name = re.sub(quantity_pattern, "", product_name, flags=re.IGNORECASE)
    
    cleanup_patterns = [
        r'\bjapan\b', r'\bjapanese\b', r'\bkorea\b', r'\bkorean\b',
        r'\bglobal\b', r'\binternational\b',
        r'\bnew\b', r'\bused\b', r'\brefurbished\b', r'\bcertified\b', 
        r'\boriginal\b', r'\bgenuine\b', r'\bauthentic\b',
        r'\bblack\b', r'\bwhite\b', r'\bred\b', r'\bblue\b', r'\bgreen\b', 
        r'\byellow\b', r'\bpink\b', r'\bgray\b', r'\bgrey\b', r'\bsilver\b', r'\bgold\b',
        r'\bfree\s*shipping\b', r'\bfast\s*shipping\b', r'\bshipping\s*included\b',
        r'\bpopular\b', r'\bsafety\b', r'\bmade\s*in\b',
        r'\s+',
    ]
    
    for pattern in cleanup_patterns:
        product_name = re.sub(pattern, " ", product_name, flags=re.IGNORECASE)
    
    product_name = re.sub(r'\s+', ' ', product_name).strip()
    
    return product_name if product_name else clean_title

def extract_all_info(clean_title):
    """商品名から全ての情報を一括抽出"""
    brand = extract_brand(clean_title)
    quantity = extract_quantity(clean_title)
    product_name = extract_product_name(clean_title, brand, quantity)
    
    return {
        "brand": brand,
        "quantity": quantity,
        "product_name": product_name,
        "clean_title": clean_title
    }

def test_brand_extraction():
    """ブランド抽出のテスト関数"""
    test_cases = [
        "japan fancl mild cleansing oil 120ml*2",
        "japan orbis essence hair milk 140g hair care liquid hair treatment",
        "lebel iau serum cleansing shampoo 1000ml / cream treatment 1000ml",
        "milbon elujuda bleach care gel serum 120g/essence/for bleached hair/leave-in treatment",
        "yolu calm night repair relax night repair deep night repair night beauty hair care",
        "global milbon scalp purifying gel shampoo 1000ml",
        "tsubaki premium moist shampoo 490ml",
        "essential smart blow dry shampoo 200ml",
        "ichikami moisturizing shampoo 480ml"
    ]
    
    print("=== ブランド抽出テスト（brands.json使用） ===")
    
    for title in test_cases:
        result = extract_all_info(title)
        print(f"\nタイトル: {title}")
        print(f"ブランド: {result['brand']}")
        print(f"数量: {result['quantity']}")
        print(f"商品名: {result['product_name']}")

if __name__ == "__main__":
    test_brand_extraction()