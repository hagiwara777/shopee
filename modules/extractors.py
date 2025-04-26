import re
import json
from pathlib import Path

def load_brand_dict():
    path = Path(__file__).resolve().parents[1] / "data" / "brands.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def extract_brand(text, brand_list):
    """
    テキストからブランド名を抽出する（最終改善版）
    - 最も長いマッチを選択して精度を向上
    - 英語名・日本語名両方を検索
    - 各ブランドの出現位置も考慮
    """
    if not text or not isinstance(text, str):
        return ""
        
    text = text.lower()
    matches = []
    
    for entry in brand_list:
        # 英語名も検索対象に追加
        variations = entry.get("variations", []).copy()
        if "english_name" in entry and entry["english_name"].lower() not in [v.lower() for v in variations]:
            variations.append(entry["english_name"])
        if "japanese_name" in entry and entry["japanese_name"].lower() not in [v.lower() for v in variations]:
            variations.append(entry["japanese_name"])
            
        for variant in variations:
            variant_lower = variant.lower()
            # 単語境界（スペースや文字列の始まり/終わり）で囲まれていることを確認
            position = text.find(variant_lower)
            if position >= 0:
                # 単語の前後が単語境界かチェック
                before_ok = position == 0 or not text[position-1].isalnum()
                after_pos = position + len(variant_lower)
                after_ok = after_pos >= len(text) or not text[after_pos].isalnum()
                
                if before_ok and after_ok:
                    # ブランド名、文字列の長さ、出現位置を記録
                    # 出現位置が早いほど重要なブランドと判断
                    matches.append((entry["english_name"], len(variant_lower), position, variant_lower))
    
    # マッチした場合：
    # 1. 最長一致
    # 2. 出現位置が早いもの
    if matches:
        # 長さ優先でソート、同じ長さなら位置が早いものを優先
        matches.sort(key=lambda x: (-x[1], x[2]))
        return matches[0][0]
    
    return ""

def extract_quantity(text):
    """
    テキストから数量情報を抽出する（最終改善版）
    - より多くの単位パターンに対応
    - SPFなどの特殊表記は除外
    """
    if not text or not isinstance(text, str):
        return ""
        
    # 共通の単位パターン（日本語・英語混在）
    units = r"(?:ml|mL|g|mg|kg|oz|pcs|sheet|sheets|pack|packs|個|枚|本|回分|錠|包|capsules|tablets|pieces|bottles|sets|units)"
    
    # 複数のパターンを試行（優先順位順）
    patterns = [
        # 数字 + 単位（スペースあり・なし）
        fr"(\d+[\.\,]?\d*\s*{units})",
        # xx-xx ml のような範囲表記
        fr"(\d+\s*[-~]\s*\d+\s*{units})",
        # 数字 x 数字形式（例：2 x 50ml）
        fr"(\d+\s*x\s*\d+[\.\,]?\d*\s*{units})",
        # 特定の表現（例：2本セット）
        r"(\d+\s*(?:本|個|枚|包|袋)(?:\s*セット)?)",
        # パーセント表記（例：10%）- 化粧品以外では不要かも
        r"(\d+[\.\,]?\d*\s*\%)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    
    return ""

def extract_product_name(text, brand=None, quantity=None):
    """
    ブランド名と数量を除いた残りの部分を商品名として抽出（最終改善版）
    - エスケープ処理を強化
    - 複数回の置換で確実に削除
    - 共通の不要表現も削除
    """
    if not text or not isinstance(text, str):
        return ""
        
    result = text
    
    # ブランド名を削除（あれば）
    if brand and brand.strip():
        # 大文字小文字を区別せずに削除（完全一致）
        try:
            pattern = r'\b' + re.escape(brand) + r'\b'
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)
        except:
            # 万が一エラーになった場合は単純置換
            result = result.replace(brand, "")
    
    # 数量を削除（あれば）
    if quantity and quantity.strip():
        # 数量表記を削除
        result = result.replace(quantity, "")
    
    # 一般的な不要表現を削除
    unwanted = [
        "新品", "未開封", "未使用品", "送料無料", "正規品", "国内正規品", 
        "100%正規品", "100% authentic", "in stock", "ship from japan"
    ]
    for expr in unwanted:
        result = re.sub(re.escape(expr), "", result, flags=re.IGNORECASE)
    
    # SPF/PA表記は残す（重要な情報のため）
    
    # 余分なスペースを整理
    result = re.sub(r'\s+', ' ', result).strip()
    
    # 先頭と末尾の特殊文字を削除
    result = result.strip('.,;:- 　')
    
    return result