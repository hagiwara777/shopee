# modules/cleansing.py (修正版 - 特定の絵文字削除を追加)

import unicodedata
import re
from pathlib import Path

# dataディレクトリのパスを取得 (修正)
# __file__ はこのファイル(cleansing.py)のパス
# .resolve() で絶対パスに変換
# .parents[1] で一つ上のディレクトリ (modules/ の親 = プロジェクトルート)
# そこから "data" フォルダを結合
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def normalize(text: str) -> str:
    """
    文字列を正規化し、不要な文字やフレーズを削除する関数。
    NFKC正規化、小文字化、括弧・特定記号・絵文字の除去、
    ignore_phrases.txt に記載されたフレーズの除去を行う。
    """
    if not isinstance(text, str):
        return "" # 文字列でない場合は空文字を返す

    # NFKC正規化と小文字化
    try:
        # unicodedata.normalize は str のみ受け付ける
        text_normalized = unicodedata.normalize("NFKC", str(text)).lower()
    except TypeError:
        # 万が一、str() に変換できないオブジェクトが来た場合（通常はありえないが）
        return ""

    # --- ここから文字削除処理 ---

    # 1. 括弧・記号類の除去（例：[], (), 【】）
    text_cleaned = re.sub(r"[\[\]【】()（）]", "", text_normalized)

    # 2. 特定の記号や絵文字の除去（指定された ✨🔥🍑🎉 と、前回定義した 🅹🅿🇯🇵）
    #    削除したい文字を [] の中に追加していく
    specific_chars_to_remove = r"[✨🔥🍑🎉🅹🅿🇯🇵]"
    text_cleaned = re.sub(specific_chars_to_remove, "", text_cleaned, flags=re.UNICODE)

    # 3. 無視リスト (ignore_phrases.txt) の除去
    ignore_path = DATA_DIR / "ignore_phrases.txt" # 正しいパスを使用
    if ignore_path.exists():
        try:
            # まずUTF-8で試す
            ignore_phrases = ignore_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            try:
                # Shift-JISで試す
                print(f"警告: {ignore_path} のUTF-8読み込み失敗。Shift-JISで試行します。")
                ignore_phrases = ignore_path.read_text(encoding="shift_jis").splitlines()
            except Exception as read_e:
                print(f"警告: {ignore_path} の読み込みに失敗しました: {read_e}")
                ignore_phrases = [] # 読み込めない場合はリストを空にする
        except Exception as e:
             print(f"警告: {ignore_path} の読み込み中に予期せぬエラー: {e}")
             ignore_phrases = []

        # フレーズ除去処理
        for phrase in ignore_phrases:
            phrase_clean = phrase.strip()
            if phrase_clean: # 空行は無視
                try:
                    # re.escapeで正規表現の特殊文字をエスケープし、IGNORECASEで大文字小文字無視
                    text_cleaned = re.sub(re.escape(phrase_clean.lower()), "", text_cleaned, flags=re.IGNORECASE)
                except re.error as re_err:
                    print(f"警告: ignore_phrases.txt 内のフレーズ '{phrase_clean}' の正規表現処理でエラー: {re_err}。単純置換を試みます。")
                    # 正規表現エラーの場合は、単純な文字列置換で試みる（大文字小文字無視はできない）
                    text_cleaned = text_cleaned.replace(phrase_clean.lower(), "")
    else:
        print(f"警告: {ignore_path} が見つかりません。フレーズ除去をスキップします。")


    # 4. 最後に前後の空白を削除
    return text_cleaned.strip()