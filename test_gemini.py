import os
import google.generativeai as genai

API_KEY = os.getenv("GEMINI_API_KEY")
print("APIキー:", API_KEY[:8], "...", API_KEY[-4:])  # セキュリティ上、先頭と末尾だけ表示

genai.configure(api_key=API_KEY)

try:
    model = genai.GenerativeModel("gemini-2.5-pro")
    res = model.generate_content("Translate 'apple' to Japanese.")
    print("応答:", res.text)
except Exception as e:
    print("エラー:", e)
