import sqlite3
import hashlib
import time
import os
import google.generativeai as genai
import requests

CACHE_DB_PATH = "data/translation_cache.db"
CACHE_EXPIRY_SECONDS = 60 * 60 * 24 * 30  # 30日

class TranslationCache:
    def __init__(self, db_path=CACHE_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS translations (
                    english_name_hash TEXT PRIMARY KEY,
                    english_name TEXT,
                    japanese_name TEXT,
                    timestamp INTEGER
                )
            ''')
            conn.commit()

    def get_translation(self, english_name):
        if not english_name:
            return None
        query_hash = hashlib.md5(english_name.encode()).hexdigest()
        min_timestamp = int(time.time()) - CACHE_EXPIRY_SECONDS
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT japanese_name FROM translations WHERE english_name_hash = ? AND timestamp >= ?",
                (query_hash, min_timestamp)
            )
            result = cursor.fetchone()
        return result[0] if result else None

    def add_translation(self, english_name, japanese_name):
        if not english_name or not japanese_name:
            return
        query_hash = hashlib.md5(english_name.encode()).hexdigest()
        timestamp = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO translations (english_name_hash, english_name, japanese_name, timestamp) VALUES (?, ?, ?, ?)",
                (query_hash, english_name, japanese_name, timestamp)
            )
            conn.commit()

    def close(self):
        pass  # with構文で自動closeされるため

# APIキー読み込み
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("警告: GEMINI_API_KEYが設定されていません。")

translation_cache = TranslationCache()

def get_japanese_name_from_gemini(english_name: str, max_retry=3, sleep_sec=2) -> tuple[str, str]:
    """
    戻り値: (日本語名, エラー分類+詳細) または (日本語名, "") ←正常時
    """
    if not english_name:
        return ("", "入力空欄")
    cached = translation_cache.get_translation(english_name)
    if cached:
        return (cached, "")
    last_error = ""
    for attempt in range(max_retry):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            あなたは日本のECサイト担当者です。下記「英語の商品名」を分析し、日本市場向けの自然な「日本語の商品名」を一語で出力してください。ブランド名・数量も自然な日本語で、説明不要。
            英語の商品名: "{english_name}"
            日本語の商品名:
            """
            response = model.generate_content(prompt)
            japanese_name = response.text.strip()
            if not japanese_name:
                last_error = "空レスポンス"
                raise ValueError("空レスポンス")
            translation_cache.add_translation(english_name, japanese_name)
            return (japanese_name, "")
        except Exception as e:
            # エラー分類
            error_type = "未分類エラー"
            message = str(e)
            if hasattr(e, 'status_code'):
                if e.status_code == 429:
                    error_type = "レートリミット（429）"
                elif e.status_code == 401:
                    error_type = "認証エラー（401）"
            elif isinstance(e, requests.exceptions.ConnectionError):
                error_type = "ネットワークエラー"
            elif isinstance(e, ValueError) and last_error == "空レスポンス":
                error_type = "空レスポンス"
            elif "429" in message:
                error_type = "レートリミット（429）"
            elif "401" in message:
                error_type = "認証エラー（401）"
            last_error = f"{error_type}: {message}"
            time.sleep(sleep_sec)
    return ("(APIエラー)", last_error or "API未分類エラー")
