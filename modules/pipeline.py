# pipeline.py (完全版 - st.download_button対応、normalize呼び出し、LLM連携)

import pandas as pd
import re
# 'ExcelWriter' を pandas からインポート
from pandas import ExcelWriter
# pathlib をインポート
from pathlib import Path
# Streamlit をインポート (進捗表示のため)
import streamlit as st
# 必要な関数をインポート
from modules.extractors import load_brand_dict, extract_brand, extract_quantity, extract_product_name
from modules.llm_service import get_japanese_name_from_gemini # ★ LLMサービスをインポート
from modules.cleansing import normalize # ★★★ normalize 関数をインポート ★★★
import io # ★★★ BytesIO のために io モジュールをインポート ★★★
import traceback # エラー表示用

def check_ng_words(df, ng_words, *, whole_word=True):
    """
    DataFrameの 'clean_title' 列をチェックし、NGワードが含まれているかどうかのフラグと
    検出されたNGワードのリストを新しい列として追加する関数。
    """
    # ★ NGワードチェック対象の列を指定 (デフォルトは clean_title)
    check_column = 'clean_title'

    if check_column not in df.columns:
        print(f"警告: '{check_column}' 列が見つかりません。NGワードチェックをスキップします。")
        # スキップする場合でも列は作成しておく
        df["flag_ngword"] = False
        df["検出NGワード"] = ""
        return df

    # NGワードリストが空か、有効な単語がない場合は処理をスキップ
    safe_words = [re.escape(w.strip()) for w in ng_words if w and w.strip()]
    if not safe_words:
        print("NGワードリストが空のため、NGワードチェックをスキップします。")
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
    # 指定された列の各タイトルに対してNGワード検索を実行
    # fillna("") で NaN を空文字に変換、astype(str) で数値なども文字列に変換
    for title in df[check_column].fillna("").astype(str):
        matched = pattern.findall(title) # 文字列保証されているので str() は不要
        flags.append(bool(matched)) # マッチしたらTrue
        # マッチした単語を重複なくソートしてカンマ区切りで結合
        hits.append(", ".join(sorted(list(set(matched)), key=str.lower))) # setをlistにしてからソート

    # 結果をDataFrameに追加
    df["flag_ngword"] = flags
    df["検出NGワード"] = hits
    return df

def run_pipeline(df, title_col="Name", thresh=0.9, rep_rule="shortest", keep_cols=None, col_order=None, ng_category=None):
    """
    データ処理パイプラインを実行するメイン関数。
    フィルタリング、クレンジング、情報抽出、★NGワードチェック(英語)★、日本語名特定(LLM)、カラム整理を行う。
    """
    # 元のDataFrameを壊さないようにコピーを作成
    df = df.copy()
    print("パイプライン処理を開始します...")
    st.write("パイプライン処理を開始します...") # Streamlitにも表示

    # Locationカラムが存在する場合、Japanのデータのみを保持
    if "Location" in df.columns:
        original_count = len(df)
        print(f"処理前件数: {original_count}")
        df = df[df["Location"] == "Japan"].copy() # .copy() を追加して SettingWithCopyWarning 回避
        filtered_count = len(df)
        print(f"Location='Japan' でフィルタリング後件数: {filtered_count}")
        st.write(f"Location='Japan' でフィルタリング: {original_count}件 → {filtered_count}件")

    # 不要なカラムを除外 (Cost, Source, No., Country)
    exclude_cols = ["Cost", "Source", "No.", "Country"]
    cols_to_drop = [col for col in exclude_cols if col in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        print(f"不要なカラム {cols_to_drop} を削除しました。")
        st.write(f"不要なカラム {cols_to_drop} を削除。")


    # 指定されたタイトル列が存在するか確認
    if title_col not in df.columns:
         message = f"指定されたタイトル列 '{title_col}' がDataFrameに存在しません。列名を確認してください。利用可能な列: {df.columns.tolist()}"
         print(f"エラー: {message}")
         st.error(message)
         raise KeyError(message) # エラーで処理を中断

    print(f"'{title_col}' 列を基準にクレンジングと情報抽出を開始...")
    st.write(f"'{title_col}' 列のクレンジング処理を開始...") # メッセージ変更

    # ★★★ clean_title 列を作成する際に normalize を適用 ★★★
    try:
        df["clean_title"] = df[title_col].apply(normalize)
        print("normalize 関数によるクレンジング完了。")
        st.write("基本的なクレンジング完了 (normalize 適用)。")
    except Exception as norm_e:
        print(f"エラー: normalize 関数適用中に問題が発生しました: {norm_e}")
        st.warning(f"クレンジング処理中にエラーが発生しました。一部の不要語句が残る可能性があります。詳細: {norm_e}")
        # エラーが起きても処理を続けるため、元のタイトルを文字列化して使う
        df["clean_title"] = df[title_col].fillna("").astype(str)


    # ブランド辞書を読み込み、ブランド名、数量、商品名を抽出して列に追加
    try:
        print("ブランド辞書を読み込んでいます...")
        brand_dict = load_brand_dict()
        print("ブランド名を抽出しています...")
        df["brand"] = df["clean_title"].apply(lambda x: extract_brand(x, brand_dict))
        print("数量を抽出しています...")
        df["quantity"] = df["clean_title"].apply(extract_quantity)
        print("商品名を抽出しています...")
        # product_name の抽出では brand と quantity を使うため、それらが存在するか確認
        df["product_name"] = df.apply(lambda row: extract_product_name(row["clean_title"], row.get('brand'), row.get('quantity')), axis=1)
        print("ブランド、数量、商品名の抽出完了。")
        st.write("ブランド、数量、商品名の抽出完了。")
    except FileNotFoundError as e:
         message = f"エラー: ブランド辞書ファイルが見つかりません。 'data/brands.json' を確認してください。詳細: {e}"
         print(message)
         st.error(message)
         raise # エラーで処理を中断
    except Exception as e:
        message = f"エラー: ブランド辞書の読み込みまたは情報抽出中に問題が発生しました - {e}"
        print(message)
        st.error(message)
        # エラーが発生しても、最低限の列は作成しておく
        df["brand"] = ""
        df["quantity"] = ""
        df["product_name"] = df["clean_title"] # 最悪、clean_title をそのまま使う

    # ===== ★★★ NGワードチェック (clean_title に対して実行) ★★★ =====
    print("NGワードチェックを開始します...")
    st.write("NGワードチェックを開始します...")
    try:
        # ここでNGワードファイルを決定するロジックを追加（app.pyから渡されたカテゴリを使うなど）
        # 現状は data/ng_words.txt 固定
        ng_words_path = Path("data/ng_words.txt")
        if ng_words_path.exists():
             # エンコーディングを試す (UTF-8 -> Shift_JIS)
             try:
                 ng_words = ng_words_path.read_text(encoding="utf-8").splitlines()
             except UnicodeDecodeError:
                 try:
                     print("UTF-8での読み込み失敗。Shift_JISで試行します。")
                     ng_words = ng_words_path.read_text(encoding="shift_jis").splitlines()
                 except Exception as read_e:
                     raise Exception(f"NGワードファイルの読み込みに失敗しました (UTF-8, Shift_JIS): {read_e}")

             ng_words = [line.strip() for line in ng_words if line.strip()]
             print(f"{len(ng_words)} 件のNGワードを読み込みました。")
             df = check_ng_words(df, ng_words, whole_word=True) # check_ng_words は clean_title に対して実行
             print("NGワードチェック完了。")
             st.write("NGワードチェック完了。")
        else:
            print(f"警告: {ng_words_path} が見つかりません。NGワードチェックをスキップします。")
            st.warning(f"{ng_words_path} が見つからないため、NGワードチェックはスキップされました。")
            # スキップする場合でも列は作成しておく
            df["flag_ngword"] = False
            df["検出NGワード"] = ""
    except Exception as e:
        message = f"警告: NGワードファイルの読み込みまたはチェック中にエラーが発生しました: {e}"
        print(message)
        st.warning(message)
        df["flag_ngword"] = False
        df["検出NGワード"] = ""
    # ===== ★★★ ここまでNGワードチェック ★★★ =====

    # ===== ★★★ 日本語商品名取得処理 (LLM連携) ★★★ =====
    print("日本語商品名の取得処理を開始します (LLM API + Cache)...")
    st.info("LLM API を使用して日本語商品名を取得します...(キャッシュ利用)") # Streamlit画面に進捗表示
    total_rows = len(df)
    # 'japanese_name' 列がなければ作成、あれば初期化
    df['japanese_name'] = ""

    # Streamlitの進捗バーを初期化
    progress_text = "日本語商品名を取得中... (0%)"
    progress_bar = st.progress(0, text=progress_text)
    processed_count = 0

    # 1行ずつ処理 (iterrows は低速だが進捗表示のため)
    for index, row in df.iterrows():
        # clean_title が空でない場合のみ処理
        current_title = row.get('clean_title', '')
        if current_title:
             # 日本語名を取得（キャッシュ or API）
             try:
                 jp_name = get_japanese_name_from_gemini(current_title)
                 # 結果をDataFrameに書き込む (locを使うのが確実)
                 df.loc[index, 'japanese_name'] = jp_name
             except Exception as llm_e:
                 print(f"エラー: LLM呼び出し中に問題発生 (Row {index}, Title: {current_title}): {llm_e}")
                 st.warning(f"行 {index+2} ({current_title[:30]}...) の日本語名取得でエラーが発生しました。")
                 df.loc[index, 'japanese_name'] = "(処理エラー)" # エラー情報を記録
        else:
             df.loc[index, 'japanese_name'] = "" # clean_titleが空なら日本語名も空

        processed_count += 1
        # 進捗バー更新
        progress_percentage = int((processed_count / total_rows) * 100) if total_rows > 0 else 0
        progress_text = f"日本語商品名を取得中... ({processed_count}/{total_rows} - {progress_percentage}%)"
        # UIの更新は負荷がかかるため、一定間隔でのみ更新するなどの工夫も検討可
        if processed_count % 5 == 0 or processed_count == total_rows: # 例: 5件ごと、または最後に更新
            progress_bar.progress(progress_percentage, text=progress_text)

    progress_bar.empty() # 完了したらバーを消す
    print("日本語商品名の取得処理が完了しました。")
    st.success("日本語商品名の取得処理が完了しました。")
    # ===== ★★★ ここまで日本語商品名取得処理 ★★★ =====

    # カラムの指定があれば選択 (存在する列のみ)
    if keep_cols:
        existing_keep_cols = [c for c in keep_cols if c in df.columns]
        if existing_keep_cols:
             df = df[existing_keep_cols]
             print(f"指定された列 {existing_keep_cols} を保持しました。")
             st.write(f"指定された列 {existing_keep_cols} を保持。")

    # カラム順序の指定があれば適用、なければデフォルト順序を適用 (存在する列のみ)
    # ★ 日本語名とNGワード関連列もデフォルト順序に含める
    default_col_order = [
        "clean_title", "japanese_name", "brand", "product_name", "quantity",
        "flag_ngword", "検出NGワード"
    ]
    # 元のExcelにあった列も考慮に入れる
    original_columns = [c for c in df.columns if c not in default_col_order]

    print("カラム順序を調整します...")
    if col_order:
        # 指定された順序を優先
        final_col_order = [c for c in col_order if c in df.columns]
        # 指定されなかった列を後ろに追加
        remaining_cols = [c for c in df.columns if c not in final_col_order]
        final_col_order.extend(remaining_cols)
        print(f"指定されたカラム順序 {final_col_order} を適用しました。")
    else:
        # デフォルト順序を適用
        final_col_order = [c for c in default_col_order if c in df.columns]
        # デフォルトに含まれない元の列を後ろに追加
        remaining_original_cols = [c for c in original_columns if c not in final_col_order]
        final_col_order.extend(remaining_original_cols)
        print(f"デフォルトのカラム順序 {final_col_order} を適用しました。")

    # 存在しない列を除外して最終決定
    final_col_order = [c for c in final_col_order if c in df.columns]
    df = df.reindex(columns=final_col_order)
    st.write(f"カラム順序を調整: {', '.join(final_col_order)}")

    print("パイプライン処理が完了しました。")
    st.success("パイプライン処理が完了しました。")
    return df


# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# save_with_highlight 関数 (xlsxwriter を使い、BytesIO に出力)
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
def save_with_highlight(df: pd.DataFrame) -> bytes:
    """
    DataFrameをExcel形式のバイナリデータとしてメモリ上に作成し、
    特定の書式設定（折り返し、列幅）とNGワード行のハイライトを適用する関数（xlsxwriterを使用）。
    戻り値: Excelファイルのバイナリデータ (bytes)
    """
    print("Excelバイナリデータの作成を開始します (xlsxwriter, BytesIO)...")
    output_buffer = io.BytesIO() # メモリ上にバイナリ出力するためのバッファ

    try:
        # ExcelWriterオブジェクトを BytesIO に対して作成
        with ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
            sheet_name = 'Sheet1'
            df.to_excel(writer, sheet_name=sheet_name, index=False, header=True)

            # WorkbookとWorksheetオブジェクトを取得
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]

            # --- 書式設定 ---
            base_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
            highlight_format = workbook.add_format({'bg_color': '#FFCCCC', 'text_wrap': True, 'valign': 'top', 'border': 1})
            header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'fg_color': '#D7E4BC', 'border': 1})

            # --- ヘッダー行の書式設定 ---
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # --- 列幅の設定 ---
            for col_num, col_name in enumerate(df.columns):
                 header_len = len(str(col_name))
                 max_content_len = df[col_name].astype(str).map(len).max()
                 if pd.isna(max_content_len): max_content_len = 0
                 max_len = max(header_len, int(max_content_len))

                 if col_name in ['clean_title', 'japanese_name', 'product_name']:
                      col_width = 60
                 elif col_name in ['brand', '検出NGワード']:
                      col_width = 25
                 elif col_name in ['quantity', 'flag_ngword']:
                      col_width = 15
                 else:
                      col_width = min(max(max_len + 3, 12), 60)

                 worksheet.set_column(col_num, col_num, col_width)

            # --- データ行の書式設定とNGワードハイライト ---
            has_ng_flag = 'flag_ngword' in df.columns
            ng_col_idx = -1
            if has_ng_flag:
                try:
                    ng_col_idx = df.columns.get_loc('flag_ngword')
                except KeyError:
                    has_ng_flag = False

            for row_idx in range(len(df)):
                is_ng_row = False
                if has_ng_flag:
                    is_ng_row = bool(df.iloc[row_idx, ng_col_idx])

                cell_format = highlight_format if is_ng_row else base_format
                worksheet.set_row(row_idx + 1, None)

                for col_idx in range(len(df.columns)):
                    value = df.iloc[row_idx, col_idx]
                    if pd.isna(value): value = None
                    worksheet.write(row_idx + 1, col_idx, value, cell_format)

            # オートフィルターの設定
            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
            # ウィンドウ枠の固定
            worksheet.freeze_panes(1, 0)

        # ★★★ withブロックを抜けると BytesIO に書き込みが完了している ★★★
        print("Excelバイナリデータの作成完了。")
        # BytesIOの現在の内容 (ファイル全体) をバイナリデータとして返す
        return output_buffer.getvalue()

    except ImportError:
        message = "エラー: Excelファイルの書き込みに必要な 'xlsxwriter' がインストールされていません。"
        print(message)
        st.error(message + " `pip install xlsxwriter` を試してください。")
        raise
    except Exception as e:
        message = f"エラー: Excelバイナリデータの作成中に問題が発生しました。"
        print(message)
        print(f"詳細: {e}")
        print(traceback.format_exc())
        st.error(message)
        st.text_area("エラー詳細:", traceback.format_exc(), height=150)
        # エラーが発生した場合は空のbytesを返すか、Noneを返すか、再度raiseするか検討
        return b"" # 空のbytesを返す例