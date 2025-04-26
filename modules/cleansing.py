import unicodedata
import re
from pathlib import Path

def normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text).lower()

    # 括弧・記号類の除去（例：[], (), 【】）
    text = re.sub(r"[\[\]【】()（）]", "", text)

    # 特定の記号や絵文字の除去（🅹🅿🇯🇵など）
    emoji_pattern = re.compile("[🅹🅿🇯🇵]", flags=re.UNICODE)
    text = emoji_pattern.sub("", text)

    # ignore_phrases の除去
    ignore_path = Path(__file__).resolve().parents[1] / "data" / "ignore_phrases.txt"
    if ignore_path.exists():
        ignore_phrases = ignore_path.read_text(encoding="utf-8").splitlines()
        for phrase in ignore_phrases:
            phrase = phrase.strip().lower()
            text = re.sub(re.escape(phrase), "", text)

    return text.strip()