# pipeline.py (完全版 - Excel書式設定 修正済み)

import pandas as pd
import re
# 'ExcelWriter' を pandas からインポート
from pandas import ExcelWriter
# pathlib をインポート (load_brand_dict で使われている可能性を考慮)
from pathlib import Path
# 必要な関数を modules.extractors からインポート
from modules.extractors import load_brand_dict, extract_brand, extract_quantity, extract_product_name

def check_ng_words(df, ng_words, *, whole_word=True):
    """
    DataFrameの 'clean_title' 列をチェックし、NGワードが含まれているかどうかのフラグと
    検出されたNGワードのリストを新しい列として追加する関数。
    """
    if "clean_title" not in df.columns:
        raise KeyError("'clean_title' カラムが必要です")

    # NGワードリストが空か、有効な単語がない場合は処理をスキップ
    safe_words = [re.escape(w.strip()) for w in ng_words if w and w.strip()]
    if not safe_words:
        df["flag_ngword"] = False
        df["検出NGワード"] = ""
        return df

    # パターンを生成（完全一致モードかどうかで分岐）
    if whole_word:
        # \b は単語の境界を示す正規表現
        pattern = re.compile("|".join(fr"\b{w}\b" for w in safe_words), re.IGNORECASE)
    else:
        pattern = re.compile("|".join(safe_words), re.IGNORECASE)

    flags = []
    hits = []
    # 'clean_title' 列の各タイトルに対してNGワード検索を実行
    for title in df["clean_title"].fillna(""): # NaN値は空文字として扱う
        # 文字列でない場合は空文字に変換してから検索
        matched = pattern.findall(str(title))
        flags.append(bool(matched)) # マッチしたらTrue
        # マッチした単語を重複なくソートしてカンマ区切りで結合
        hits.append(", ".join(sorted(set(matched))))

    # 結果をDataFrameに追加
    df["flag_ngword"] = flags
    df["検出NGワード"] = hits
    return df

def run_pipeline(df, title_col="Name", thresh=0.9, rep_rule="shortest", keep_cols=None, col_order=None, ng_category=None):
    """
    データ処理パイプラインを実行するメイン関数。
    フィルタリング、クレンジング、情報抽出、NGワードチェック、カラム整理を行う。
    """
    # 元のDataFrameを壊さないようにコピーを作成
    df = df.copy()

    # Locationカラムが存在する場合、Japanのデータのみを保持
    if "Location" in df.columns:
        df = df[df["Location"] == "Japan"]

    # 不要なカラムを除外 (Cost, Source, No., Country)
    exclude_cols = ["Cost", "Source", "No.", "Country"]
    for col in exclude_cols:
        if col in df.columns:
            df = df.drop(columns=[col])

    # クリーニングして商品情報を抽出
    # 指定されたタイトル列が存在するか確認
    if title_col not in df.columns:
         raise KeyError(f"指定されたタイトル列 '{title_col}' がDataFrameに存在しません。列名を確認してください。")
    # clean_title 列を作成 (元のタイトル列を文字列に変換)
    df["clean_title"] = df[title_col].astype(str)

    # ブランド辞書を読み込み、ブランド名、数量、商品名を抽出して列に追加
    brand_dict = load_brand_dict()
    df["brand"] = df["clean_title"].apply(lambda x: extract_brand(x, brand_dict))
    df["quantity"] = df["clean_title"].apply(extract_quantity)
    df["product_name"] = df.apply(lambda row: extract_product_name(row["clean_title"], row["brand"], row["quantity"]), axis=1)

    # NGワードチェック
    # ng_words.txt を読み込み、check_ng_words 関数を実行
    try:
        # dataフォルダにある ng_words.txt を想定
        ng_words_path = Path("data/ng_words.txt")
        if ng_words_path.exists():
             with open(ng_words_path, encoding="utf-8") as f:
                ng_words = [line.strip() for line in f if line.strip()]
             df = check_ng_words(df, ng_words, whole_word=True)
        else:
            print("警告: data/ng_words.txt が見つかりません。NGワードチェックをスキップします。")
            df["flag_ngword"] = False
            df["検出NGワード"] = ""
    except Exception as e:
        print(f"警告: NGワードファイルの読み込みまたはチェック中にエラーが発生しました: {e}")
        df["flag_ngword"] = False
        df["検出NGワード"] = ""

    # カラムの指定があれば選択 (存在する列のみ)
    if keep_cols:
        existing_keep_cols = [c for c in keep_cols if c in df.columns]
        df = df[existing_keep_cols]

    # デフォルトのカラム順序を設定
    default_col_order = ["clean_title", "brand", "product_name", "quantity"]

    # カラム順序の指定があれば適用、なければデフォルト順序を適用 (存在する列のみ)
    if col_order:
        existing_col_order = [c for c in col_order if c in df.columns]
        # 指定された順序に含まれない他の列も保持する
        other_columns = [c for c in df.columns if c not in existing_col_order]
        df = df.reindex(columns=existing_col_order + other_columns)
    else:
        existing_default_columns = [c for c in default_col_order if c in df.columns]
        other_columns = [c for c in df.columns if c not in default_col_order]
        df = df.reindex(columns=existing_default_columns + other_columns)

    return df

def save_with_highlight(df: pd.DataFrame, output_path: str):
    """
    DataFrameをExcelファイルに保存し、特定の書式設定（折り返し、列幅）と
    NGワード行のハイライトを適用する関数（xlsxwriterを使用）。
    """
    print(f"'{output_path}' への保存を開始します...")
    try:
        # ExcelWriterオブジェクトを作成 (mode='w' でファイルを新規作成または上書き)
        with ExcelWriter(output_path, engine='xlsxwriter', mode='w') as writer:
            # スタイルなしでDataFrameを 'Sheet1' に書き込む (ヘッダーは書き込む、インデックスは書き込まない)
            df.to_excel(writer, sheet_name='Sheet1', index=False, header=True)

            # WorkbookとWorksheetオブジェクトを取得
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']

            # --- 書式設定 ---
            # 1. 折り返し書式を作成 (縦位置も上揃えに)
            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

            # 2. NGワード行のハイライト用書式を作成（折り返し・上揃えも適用）
            highlight_format = workbook.add_format({'bg_color': '#FFCCCC', 'text_wrap': True, 'valign': 'top'})

            # 3. 列幅の設定
            #    A列(0)とC列(2)の幅を調整 (75は仮の値、必要に応じて調整してください)
            col_width_a = 75
            col_width_c = 75
            worksheet.set_column(0, 0, col_width_a, wrap_format) # A列 (0番目)
            worksheet.set_column(2, 2, col_width_c, wrap_format) # C列 (2番目)

            # 他の列も必要であれば幅を設定 (例: B列も少し広げる)
            # worksheet.set_column(1, 1, 20) # B列 (1番目) 幅20

            # --- NGワード行のハイライト適用 ---
            # 'flag_ngword' 列が存在するか確認
            if 'flag_ngword' in df.columns:
                # DataFrameの各行をチェック (インデックスは0から始まる)
                for row_idx in range(len(df)):
                    # iloc を使って行データにアクセスし、flag_ngword の値を取得
                    if df.iloc[row_idx]['flag_ngword']:
                        # Excelの行は1から始まるため、row_idx + 1 で指定
                        # set_row で行全体にハイライト書式を適用 (高さはNone=自動調整)
                        worksheet.set_row(row_idx + 1, None, highlight_format)
            else:
                 print("警告: 'flag_ngword' 列が見つからないため、ハイライトは適用されません。")

        # 'with' ブロックを抜けるときに自動的に保存・クローズされる
        print(f"'{output_path}' に書式設定を適用して正常に保存しました。")

    except Exception as e:
        print(f"エラー: Excelファイル '{output_path}' の保存中に問題が発生しました。")
        print(f"詳細: {e}")