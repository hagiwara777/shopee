import openai
import google.generativeai as genai
import os

def get_japanese_name_from_gpt4o(clean_title):
    api_key = os.getenv("OPENAI_API_KEY")
    client = openai.OpenAI(api_key=api_key)
    prompt = f"次の英語の商品名を、日本のECサイトで通じる自然な日本語の商品名に翻訳してください。ブランドや容量も日本語で表記し、説明や余計な語句は不要：\n\n{clean_title}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=64,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

def get_japanese_name_from_gemini(clean_title):
    api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    prompt = f"次の英語の商品名を、日本語の商品名に自然に翻訳してください。ブランドや容量も自然な日本語で。余計な説明不要：\n\n{clean_title}"
    response = model.generate_content(prompt)
    return response.text.strip()

def get_japanese_name_hybrid(clean_title):
    try:
        jp_name = get_japanese_name_from_gpt4o(clean_title)
        if jp_name and not jp_name.isspace() and "変換不可" not in jp_name:
            return jp_name, "GPT-4o"
    except Exception as e:
        print(f"GPT-4o失敗: {e}")
    try:
        jp_name = get_japanese_name_from_gemini(clean_title)
        return jp_name, "Gemini"
    except Exception as e:
        print(f"Gemini失敗: {e}")
        return "(変換不可)", "None"
