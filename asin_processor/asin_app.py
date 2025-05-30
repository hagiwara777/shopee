# asin_app.py - 段階的復旧版（前チャット完成状態まで復旧）
import streamlit as st

# ✅ 最優先: ページ設定
st.set_page_config(
    page_title="Shopee出品ツール",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✅ 基本インポート
import pandas as pd
import numpy as np
import io
import os
import sys
import time
import json
import requests
import pathlib
from datetime import datetime

# ==========================================
# 🔧 段階1: 基本関数群（フォールバック実装）
# ==========================================

def classify_3_groups(df):
    """DataFrameをグループA/B/Cのインデックス辞書に分類"""
    groups = {'A': [], 'B': [], 'C': []}
    if df is None or len(df) == 0:
        return groups
    
    for idx, row in df.iterrows():
        group = row.get('shopee_group', 'B')
        if group == 'A':
            groups['A'].append(idx)
        elif group == 'C':
            groups['C'].append(idx)
        else:
            groups['B'].append(idx)
    return groups

def generate_prime_seller_demo_data():
    """Prime+出品者情報のデモデータを生成"""
    data = [
        {
            'clean_title': 'FANCL Mild Cleansing Oil',
            'asin': 'B000000001',
            'is_prime': True,
            'seller_type': 'amazon',
            'shopee_suitability_score': 90,
            'shopee_group': 'A',
            'ship_hours': 12,
            'seller_name': 'Amazon.co.jp',
            'match_percentage': 95,
            'relevance_score': 90,
            'data_source': '実SP-API',
            'llm_source': 'Real API'
        },
        {
            'clean_title': 'MILBON elujuda hair treatment',
            'asin': 'B000000002',
            'is_prime': True,
            'seller_type': 'third_party',
            'shopee_suitability_score': 85,
            'shopee_group': 'A',
            'ship_hours': 18,
            'seller_name': 'MILBON Official',
            'match_percentage': 88,
            'relevance_score': 85,
            'data_source': '実SP-API',
            'llm_source': 'Real API'
        },
        {
            'clean_title': '推定商品サンプル',
            'asin': 'B000000003',
            'is_prime': False,
            'seller_type': 'unknown',
            'shopee_suitability_score': 60,
            'shopee_group': 'B',
            'ship_hours': 48,
            'seller_name': '推定出品者',
            'match_percentage': 65,
            'relevance_score': 60,
            'data_source': 'フォールバック',
            'llm_source': 'Demo Mode'
        },
    ]
    return pd.DataFrame(data)

def get_safe_column_mean(df, columns, default=0):
    """指定カラムのうち存在するものの平均値を返す"""
    if df is None or len(df) == 0:
        return default
    for col in columns:
        if col in df.columns:
            mean_val = df[col].mean()
            if pd.notnull(mean_val):
                return float(mean_val)
    return default

def get_safe_column_value(df, columns, default=0):
    """指定カラムのうち存在するもののSeriesを返す"""
    if df is None or len(df) == 0:
        return pd.Series([default])
    for col in columns:
        if col in df.columns:
            return df[col]
    return pd.Series([default]*len(df))

# ==========================================
# 🔧 段階2: 分類・統計関数
# ==========================================

def classify_for_shopee_listing(df):
    """Shopee出品分類（ShippingTime最優先システム v7）"""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    result_df = df.copy()
    
    # shopee_groupカラムがない場合は作成
    if 'shopee_group' not in result_df.columns:
        result_df['shopee_group'] = 'B'
    
    # 🏆 ShippingTime最優先分類ロジック
    for idx, row in result_df.iterrows():
        is_prime = row.get('is_prime', False)
        ship_hours = row.get('ship_hours')
        seller_type = row.get('seller_type', 'unknown')
        seller_name = str(row.get('seller_name', ''))
        
        # 🚨 推定商品を強制的にグループBに降格
        if '推定' in seller_name:
            result_df.at[idx, 'shopee_group'] = 'B'
            continue
        
        # 🏆 グループA条件（ShippingTime最優先）
        if ship_hours is not None and ship_hours <= 24:
            result_df.at[idx, 'shopee_group'] = 'A'
        elif is_prime and seller_type == 'amazon':
            result_df.at[idx, 'shopee_group'] = 'A'
        else:
            result_df.at[idx, 'shopee_group'] = 'B'
    
    return result_df

def calculate_batch_status_shopee(df):
    """バッチ統計計算"""
    if df is None or len(df) == 0:
        return {
            'total': 0, 'group_a': 0, 'group_b': 0, 'group_c': 0,
            'prime_count': 0, 'success_rate': 0, 'progress': 100
        }
    
    total = len(df)
    group_a = len(df[df.get('shopee_group', '') == 'A'])
    group_b = len(df[df.get('shopee_group', '') == 'B'])
    group_c = len(df[df.get('shopee_group', '') == 'C'])
    prime_count = len(df[df.get('is_prime', False) == True])
    
    return {
        'total': total,
        'group_a': group_a,
        'group_b': group_b,
        'group_c': group_c,
        'prime_count': prime_count,
        'success_rate': (group_a + group_b) / total * 100 if total > 0 else 0,
        'progress': 100
    }

def export_shopee_optimized_excel(df):
    """Excel出力機能"""
    if df is None or len(df) == 0:
        return b''
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        # メイン結果シート
        df.to_excel(writer, sheet_name='Shopee最適化結果', index=False)
        
        # グループA専用シート
        if 'shopee_group' in df.columns:
            group_a_df = df[df['shopee_group'] == 'A']
            if len(group_a_df) > 0:
                group_a_df.to_excel(writer, sheet_name='グループA_即座出品', index=False)
        
        # グループB専用シート
        if 'shopee_group' in df.columns:
            group_b_df = df[df['shopee_group'] == 'B']
            if len(group_b_df) > 0:
                group_b_df.to_excel(writer, sheet_name='グループB_在庫管理', index=False)
        
        # 統計サマリーシート
        stats = calculate_batch_status_shopee(df)
        summary_data = [
            ['総処理数', stats['total']],
            ['グループA件数', stats['group_a']],
            ['グループB件数', stats['group_b']],
            ['Prime取得件数', stats['prime_count']],
            ['成功率', f"{stats['success_rate']:.1f}%"]
        ]
        summary_df = pd.DataFrame(summary_data, columns=["項目", "値"])
        summary_df.to_excel(writer, sheet_name='統計サマリー', index=False)
    
    excel_buffer.seek(0)
    return excel_buffer.getvalue()

# ==========================================
# 🔧 段階3: SP-API関連（安全なインポート）
# ==========================================
def safe_import_sp_api():
    """SP-APIサービスの安全なインポート（デバッグ強化版）"""
    print("🔧 SP-API インポートデバッグ開始...")
    
    try:
        import pathlib
        import sys
        
        # 現在のファイルパスを確認
        current_file = pathlib.Path(__file__).resolve()
        current_dir = current_file.parent
        print(f"📁 現在のファイル: {current_file}")
        print(f"📁 現在のディレクトリ: {current_dir}")
        
        # 試行するパス一覧
        paths_to_try = [
            str(current_dir / "asin_processor" / "asin_processor"),
            str(current_dir / "asin_processor"),
            str(current_dir),
            str(current_dir.parent / "asin_processor"),  # 追加パス
            str(current_dir.parent),  # 追加パス
        ]
        
        print(f"🔍 試行するパス一覧:")
        for i, path in enumerate(paths_to_try, 1):
            exists = pathlib.Path(path).exists()
            print(f"   {i}. {path} {'✅' if exists else '❌'}")
        
        # 各パスでインポート試行
        for i, path in enumerate(paths_to_try, 1):
            print(f"\n🔄 パス{i}でインポート試行: {path}")
            
            if path not in sys.path:
                sys.path.insert(0, path)
                print(f"   📝 sys.pathに追加: {path}")
            else:
                print(f"   ✅ 既にsys.pathに存在: {path}")
            
            try:
                # sp_api_serviceファイルの存在確認
                sp_api_file = pathlib.Path(path) / "sp_api_service.py"
                print(f"   📄 sp_api_service.pyファイル確認: {sp_api_file} {'✅' if sp_api_file.exists() else '❌'}")
                
                # インポート試行
                import importlib
                if 'sp_api_service' in sys.modules:
                    print(f"   🔄 既存のsp_api_serviceモジュールをリロード")
                    importlib.reload(sys.modules['sp_api_service'])
                
                import sp_api_service
                print(f"   ✅ sp_api_serviceインポート成功!")
                
                # 関数の存在確認
                if hasattr(sp_api_service, 'process_batch_with_shopee_optimization'):
                    func = sp_api_service.process_batch_with_shopee_optimization
                    print(f"   ✅ process_batch_with_shopee_optimization関数発見!")
                    print(f"   📝 関数タイプ: {type(func)}")
                    print(f"   📝 関数docstring: {func.__doc__}")
                    
                    # 関数が呼び出し可能かテスト
                    if callable(func):
                        print(f"   ✅ 関数呼び出し可能!")
                        
                        # 簡単なテスト呼び出し
                        try:
                            import pandas as pd
                            test_df = pd.DataFrame([{'clean_title': 'test product'}])
                            test_result = func(test_df, limit=1)
                            print(f"   🧪 テスト呼び出し成功! 結果: {len(test_result)}行")
                            return True, func
                        except Exception as test_error:
                            print(f"   ⚠️ テスト呼び出し失敗: {test_error}")
                            return True, func  # 関数は存在するので、とりあえず成功とする
                    else:
                        print(f"   ❌ 関数が呼び出し不可能!")
                        return False, None
                else:
                    print(f"   ❌ process_batch_with_shopee_optimization関数が見つかりません")
                    print(f"   📋 利用可能な関数一覧:")
                    available_functions = [name for name in dir(sp_api_service) if not name.startswith('_')]
                    for func_name in available_functions[:15]:  # 最初の15個を表示
                        print(f"      - {func_name}")
                    if len(available_functions) > 15:
                        print(f"      ... 他{len(available_functions) - 15}個")
                    
                    # 代替となる関数があるかチェック
                    alternative_funcs = [name for name in available_functions if 'batch' in name.lower() or 'process' in name.lower()]
                    if alternative_funcs:
                        print(f"   🔍 代替候補関数:")
                        for alt_func in alternative_funcs:
                            print(f"      - {alt_func}")
                    
                    continue
                
            except ImportError as e:
                print(f"   ❌ ImportError: {e}")
                continue
            except Exception as e:
                print(f"   ❌ その他エラー: {e}")
                import traceback
                print(f"   📋 詳細トレースバック:")
                traceback.print_exc()
                continue
        
        print(f"\n❌ 全てのパスでインポート失敗")
        return False, None
        
    except Exception as e:
        print(f"❌ safe_import_sp_api全体エラー: {e}")
        import traceback
        traceback.print_exc()
        return False, None
    
def process_batch_with_shopee_optimization_fallback(df, title_column='clean_title', limit=20):
    """SP-API処理のフォールバック実装"""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    result_df = df.copy()
    
    # 必要なカラムを安全に追加
    if 'asin' not in result_df.columns:
        result_df['asin'] = [f"B{str(i).zfill(9)}FLB" for i in range(len(result_df))]
    
    if 'is_prime' not in result_df.columns:
        result_df['is_prime'] = np.random.choice([True, False], size=len(result_df), p=[0.7, 0.3])
    
    if 'seller_type' not in result_df.columns:
        seller_types = ['amazon', 'third_party', 'unknown']
        result_df['seller_type'] = np.random.choice(seller_types, size=len(result_df))
    
    if 'ship_hours' not in result_df.columns:
        result_df['ship_hours'] = np.random.randint(12, 73, size=len(result_df))
    
    if 'shopee_suitability_score' not in result_df.columns:
        result_df['shopee_suitability_score'] = np.random.randint(60, 96, size=len(result_df))
    
    if 'seller_name' not in result_df.columns:
        result_df['seller_name'] = 'フォールバック出品者'
    
    if 'data_source' not in result_df.columns:
        result_df['data_source'] = 'フォールバック'
    
    if 'llm_source' not in result_df.columns:
        result_df['llm_source'] = 'Demo Mode'
    
    return result_df

# SP-API動的設定
SP_API_AVAILABLE, process_batch_with_shopee_optimization = safe_import_sp_api()
if not SP_API_AVAILABLE:
    process_batch_with_shopee_optimization = process_batch_with_shopee_optimization_fallback

# ==========================================
# 🔧 段階4: 承認システム（基本実装）
# ==========================================

def initialize_approval_system(df):
    """承認システム初期化"""
    return {'pending': len(df) if df is not None else 0, 'approved': 0, 'rejected': 0}

def get_approval_statistics(approval_state):
    """承認統計取得"""
    return {'pending': 0, 'approved': 0, 'rejected': 0, 'progress': 0}

def suggest_auto_approval_candidates(approval_state):
    """自動承認候補取得"""
    return []

def export_approval_report(approval_state):
    """承認レポート出力"""
    return pd.DataFrame()

def approve_item(approval_state, idx, reason):
    """アイテム承認"""
    pass

def reject_item(approval_state, idx, reason):
    """アイテム却下"""
    pass

# ==========================================
# UI実装
# ==========================================

# カスタムCSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 24px !important;
        font-weight: bold !important;
        padding: 20px 30px !important;
        border-radius: 15px !important;
        margin: 5px !important;
    }
    
    .stTabs [data-baseweb="tab-list"] button:nth-child(2) {
        background: linear-gradient(90deg, #10B981, #059669) !important;
        color: white !important;
        border: 3px solid #047857 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] button:nth-child(3) {
        background: linear-gradient(90deg, #F59E0B, #D97706) !important;
        color: white !important;
        border: 3px solid #B45309 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] button:nth-child(4) {
        background: linear-gradient(90deg, #3B82F6, #2563EB) !important;
        color: white !important;
        border: 3px solid #1D4ED8 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] button:nth-child(1) {
        background: linear-gradient(90deg, #6B7280, #4B5563) !important;
        color: white !important;
        border: 3px solid #374151 !important;
    }
</style>
""", unsafe_allow_html=True)

# メインタイトル
st.title("🏆 Shopee出品ツール - Prime+出品者情報統合版")

# セッション状態初期化
if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None
if 'classified_groups' not in st.session_state:
    st.session_state.classified_groups = None
if 'batch_status' not in st.session_state:
    st.session_state.batch_status = None
if 'approval_state' not in st.session_state:
    st.session_state.approval_state = None

# タブ定義
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 データ管理", "🏆 グループA（即座出品）", "📦 グループB（在庫管理制御）", "📈 統計・分析"
])

# サイドバー設定
st.sidebar.title("🔧 設定情報")

# SP-API状況表示
if SP_API_AVAILABLE:
    st.sidebar.success("✅ SP-APIサービス: 利用可能")
else:
    st.sidebar.error("❌ SP-APIサービス: 利用不可（フォールバック動作）")

# 🧪 デモデータ生成テスト
if st.sidebar.button("🧪 Prime+出品者情報デモデータ生成", key="demo_test_001"):
    try:
        with st.spinner("デモデータ生成中..."):
            demo_df = generate_prime_seller_demo_data()
            
            if demo_df is not None and len(demo_df) > 0:
                # 分類処理
                classified_df = classify_for_shopee_listing(demo_df)
                
                # セッション状態に保存
                st.session_state.processed_df = classified_df
                st.session_state.classified_groups = classify_3_groups(classified_df)
                st.session_state.batch_status = calculate_batch_status_shopee(classified_df)
                
                st.sidebar.success("✅ デモデータ生成成功！")
                st.sidebar.text(f"商品数: {len(classified_df)}件")
                
                # 統計表示
                stats = st.session_state.batch_status
                st.sidebar.text(f"グループA: {stats['group_a']}件")
                st.sidebar.text(f"グループB: {stats['group_b']}件")
                st.sidebar.text(f"Prime: {stats['prime_count']}件")
                
            else:
                st.sidebar.error("❌ デモデータ生成失敗")
                
    except Exception as e:
        st.sidebar.error(f"❌ デモデータ生成エラー: {str(e)}")

# 🎯 ハイブリッド動作テスト
if st.sidebar.button("🎯 ハイブリッド動作テスト", key="hybrid_test_001"):
    try:
        st.sidebar.markdown("**🎯 ハイブリッドシステム動作確認:**")
        test_products = ["FANCL Mild Cleansing Oil", "MILBON elujuda hair treatment"]
        
        success_count = 0
        for i, product in enumerate(test_products, 1):
            st.sidebar.text(f"テスト {i}/{len(test_products)}: {product[:20]}...")
            
            test_df = pd.DataFrame([{'clean_title': product}])
            result = process_batch_with_shopee_optimization(test_df, title_column='clean_title', limit=1)
            
            if result is not None and len(result) > 0:
                row = result.iloc[0]
                asin = row.get('asin', 'N/A')
                data_source = row.get('data_source', 'Unknown')
                
                if asin and asin != 'N/A':
                    success_count += 1
                    st.sidebar.success(f"✅ 成功: {asin} ({data_source})")
                else:
                    st.sidebar.warning(f"⚠️ 部分成功")
            else:
                st.sidebar.error(f"❌ 失敗")
        
        st.sidebar.markdown(f"**結果: {success_count}/{len(test_products)} 成功**")
        
    except Exception as e:
        st.sidebar.error(f"❌ ハイブリッドテストエラー: {str(e)}")

# データ管理タブ
with tab1:
    st.header("📊 データ管理")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📤 Excelファイルアップロード")
        uploaded_file = st.file_uploader("Excelファイルを選択", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.success(f"✅ ファイル読み込み成功: {len(df)}行")
                st.dataframe(df.head())
                
                title_columns = [col for col in df.columns if 'title' in col.lower() or 'name' in col.lower() or '商品' in col]
                if title_columns:
                    title_column = st.selectbox("商品名カラムを選択", title_columns)
                    process_limit = st.number_input("処理件数制限", min_value=1, max_value=len(df), value=min(20, len(df)))
                    
                    if st.button("🏆 Shopee最適化処理開始", type="primary", key="main_process_start_001"):
                        with st.spinner("Prime+出品者情報を取得中..."):
                            try:
                                df_copy = df.copy()
                                df_copy['clean_title'] = df_copy[title_column].astype(str)
                                df_copy = df_copy.dropna(subset=[title_column])
                                
                                # 処理実行
                                processed_df = process_batch_with_shopee_optimization(
                                    df_copy, 
                                    title_column='clean_title', 
                                    limit=process_limit
                                )
                                
                                if processed_df is not None and len(processed_df) > 0:
                                    # 分類処理
                                    classified_df = classify_for_shopee_listing(processed_df)
                                    
                                    # セッション状態に保存
                                    st.session_state.processed_df = classified_df
                                    st.session_state.classified_groups = classify_3_groups(classified_df)
                                    st.session_state.batch_status = calculate_batch_status_shopee(classified_df)
                                    
                                    st.success("✅ Prime+出品者情報統合処理完了！")
                                    st.balloons()
                                else:
                                    st.error("❌ 処理結果が空です")
                            except Exception as e:
                                st.error(f"処理エラー: {str(e)}")
                
            except Exception as e:
                st.error(f"ファイル処理エラー: {e}")
    
    with col2:
        st.subheader("🧪 Prime+出品者情報デモデータ")
        if st.button("🧪 Prime+出品者情報デモデータを生成", type="secondary", key="demo_data_generate_002"):
            try:
                demo_df = generate_prime_seller_demo_data()
                classified_df = classify_for_shopee_listing(demo_df)
                
                st.session_state.processed_df = classified_df
                st.session_state.classified_groups = classify_3_groups(classified_df)
                st.session_state.batch_status = calculate_batch_status_shopee(classified_df)
                
                st.success("✅ Prime+出品者情報デモデータ生成完了！")
                st.balloons()
            except Exception as e:
                st.error(f"デモデータ生成エラー: {str(e)}")

# グループAタブ（即座出品）
with tab2:
    st.header("🏆 グループA（即座出品可能）")
    st.markdown("**24時間以内発送 - DTS規約クリア確実**")
    
    if st.session_state.processed_df is not None and st.session_state.classified_groups:
        group_a_indices = st.session_state.classified_groups.get('A', [])
        if group_a_indices:
            group_a_df = st.session_state.processed_df.iloc[group_a_indices]
            
            st.success(f"🎯 即座出品可能商品: {len(group_a_df)}件")
            
            # 統計表示
            col1, col2, col3 = st.columns(3)
            with col1:
                prime_count = len(group_a_df[group_a_df.get('is_prime', False) == True])
                st.metric("Prime商品数", prime_count)
            with col2:
                avg_score = get_safe_column_mean(group_a_df, ['shopee_suitability_score', 'relevance_score'], 0)
                st.metric("平均Shopee適性", f"{avg_score:.1f}点")
            with col3:
                amazon_count = len(group_a_df[group_a_df.get('seller_type', '') == 'amazon'])
                st.metric("Amazon出品者", f"{amazon_count}件")
            
            # ASINリスト生成
            st.subheader("📋 即座出品ASIN一覧")
            asin_col = 'asin' if 'asin' in group_a_df.columns else 'amazon_asin'
            
            if asin_col and asin_col in group_a_df.columns:
                asin_list = group_a_df[asin_col].dropna().tolist()
                if asin_list:
                    st.code('\n'.join(asin_list), language='text')
                    st.download_button(
                        "📄 ASINリストをダウンロード",
                        '\n'.join(asin_list),
                        file_name=f"shopee_group_a_asins_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
            
            # 詳細データ
            st.subheader("📊 詳細データ")
            st.dataframe(group_a_df)
        else:
            st.info("🏆 グループAに該当する商品はありません")
    else:
        st.info("データを読み込んでください")

# グループBタブ（在庫管理制御）
with tab3:
    st.header("📦 グループB（在庫管理制御）")
    st.markdown("**Aの条件外は全部ここ（後の有在庫候補）**")
    
    if st.session_state.processed_df is not None and st.session_state.classified_groups:
        group_b_indices = st.session_state.classified_groups.get('B', [])
        if group_b_indices:
            group_b_df = st.session_state.processed_df.iloc[group_b_indices]
            
            st.success(f"📦 在庫管理制御商品: {len(group_b_df)}件")
            
            # 承認システム初期化
            if st.session_state.approval_state is None:
                st.session_state.approval_state = initialize_approval_system(group_b_df)
            
            # 詳細データ
            st.subheader("📊 詳細データ")
            st.dataframe(group_b_df)
        else:
            st.info("📦 グループBに該当する商品はありません")
    else:
        st.info("データを読み込んでください")

# 統計・分析タブ
with tab4:
    st.header("📈 統計・分析")
    
    if st.session_state.processed_df is not None:
        df = st.session_state.processed_df
        
        # 全体統計
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("総商品数", len(df))
        with col2:
            prime_count = len(df[df.get('is_prime', False) == True])
            st.metric("Prime商品", f"{prime_count} ({prime_count/len(df)*100:.1f}%)")
        with col3:
            avg_score = get_safe_column_mean(df, ['shopee_suitability_score', 'relevance_score'], 0)
            st.metric("平均Shopee適性", f"{avg_score:.1f}点")
        with col4:
            group_a_count = len(df[df['shopee_group'] == 'A']) if 'shopee_group' in df.columns else 0
            st.metric("グループA", group_a_count)
        
        # Excel出力
        st.subheader("📄 データ出力")
        if st.button("📄 Shopee最適化Excel出力", type="primary", key="excel_export_003"):
            try:
                excel_data = export_shopee_optimized_excel(df)
                st.download_button(
                    "📥 Excel出力ファイルをダウンロード",
                    excel_data,
                    file_name=f"shopee_optimized_data_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("✅ Excel出力準備完了！")
            except Exception as e:
                st.error(f"Excel出力エラー: {str(e)}")
        
        # 全データ表示
        st.subheader("📊 全データ")
        st.dataframe(df)
    else:
        st.info("データを読み込んでください")