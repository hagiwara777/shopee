# asin_app.py - 最小限テスト版（読み込み問題診断用）
import streamlit as st

# ✅ 最優先: ページ設定
st.set_page_config(
    page_title="Shopee出品ツール",
    page_icon="🏆",
    layout="wide"
)

# ✅ 基本インポート（問題があるものは除外）
try:
    import pandas as pd
    import numpy as np
    from datetime import datetime
    import io
    BASIC_IMPORTS_OK = True
except Exception as e:
    BASIC_IMPORTS_OK = False
    basic_import_error = str(e)

# ✅ メインタイトルと基本UI
st.title("🏆 Shopee出品ツール - 最小限テスト版")

# ✅ 基本機能確認
st.header("🔧 システム状態確認")

if BASIC_IMPORTS_OK:
    st.success("✅ 基本インポート: 成功")
else:
    st.error(f"❌ 基本インポート: 失敗 - {basic_import_error}")

# ✅ 現在時刻表示
st.info(f"⏰ 現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ✅ サンプルデータ表示
if st.button("🧪 サンプルデータ表示"):
    sample_data = pd.DataFrame({
        'clean_title': ['FANCL Mild Cleansing Oil', 'MILBON elujuda hair treatment', 'サンプル商品'],
        'status': ['テスト', 'テスト', 'テスト']
    })
    st.dataframe(sample_data)
    st.success("✅ サンプルデータ表示成功")

# ✅ タブ基本機能
tab1, tab2 = st.tabs(["📁 テスト1", "📊 テスト2"])

with tab1:
    st.header("📁 テスト1")
    st.write("このタブが表示されれば、基本機能は動作しています。")

with tab2:
    st.header("📊 テスト2")
    st.write("タブ切り替えが動作すれば、UI機能も正常です。")

# ✅ サイドバー基本機能
st.sidebar.title("🔧 テスト設定")
st.sidebar.write("サイドバーが表示されています。")

test_value = st.sidebar.slider("テストスライダー", 0, 100, 50)
st.sidebar.write(f"選択値: {test_value}")

# ✅ 診断情報
st.sidebar.markdown("---")
st.sidebar.subheader("📊 診断情報")
st.sidebar.write(f"Python実行中: ✅")
st.sidebar.write(f"Streamlit動作中: ✅")
st.sidebar.write(f"基本インポート: {'✅' if BASIC_IMPORTS_OK else '❌'}")

# ✅ ファイルパス確認
import os
import pathlib

current_dir = str(pathlib.Path(__file__).resolve().parent)
st.sidebar.write(f"実行ディレクトリ: {os.path.basename(current_dir)}")

# ✅ 成功メッセージ
st.success("🎉 最小限テスト版が正常に動作しています！")
st.info("このメッセージが表示されれば、Streamlitの基本機能は正常です。")

# ✅ 次のステップ提案
st.markdown("---")
st.subheader("🚀 次のステップ")
st.markdown("""
**この画面が表示されている場合:**
- ✅ Streamlitは正常に動作
- ✅ 基本的なPythonインポートは成功
- ✅ ページ設定は正しく処理

**次に確認すること:**
1. サンプルデータ表示ボタンをクリック
2. タブ切り替えを試行
3. サイドバーのスライダーを操作
4. 全て動作すれば、段階的に機能を追加可能
""")