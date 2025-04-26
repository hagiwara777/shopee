import streamlit as st
import pandas as pd
from pathlib import Path
from modules.extractors import load_brand_dict, extract_brand, extract_quantity, extract_product_name
from modules.pipeline import check_ng_words, save_with_highlight

st.title("🧹 商品名クレンジング＆NGワードチェックツール")

# ------------------------
# 🚫 NGワード編集 UI
# ------------------------
CATEGORIES = ["", "禁止語", "ブランド名", "著作権", "その他"]
selected_category = st.selectbox("NGワードカテゴリを選択", CATEGORIES, index=0)

def get_ng_file():
    if selected_category:
        return f"data/ng_words_{selected_category}.txt"
    return "data/ng_words.txt"

def load_ng_words():
    path = Path(get_ng_file())
    if path.exists():
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return []

def save_ng_words(words):
    cleaned = sorted(set(w.strip() for w in words if w.strip()))
    Path(get_ng_file()).write_text("\n".join(cleaned), encoding="utf-8")
    return cleaned

with st.expander("✏ NGワード一覧を編集・削除", expanded=False):
    ng_words = load_ng_words()
    df_edit = pd.DataFrame({"NGワード": ng_words})
    edited = st.data_editor(df_edit, num_rows="dynamic")
    if st.button("💾 NGワードを保存"):
        updated_words = edited["NGワード"].dropna().tolist()
        saved = save_ng_words(updated_words)
        st.success(f"{len(saved)} 件のNGワードを保存しました")

with st.expander("➕ NGワードを追加", expanded=False):
    new_word = st.text_input("新しいNGワードを入力")
    if st.button("追加"):
        if new_word.strip():
            current = load_ng_words()
            current.append(new_word.strip())
            saved = save_ng_words(current)
            st.success(f"'{new_word}' を追加しました")
        else:
            st.warning("空のワードは追加できません")

# ------------------------
# ファイル処理
# ------------------------
uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"])
if uploaded_file:
    sheet_name = st.text_input("読み込むシート名", value="データ")
    title_col = st.text_input("商品名の列名", value="Name")

    df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
    if title_col not in df.columns:
        st.error(f"列 '{title_col}' が見つかりません。")
        st.stop()

    # 不要なカラムを除外
    exclude_cols = ["Cost", "Source", "No.", "Country"]
    for col in exclude_cols:
        if col in df.columns:
            df = df.drop(columns=[col])
    
    # Locationカラムが存在する場合、Japanのデータのみを保持
    if "Location" in df.columns:
        df = df[df["Location"] == "Japan"]
        st.info(f"Locationが「Japan」のデータのみ表示しています（{len(df)}件）")

    from modules.cleansing import normalize
    df["clean_title"] = df[title_col].apply(normalize)

    # ブランド辞書読み込みと抽出
    brand_dict = load_brand_dict()
    df["brand"] = df["clean_title"].apply(lambda x: extract_brand(x, brand_dict))
    df["quantity"] = df["clean_title"].apply(extract_quantity)
    df["product_name"] = df.apply(lambda row: extract_product_name(row["clean_title"], row["brand"], row["quantity"]), axis=1)

    # NGワードチェック
    ng_words = load_ng_words()
    whole_word = st.checkbox("🔍 完全一致モード（\\b 単語境界）", value=True)
    df = check_ng_words(df, ng_words, whole_word=whole_word)

    # カラム順序の調整
    column_order = ["clean_title", "brand", "product_name", "quantity"]
    all_columns = column_order + [col for col in df.columns if col not in column_order]
    df = df.reindex(columns=[col for col in all_columns if col in df.columns])
    
    # 結果表示と保存
    st.subheader("📊 プレビュー")
    st.dataframe(df)

    if st.button("💾 Excelファイルとして保存"):
        save_with_highlight(df, "output.xlsx")
        st.success("output.xlsx を保存しました")