import streamlit as st
import json
from pathlib import Path
import pandas as pd

BRANDS_PATH = Path("data/brands.json")

def load_brands():
    if BRANDS_PATH.exists():
        with open(BRANDS_PATH, encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}

def save_brands(brands):
    with open(BRANDS_PATH, "w", encoding="utf-8") as f:
        json.dump(brands, f, ensure_ascii=False, indent=2)

def is_english(s):
    import re
    return bool(re.match(r"^[a-zA-Z0-9\s\-.&()]+$", str(s).strip()))

def preferred_name(variations):
    import re
    katakana_re = re.compile(r'[\u30A0-\u30FF]+')
    kanji_re = re.compile(r'[\u4E00-\u9FFF]+')
    hiragana_re = re.compile(r'[\u3040-\u309F]+')
    # カタカナ→漢字→ひらがな→英字優先
    for name in variations:
        if katakana_re.search(name):
            return name
    for name in variations:
        if kanji_re.search(name):
            return name
    for name in variations:
        if hiragana_re.search(name):
            return name
    for name in variations:
        if re.match(r'^[A-Za-z0-9\s\-&.()]+$', name):
            return name
    return variations[0] if variations else ""

st.title("ブランド辞書（brands.json）バリエーション編集ツール")

brands = load_brands()

# 1. ブランドリスト表示（メイン英語名・優先日本語名を見やすく一覧）
st.subheader("現在のブランドリスト（メイン英語名→優先日本語名）")
if brands:
    rows = []
    for en, vars in brands.items():
        vars = vars if isinstance(vars, list) else [vars]
        jp_pref = preferred_name(vars)
        rows.append([en, jp_pref, ", ".join(vars)])
    df_brands = pd.DataFrame(rows, columns=["英語ブランド名", "優先日本語名", "すべてのバリエーション"])
    st.dataframe(df_brands)
else:
    st.info("ブランド辞書が空です。")

st.markdown("---")

# 2. 新規ブランド追加
st.subheader("新規ブランドの追加")
with st.form("add_form", clear_on_submit=True):
    new_en = st.text_input("英語ブランド名")
    new_vars = st.text_area("バリエーション（カンマ区切り）", help="例: ミルボン,みるぼん,MILBON")
    submitted = st.form_submit_button("追加する")
    if submitted:
        if new_en and new_vars:
            var_list = [v.strip() for v in new_vars.split(",") if v.strip()]
            brands[new_en.strip()] = var_list
            save_brands(brands)
            st.success(f"{new_en.strip()} → {var_list} を追加しました。画面を再読み込みしてください。")
        else:
            st.warning("全てのフィールドを入力してください。")

st.markdown("---")

# 3. 既存ブランドの編集・削除
st.subheader("既存ブランドの編集・削除")
edit_en = st.selectbox("編集・削除したい英語ブランド名", [""] + sorted(list(brands.keys())))
if edit_en:
    current_vars = brands[edit_en]
    var_str = ", ".join(current_vars)
    edit_vars = st.text_area("バリエーション（カンマ区切りで編集）", value=var_str)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("上書き保存"):
            var_list = [v.strip() for v in edit_vars.split(",") if v.strip()]
            brands[edit_en] = var_list
            save_brands(brands)
            st.success(f"{edit_en} → {var_list} に更新しました。画面を再読み込みしてください。")
    with col2:
        if st.button("削除する"):
            brands.pop(edit_en)
            save_brands(brands)
            st.success(f"{edit_en} を辞書から削除しました。画面を再読み込みしてください。")

st.markdown("---")

# 4. CSVからの一括インポート
st.subheader("CSVファイルからブランド一括追加・上書き")
csv_file = st.file_uploader("ブランド一覧CSV（英語ブランド名, バリエーション列（カンマ区切り））", type=["csv"])
if csv_file:
    try:
        df_new = pd.read_csv(csv_file)
        if "英語ブランド名" in df_new.columns and "バリエーション" in df_new.columns:
            for _, row in df_new.iterrows():
                key = row["英語ブランド名"]
                vals = [v.strip() for v in str(row["バリエーション"]).split(",") if v.strip()]
                brands[key] = vals
            save_brands(brands)
            st.success("CSVからのブランド一括インポート・上書きに成功しました！画面を再読み込みしてください。")
        else:
            st.error("CSVに '英語ブランド名' および 'バリエーション' の列が必要です。")
    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")

st.markdown("---")
st.info("編集後はページを再読み込みすると最新の状態が反映されます。")
