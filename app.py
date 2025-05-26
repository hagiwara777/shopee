import streamlit as st
import pandas as pd
import time
from datetime import datetime
import traceback
from pipeline import run_pipeline, save_with_highlight
import io
import sys
from contextlib import redirect_stdout, redirect_stderr

# ページ設定
st.set_page_config(
    page_title="ASIN一括日本語化＆検索ツール",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 ASIN一括日本語化＆検索ツール")
st.markdown("---")

# サイドバーに設定
st.sidebar.header("⚙️ 処理設定")

# ファイルアップロード
uploaded_file = st.file_uploader(
    "📁 Excel/CSVファイルをアップロード", 
    type=["xlsx", "csv"],
    help="SGdate100.xlsx等のリサーチデータファイルをアップロードしてください"
)

if uploaded_file:
    try:
        # ファイル読み込み
        with st.spinner("📖 ファイルを読み込み中..."):
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        
        # ファイル情報表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 データ行数", len(df))
        with col2:
            st.metric("📋 列数", len(df.columns))
        with col3:
            st.metric("📁 ファイル名", uploaded_file.name)
        
        # データプレビュー
        with st.expander("👀 データプレビュー", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
            
        # Name列の確認
        if 'Name' not in df.columns:
            st.error("❌ 'Name'列が見つかりません。ファイル形式を確認してください。")
            st.write("**利用可能な列:**", list(df.columns))
            st.stop()
        
        # NGワード設定
        st.sidebar.subheader("🚫 NGワード設定")
        use_ng_words = st.sidebar.checkbox("NGワードファイル使用", value=False)
        ng_words = []
        
        if use_ng_words:
            ng_file = st.sidebar.file_uploader("NGワードリスト(txt)", type=["txt"])
            if ng_file:
                ng_words = ng_file.read().decode("utf-8").splitlines()
                st.sidebar.success(f"✅ NGワード {len(ng_words)}件読み込み済み")
        
        # 処理オプション
        st.sidebar.subheader("🔧 処理オプション")
        process_limit = st.sidebar.number_input(
            "処理件数制限（テスト用）", 
            min_value=0, 
            max_value=len(df), 
            value=0,
            help="0の場合は全件処理"
        )
        
        # 実行ボタン
        if st.button("🚀 日本語化＆ASIN検索を実行", type="primary"):
            
            # 処理開始時刻
            start_time = time.time()
            
            # 処理データの準備
            process_df = df.copy()
            if process_limit > 0:
                process_df = process_df.head(process_limit)
                st.info(f"ℹ️ テスト用に先頭{process_limit}件のみ処理します")
            
            # メインコンテナ
            status_container = st.container()
            progress_container = st.container()
            log_container = st.container()
            
            with status_container:
                st.markdown("### 📊 処理状況")
                
                # ステータス表示用のプレースホルダー
                status_placeholder = st.empty()
                
            with progress_container:
                # 進捗バー
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
            with log_container:
                # ログ表示エリア
                st.markdown("### 📝 処理ログ")
                log_placeholder = st.empty()
                error_placeholder = st.empty()
            
            # ログキャプチャ用
            log_buffer = []
            error_buffer = []
            
            def add_log(message):
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] {message}"
                log_buffer.append(log_entry)
                log_placeholder.text_area(
                    "実行ログ", 
                    value="\n".join(log_buffer[-20:]),  # 最新20件のみ表示
                    height=200,
                    key=f"log_{len(log_buffer)}"
                )
            
            def add_error(message):
                timestamp = datetime.now().strftime("%H:%M:%S")
                error_entry = f"[{timestamp}] ❌ {message}"
                error_buffer.append(error_entry)
                error_placeholder.error("\n".join(error_buffer[-5:]))  # 最新5件のエラー
            
            try:
                # 処理開始
                add_log("🚀 処理を開始しました...")
                status_placeholder.info("🔄 データ処理中...")
                progress_bar.progress(0.1)
                progress_text.text("データクレンジング中...")
                
                # カスタムパイプライン実行（進捗付き）
                add_log(f"📊 {len(process_df)}件のデータを処理します")
                
                # パイプライン関数を進捗表示付きで実行
                class ProgressTracker:
                    def __init__(self):
                        self.current_step = 0
                        self.total_steps = 5  # データクレンジング、ブランド抽出、NGワード、日本語化、ASIN検索
                        self.current_item = 0
                        self.total_items = len(process_df)
                    
                    def update_step(self, step_name, progress=None):
                        self.current_step += 1
                        if progress is None:
                            progress = self.current_step / self.total_steps
                        progress_bar.progress(min(progress, 1.0))
                        progress_text.text(f"{step_name} ({self.current_step}/{self.total_steps})")
                        add_log(f"✅ {step_name}完了")
                    
                    def update_item(self, item_name, index):
                        self.current_item = index + 1
                        item_progress = 0.6 + (0.4 * self.current_item / self.total_items)  # 60%以降を項目処理用
                        progress_bar.progress(min(item_progress, 1.0))
                        progress_text.text(f"{item_name} ({self.current_item}/{self.total_items})")
                        if self.current_item % 10 == 0:  # 10件ごとにログ
                            add_log(f"📝 {item_name}: {self.current_item}/{self.total_items}件完了")
                
                tracker = ProgressTracker()
                
                # 実際の処理実行
                with st.spinner("データ処理実行中..."):
                    
                    # コンソール出力をキャプチャ
                    stdout_buffer = io.StringIO()
                    stderr_buffer = io.StringIO()
                    
                    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                        df_result = run_pipeline(
                            process_df, 
                            title_col="Name", 
                            ng_words=ng_words
                        )
                    
                    # キャプチャした出力をログに追加
                    stdout_content = stdout_buffer.getvalue()
                    stderr_content = stderr_buffer.getvalue()
                    
                    if stdout_content:
                        for line in stdout_content.strip().split('\n'):
                            if line.strip():
                                add_log(f"📝 {line}")
                    
                    if stderr_content:
                        for line in stderr_content.strip().split('\n'):
                            if line.strip():
                                add_error(line)
                
                # 処理完了
                progress_bar.progress(1.0)
                progress_text.text("✅ 処理完了！")
                
                # 処理時間計算
                end_time = time.time()
                processing_time = end_time - start_time
                add_log(f"⏱️ 総処理時間: {processing_time:.2f}秒")
                
                # 結果表示
                status_placeholder.success("✅ 処理が正常に完了しました！")
                
                # 結果サマリー
                st.markdown("### 📊 処理結果")
                
                result_col1, result_col2, result_col3, result_col4 = st.columns(4)
                
                with result_col1:
                    st.metric("✅ 処理済み件数", len(df_result))
                with result_col2:
                    japanese_count = len(df_result[df_result['japanese_name'] != ''])
                    st.metric("🇯🇵 日本語化成功", japanese_count)
                with result_col3:
                    asin_count = len(df_result[df_result['ASIN'] != ''])
                    st.metric("🛒 ASIN取得成功", asin_count)
                with result_col4:
                    success_rate = (asin_count / len(df_result) * 100) if len(df_result) > 0 else 0
                    st.metric("📈 成功率", f"{success_rate:.1f}%")
                
                # 結果データ表示
                st.markdown("### 📋 処理結果データ")
                st.dataframe(df_result, use_container_width=True)
                
                # Excel出力
                with st.spinner("📁 Excelファイル出力中..."):
                    output_filename = f"output_with_asin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    save_with_highlight(df_result, output_filename)
                    add_log(f"💾 Excel出力完了: {output_filename}")
                
                st.success(f"🎉 処理完了！Excelファイルを出力しました: {output_filename}")
                
                # ダウンロードボタン（オプション）
                try:
                    with open(output_filename, 'rb') as f:
                        st.download_button(
                            label="📥 結果ファイルをダウンロード",
                            data=f.read(),
                            file_name=output_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except:
                    st.info("💡 ファイルは作業ディレクトリに保存されました")
                
            except Exception as e:
                # エラーハンドリング
                error_msg = str(e)
                error_traceback = traceback.format_exc()
                
                status_placeholder.error("❌ 処理中にエラーが発生しました")
                add_error(f"エラー: {error_msg}")
                
                # 詳細エラー情報
                with st.expander("🔍 詳細エラー情報", expanded=True):
                    st.code(error_traceback, language="python")
                
                # エラー対処法の提案
                st.markdown("### 🛠️ エラー対処法")
                if "API" in error_msg:
                    st.warning("🔑 API認証エラーの可能性があります。.envファイルの設定を確認してください。")
                elif "Memory" in error_msg or "memory" in error_msg:
                    st.warning("💾 メモリ不足の可能性があります。処理件数を制限してお試しください。")
                elif "Network" in error_msg or "Connection" in error_msg:
                    st.warning("🌐 ネットワークエラーの可能性があります。しばらく待ってから再実行してください。")
                else:
                    st.warning("❓ 予期しないエラーです。データ形式やファイル内容を確認してください。")
    
    except Exception as e:
        st.error(f"❌ ファイル読み込みエラー: {str(e)}")
        st.write("**対処法:**")
        st.write("- ファイル形式がExcel(.xlsx)またはCSV(.csv)であることを確認")
        st.write("- ファイルが破損していないことを確認")
        st.write("- 他のアプリケーションでファイルが開かれていないことを確認")

else:
    # ファイルが選択されていない場合の説明
    st.info("👆 上記のファイルアップロード欄から、処理したいExcel/CSVファイルを選択してください。")
    
    st.markdown("### 📖 使用方法")
    st.markdown("""
    1. **📁 ファイルアップロード**: SGdate100.xlsx等のリサーチデータファイルをアップロード
    2. **⚙️ 設定調整**: サイドバーでNGワードファイルや処理件数を設定（オプション）
    3. **🚀 実行**: 「日本語化＆ASIN検索を実行」ボタンをクリック
    4. **📊 結果確認**: 進捗を確認しながら処理結果をダウンロード
    """)
    
    st.markdown("### 🔧 処理内容")
    st.markdown("""
    - **データクレンジング**: 商品名の正規化・不要文字除去
    - **ブランド抽出**: 化粧品ブランド名の自動検出
    - **日本語化**: OpenAI GPT-4oによる自然な日本語翻訳
    - **ASIN検索**: Amazon SP-APIによる商品ASIN取得
    - **Excel出力**: 処理結果の構造化されたExcelファイル出力
    """)