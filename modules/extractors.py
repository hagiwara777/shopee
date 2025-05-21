import re
import json
from pathlib import Path

BRANDS_PATH = Path("data/brands.json")

def load_brands():
    """brands.jsonを読み込んで返す"""
    if BRANDS_PATH.exists():
        with open(BRANDS_PATH, encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}

def get_preferred_brand_name(variations):
    """
    バリエーションリストから「カタカナ＞漢字＞ひらがな＞英字」優先でブランド名を返す
    """
    katakana_re = re.compile(r'[\u30A0-\u30FF]+')
    kanji_re = re.compile(r'[\u4E00-\u9FFF]+')
    hiragana_re = re.compile(r'[\u3040-\u309F]+')
    for name in variations:
        if katakana_re.search(name):
            return name
    for name in variations:
        if kanji_re.search(name):
            return name
    for name in variations:
        if hiragana_re.search(name):
            return name
    for name in variations:
        if re.match(r'^[A-Za-z0-9\s\-&.()]+$', name):
            return name
    return variations[0] if variations else ""

# 他にも必要に応じてextractor関数を追加できます
