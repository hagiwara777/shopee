import streamlit as st
import pandas as pd
from modules.extractors import load_brands, get_preferred_brand_name

st.title("Shopee自動リサーチ出品ツール（ブランド優先度検索デモ）")

# ファイルアップロード欄
uploaded_file = st.file_uploader("商品リストCSVをアップロードしてください", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("アップロードデータのプレビュー:", df.head())

    # brands.jsonのロード
    brands = load_brands()

    # ブランド検索用列が何か選ばせる（例：Brand, ブランド, brand_name等）
    brand_col = st.selectbox("ブランド名カラムを選択してください", df.columns.tolist())

    # 新しい列を作成
    df["SP-API検索用ブランド名"] = df[brand_col].apply(
        lambda b: get_preferred_brand_name(brands.get(str(b), [str(b)]))
    )

    st.write("ブランド優先度判定後のサンプル:")
    st.dataframe(df[[brand_col, "SP-API検索用ブランド名"]].head(20))

    # ダウンロードリンク
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("変換後CSVをダウンロード", csv, file_name="output_with_spapi_brand.csv", mime="text/csv")

else:
    st.info("CSVファイルをアップロードしてください。")

# ※ このサンプルは「SP-API検索用ブランド名」を決める部分まで。  
#   実際のAPI連携・出品処理等は別途ロジックを追加してください。
