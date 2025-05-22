import streamlit as st
import pandas as pd
from pipeline import run_pipeline, save_with_highlight

st.title("ASIN一括日本語化＆検索ツール")
uploaded_file = st.file_uploader("Excel/CSVファイルをアップロード", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    st.write("プレビュー", df.head())

    # NGワードリストは必要に応じてファイル/テキストボックス等から取得
    ng_words = []
    if st.checkbox("NGワードファイル使用", value=False):
        ng_file = st.file_uploader("NGワードリスト(txt)", type=["txt"])
        if ng_file:
            ng_words = ng_file.read().decode("utf-8").splitlines()

    if st.button("日本語化＆ASIN検索を実行"):
        df_result = run_pipeline(df, title_col="Name", ng_words=ng_words)
        st.dataframe(df_result.head())
        # xlsxダウンロード
        save_with_highlight(df_result, "output_with_asin.xlsx")
        st.success("Excel出力しました。output_with_asin.xlsx")
