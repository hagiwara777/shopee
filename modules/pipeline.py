import pandas as pd
import re
from modules.extractors import load_brand_dict, extract_brand, extract_quantity, extract_product_name

def check_ng_words(df, ng_words, *, whole_word=True):
    if "clean_title" not in df.columns:
        raise KeyError("'clean_title' カラムが必要です")
    safe_words = [re.escape(w.strip()) for w in ng_words if w and w.strip()]
    if not safe_words:
        df["flag_ngword"] = False
        df["検出NGワード"] = ""
        return df
    if whole_word:
        pattern = re.compile("|".join(fr"\b{w}\b" for w in safe_words), re.IGNORECASE)
    else:
        pattern = re.compile("|".join(safe_words), re.IGNORECASE)
    flags, hits = [], []
    for title in df["clean_title"].fillna(""):
        matched = pattern.findall(str(title))
        flags.append(bool(matched))
        hits.append(", ".join(sorted(set(matched))))
    df["flag_ngword"] = flags
    df["検出NGワード"] = hits
    return df

def run_pipeline(df, title_col="Name", thresh=0.9, rep_rule="shortest", keep_cols=None, col_order=None, ng_category=None):
    df = df.copy()
    
    # Locationカラムが存在する場合、Japanのデータのみを保持
    if "Location" in df.columns:
        df = df[df["Location"] == "Japan"]
    
    # 不要なカラムを除外
    exclude_cols = ["Cost", "Source", "No.", "Country"]
    for col in exclude_cols:
        if col in df.columns:
            df = df.drop(columns=[col])
    
    # クリーニングして商品情報を抽出
    df["clean_title"] = df[title_col].astype(str)
    brand_dict = load_brand_dict()
    df["brand"] = df["clean_title"].apply(lambda x: extract_brand(x, brand_dict))
    df["quantity"] = df["clean_title"].apply(extract_quantity)
    df["product_name"] = df.apply(lambda row: extract_product_name(row["clean_title"], row["brand"], row["quantity"]), axis=1)
    
    # NGワードチェック
    with open("data/ng_words.txt", encoding="utf-8") as f:
        ng_words = [line.strip() for line in f if line.strip()]
    df = check_ng_words(df, ng_words, whole_word=True)
    
    # カラムの指定があれば選択
    if keep_cols:
        df = df[[c for c in keep_cols if c in df.columns]]
    
    # デフォルトのカラム順序を設定
    default_col_order = ["clean_title", "brand", "product_name", "quantity"]
    
    if col_order:
        # 指定された順序で並べ替え
        df = df.reindex(columns=[c for c in col_order if c in df.columns])
    else:
        # 標準順序で並べ替え
        existing_default_columns = [c for c in default_col_order if c in df.columns]
        other_columns = [c for c in df.columns if c not in default_col_order]
        df = df.reindex(columns=existing_default_columns + other_columns)
    
    return df

def save_with_highlight(df: pd.DataFrame, output_path: str):
    # デフォルトカラム順序を保証
    default_col_order = ["clean_title", "brand", "product_name", "quantity"]
    
    # 存在する列だけを選択
    existing_default_columns = [c for c in default_col_order if c in df.columns]
    other_columns = [c for c in df.columns if c not in default_col_order]
    
    # 最終的な列順序を設定
    df = df.reindex(columns=existing_default_columns + other_columns)
    
    def highlight_row(row):
        if row.get("flag_ngword", False):
            return ["background-color: #FFCCCC"] * len(row)
        return ["" for _ in row]
    
    styled = df.style.apply(highlight_row, axis=1)
    styled.to_excel(output_path, index=False, engine="xlsxwriter")