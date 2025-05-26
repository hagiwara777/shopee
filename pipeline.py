import pandas as pd
import re
from pandas import ExcelWriter
from pathlib import Path
import streamlit as st
from modules.extractors import load_brand_dict, extract_brand, extract_quantity, extract_product_name
from modules.llm_service import get_japanese_name_hybrid
from modules.spapi_service import search_asin_by_title
from modules.cleansing import normalize
import io
import traceback

def check_ng_words(df, ng_words, *, whole_word=True):
    check_column = 'clean_title'
    if check_column not in df.columns:
        df["flag_ngword"] = False
        df["検出NGワード"] = ""
        return df
    safe_words = [re.escape(w.strip()) for w in ng_words if w and w.strip()]
    if not safe_words:
        df["flag_ngword"] = False
        df["検出NGワード"] = ""
        return df
    if whole_word:
        pattern = re.compile("|".join(fr"\b{w}\b" for w in safe_words), re.IGNORECASE)
    else:
        pattern = re.compile("|".join(safe_words), re.IGNORECASE)
    flags = []
    hits = []
    for title in df[check_column].fillna("").astype(str):
        matched = pattern.findall(title)
        flags.append(bool(matched))
        hits.append(", ".join(sorted(list(set(matched)), key=str.lower)))
    df["flag_ngword"] = flags
    df["検出NGワード"] = hits
    return df

def run_pipeline(df, title_col="Name", ng_words=None):
    df = df.copy()

    # 不要カラム除去
    exclude_cols = ["Cost", "Source", "No.", "Country"]
    cols_to_drop = [col for col in exclude_cols if col in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # clean_title作成
    df["clean_title"] = df[title_col].apply(normalize) if title_col in df.columns else df[title_col]

    # ブランド・数量・商品名
    brand_dict = load_brand_dict()
    df["brand"] = df["clean_title"].apply(lambda x: extract_brand(x, brand_dict))
    df["quantity"] = df["clean_title"].apply(extract_quantity)
    df["product_name"] = df.apply(lambda row: extract_product_name(row["clean_title"], row.get('brand'), row.get('quantity')), axis=1)

    # NGワード
    if ng_words:
        df = check_ng_words(df, ng_words, whole_word=True)

    # 日本語化（ハイブリッドLLM）
    df["japanese_name"] = ""
    df["llm_source"] = ""
    for idx, row in df.iterrows():
        name = row["clean_title"]
        jp, src = get_japanese_name_hybrid(name)
        df.at[idx, "japanese_name"] = jp
        df.at[idx, "llm_source"] = src

    # ASIN検索
    df["ASIN"] = ""
    for idx, row in df.iterrows():
        jp_name = row["japanese_name"]
        asin = search_asin_by_title(jp_name)
        df.at[idx, "ASIN"] = asin

    # カラム順を指定
    col_order = [
        "ASIN",
        "clean_title",
        "検出NGワード",
        "brand",
        "product_name",
        "quantity"
    ]
    # 残りのカラムを後ろに追加
    remain_cols = [c for c in df.columns if c not in col_order]
    final_cols = col_order + remain_cols
    df = df.reindex(columns=final_cols)
    return df

def save_with_highlight(df: pd.DataFrame, out_path: str):
    with ExcelWriter(out_path, engine='xlsxwriter') as writer:
        sheet_name = 'Sheet1'
        df.to_excel(writer, sheet_name=sheet_name, index=False, header=True)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        # 書式などは必要に応じて追加可能（省略可）
    print(f"Excel出力完了: {out_path}")
