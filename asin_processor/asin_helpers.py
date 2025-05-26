# asin_helpers.py - Shopee特化機能統合フルコード版
import pandas as pd
import numpy as np
from datetime import datetime
import re

# ======================== Shopee出品特化機能（新規追加） ========================

def classify_for_shopee_listing(df):
    """
    Shopee出品特化型分類（Prime+出品者情報を最重視）
    
    グループA: Prime + Amazon/公式メーカー（最優秀 - 即座に出品可能）
    グループB: Prime + サードパーティ（良好 - 確認後出品推奨）
    グループC: 非Prime 高一致度（参考 - 慎重検討）
    グループX: 除外対象（ASIN無し、低品質など）
    """
    df = df.copy()
    
    print("🎯 Shopee出品特化型分類開始...")
    
    # 必要なカラムの確認・補完
    required_columns = {
        'is_prime': False,
        'seller_type': 'unknown',
        'is_amazon_seller': False,
        'is_official_seller': False,
        'shopee_suitability_score': 0,
        'relevance_score': 0
    }
    
    for col, default_val in required_columns.items():
        if col not in df.columns:
            df[col] = default_val
    
    # ASIN関連カラムの統一
    asin_column = None
    for col in ['asin', 'amazon_asin', 'ASIN']:
        if col in df.columns:
            asin_column = col
            break
    
    if asin_column is None:
        df['asin'] = ''
        asin_column = 'asin'
    
    # ASINの存在チェック
    df['has_valid_asin'] = df[asin_column].notna() & (df[asin_column] != '') & (df[asin_column] != 'N/A')
    
    def shopee_classify(row):
        """Shopee出品特化分類ロジック"""
        
        # ASIN無しは除外
        if not row.get('has_valid_asin', False):
            return 'X'
        
        is_prime = row.get('is_prime', False)
        seller_type = row.get('seller_type', 'unknown')
        relevance_score = row.get('relevance_score', 0)
        
        # 🏆 グループA: Prime + Amazon/公式メーカー（最優秀）
        if is_prime and seller_type in ['amazon', 'official_manufacturer']:
            return 'A'
        
        # 🟡 グループB: Prime + サードパーティ（良好）
        elif is_prime and seller_type == 'third_party':
            return 'B'
        
        # 🔵 グループC: 非Prime（一致度で判定）
        elif not is_prime:
            if relevance_score >= 70:
                return 'C'  # 非Prime高一致度
            elif relevance_score >= 40:
                return 'C'  # 非Prime中一致度も参考として含める
            else:
                return 'X'  # 非Prime低一致度は除外
        
        # ❌ その他（不明・エラー）は除外
        else:
            return 'X'
    
    # 分類実行
    df['shopee_group'] = df.apply(shopee_classify, axis=1)
    
    # 優先度設定（グループ内ソート用）
    priority_map = {'A': 1, 'B': 2, 'C': 3, 'X': 4}
    df['group_priority'] = df['shopee_group'].map(priority_map)
    
    # ソート：グループ優先度 → Shopee適性スコア降順 → 一致度降順
    df = df.sort_values(
        by=['group_priority', 'shopee_suitability_score', 'relevance_score'], 
        ascending=[True, False, False]
    ).reset_index(drop=True)
    
    # 統計情報出力
    group_stats = df['shopee_group'].value_counts().sort_index()
    total_valid = len(df[df['shopee_group'] != 'X'])
    
    print(f"📊 Shopee出品特化分類結果:")
    print(f"   🏆 グループA（Prime+Amazon/公式）: {group_stats.get('A', 0)}件 - 即座に出品可能")
    print(f"   🟡 グループB（Prime+サードパーティ）: {group_stats.get('B', 0)}件 - 確認後出品推奨")
    print(f"   🔵 グループC（非Prime参考）: {group_stats.get('C', 0)}件 - 慎重検討")
    print(f"   ❌ 除外（グループX）: {group_stats.get('X', 0)}件")
    print(f"   📈 出品候補総数: {total_valid}件 / {len(df)}件中")
    
    # 品質統計
    if total_valid > 0:
        avg_shopee_score = df[df['shopee_group'] != 'X']['shopee_suitability_score'].mean()
        avg_relevance = df[df['shopee_group'] != 'X']['relevance_score'].mean()
        print(f"   🎯 平均Shopee適性: {avg_shopee_score:.1f}点")
        print(f"   🎯 平均一致度: {avg_relevance:.1f}%")
    
    # グループ別詳細統計
    for group in ['A', 'B', 'C']:
        group_df = df[df['shopee_group'] == group]
        if len(group_df) > 0:
            group_avg_score = group_df['shopee_suitability_score'].mean()
            group_avg_relevance = group_df['relevance_score'].mean()
            print(f"     グループ{group}: Shopee適性{group_avg_score:.1f}点 | 一致度{group_avg_relevance:.1f}%")
    
    return df

def calculate_batch_status_shopee(df):
    """
    Shopee特化バッチ処理ステータス計算
    """
    total_items = len(df)
    if total_items == 0:
        return create_empty_status()
    
    # ASIN関連カラムの統一
    asin_column = get_asin_column(df)
    
    # 成功・失敗カウント
    if 'search_status' in df.columns:
        success_count = len(df[df['search_status'] == 'success'])
        failed_count = len(df[df['search_status'].isin(['error', 'no_results'])])
    elif asin_column:
        success_count = len(df[df[asin_column].notna() & (df[asin_column] != '') & (df[asin_column] != 'N/A')])
        failed_count = total_items - success_count
    else:
        success_count = 0
        failed_count = total_items
    
    processed_count = success_count + failed_count
    success_rate = (success_count / total_items * 100) if total_items > 0 else 0
    
    # Shopeeグループ統計
    if 'shopee_group' in df.columns:
        group_counts = df['shopee_group'].value_counts()
        group_a = group_counts.get('A', 0)
        group_b = group_counts.get('B', 0)
        group_c = group_counts.get('C', 0)
        group_x = group_counts.get('X', 0)
    else:
        # フォールバック：従来のconfidence_groupを使用
        if 'confidence_group' in df.columns:
            legacy_counts = df['confidence_group'].value_counts()
            group_a = legacy_counts.get('A', 0)
            group_b = legacy_counts.get('B', 0)
            group_c = legacy_counts.get('C', 0)
            group_x = 0
        else:
            group_a = group_b = group_c = group_x = 0
    
    # Prime統計
    prime_count = len(df[df.get('is_prime', False)]) if 'is_prime' in df.columns else 0
    amazon_seller_count = len(df[df.get('is_amazon_seller', False)]) if 'is_amazon_seller' in df.columns else 0
    official_seller_count = len(df[df.get('is_official_seller', False)]) if 'is_official_seller' in df.columns else 0
    
    # Shopee適性スコア統計
    if 'shopee_suitability_score' in df.columns:
        valid_scores = df[df['shopee_suitability_score'] > 0]['shopee_suitability_score']
        avg_shopee_score = valid_scores.mean() if len(valid_scores) > 0 else 0
        high_score_count = len(valid_scores[valid_scores >= 80])
    else:
        avg_shopee_score = 0
        high_score_count = 0
    
    return {
        # 基本統計
        'total': total_items,
        'processed': processed_count,
        'success': success_count,
        'failed': failed_count,
        'success_rate': success_rate,
        
        # Shopeeグループ統計
        'group_a': group_a,
        'group_b': group_b,
        'group_c': group_c,
        'group_x': group_x,
        'valid_candidates': group_a + group_b + group_c,
        
        # Prime・出品者統計
        'prime_count': prime_count,
        'amazon_seller_count': amazon_seller_count,
        'official_seller_count': official_seller_count,
        'prime_rate': (prime_count / total_items * 100) if total_items > 0 else 0,
        
        # Shopee適性統計
        'avg_shopee_score': avg_shopee_score,
        'high_score_count': high_score_count,
        'high_score_rate': (high_score_count / total_items * 100) if total_items > 0 else 0,
        
        # 進捗
        'progress': (processed_count / total_items * 100) if total_items > 0 else 0
    }

def export_shopee_optimized_excel(df):
    """
    Shopee出品最適化Excel出力
    """
    import io
    
    excel_buffer = io.BytesIO()
    
    # グループ別に分類
    groups = {
        'A': df[df['shopee_group'] == 'A'],
        'B': df[df['shopee_group'] == 'B'], 
        'C': df[df['shopee_group'] == 'C'],
        'X': df[df['shopee_group'] == 'X']
    }
    
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        # サマリーシート
        create_shopee_summary_sheet(writer, df, groups)
        
        # グループ別シート
        sheet_configs = [
            ('A', '🏆_即座出品可能_Prime+公式', '最優先で出品すべき商品'),
            ('B', '🟡_確認後出品_Prime+他社', '確認後に出品推奨する商品'),
            ('C', '🔵_検討対象_非Prime', '慎重に検討すべき商品'),
            ('X', '❌_除外_低品質', '出品対象外の商品')
        ]
        
        for group_key, sheet_name, description in sheet_configs:
            group_df = groups[group_key]
            if len(group_df) > 0:
                create_shopee_group_sheet(writer, group_df, sheet_name, description)
        
        # 統計シート
        create_shopee_stats_sheet(writer, df)
    
    excel_buffer.seek(0)
    return excel_buffer

def create_shopee_summary_sheet(writer, df, groups):
    """Shopeeサマリーシート作成"""
    summary_data = []
    
    for group_key in ['A', 'B', 'C', 'X']:
        group_df = groups[group_key]
        count = len(group_df)
        
        if count > 0:
            avg_shopee_score = group_df.get('shopee_suitability_score', pd.Series([0])).mean()
            avg_relevance = group_df.get('relevance_score', pd.Series([0])).mean()
            prime_rate = (len(group_df[group_df.get('is_prime', False)]) / count * 100) if count > 0 else 0
        else:
            avg_shopee_score = avg_relevance = prime_rate = 0
        
        group_names = {
            'A': '🏆 即座出品可能（Prime+公式）',
            'B': '🟡 確認後出品（Prime+他社）', 
            'C': '🔵 検討対象（非Prime）',
            'X': '❌ 除外対象'
        }
        
        summary_data.append({
            'グループ': group_names[group_key],
            '件数': count,
            '割合': f"{count/len(df)*100:.1f}%" if len(df) > 0 else "0%",
            'Shopee適性': f"{avg_shopee_score:.1f}点",
            '一致度': f"{avg_relevance:.1f}%",
            'Prime率': f"{prime_rate:.1f}%"
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_excel(writer, sheet_name='📊_Shopee出品サマリー', index=False)

def create_shopee_group_sheet(writer, group_df, sheet_name, description):
    """Shopeeグループ別シート作成"""
    # 必要カラムのみ抽出・整理
    output_columns = [
        'asin', 'amazon_asin', 'amazon_title', 'japanese_name', 
        'shopee_suitability_score', 'relevance_score',
        'is_prime', 'seller_name', 'seller_type',
        'amazon_brand', 'llm_source'
    ]
    
    # 存在するカラムのみ選択
    available_columns = [col for col in output_columns if col in group_df.columns]
    
    if available_columns:
        output_df = group_df[available_columns].copy()
        output_df.to_excel(writer, sheet_name=sheet_name, index=False)

def create_shopee_stats_sheet(writer, df):
    """Shopee統計シート作成"""
    stats_data = []
    
    # 基本統計
    total = len(df)
    success = len(df[df.get('search_status') == 'success']) if 'search_status' in df.columns else len(df[df.get('asin', '') != ''])
    
    stats_data.extend([
        ['基本統計', ''],
        ['総商品数', total],
        ['ASIN取得成功', success],
        ['成功率', f"{success/total*100:.1f}%" if total > 0 else "0%"],
        ['', ''],
    ])
    
    # Prime統計
    if 'is_prime' in df.columns:
        prime_count = len(df[df['is_prime']])
        stats_data.extend([
            ['Prime統計', ''],
            ['Prime対応商品', prime_count],
            ['Prime率', f"{prime_count/total*100:.1f}%" if total > 0 else "0%"],
            ['', ''],
        ])
    
    # 出品者統計
    if 'seller_type' in df.columns:
        seller_counts = df['seller_type'].value_counts()
        stats_data.extend([
            ['出品者統計', ''],
            ['Amazon出品', seller_counts.get('amazon', 0)],
            ['公式メーカー', seller_counts.get('official_manufacturer', 0)],
            ['サードパーティ', seller_counts.get('third_party', 0)],
            ['', '']
        ])
    
    stats_df = pd.DataFrame(stats_data, columns=['項目', '値'])
    stats_df.to_excel(writer, sheet_name='📈_詳細統計', index=False)

def update_approval_status(df, item_id, status):
    """
    承認状態を更新
    
    Args:
        df: データフレーム
        item_id: アイテムID（インデックス）
        status: 新しい状態（'approved', 'rejected', 'pending'）
    
    Returns:
        更新されたデータフレーム
    """
    if item_id in df.index:
        df.at[item_id, 'approval_status'] = status
        
        # 承認時は自動的にグループAに昇格（Shopee特化版）
        if status == 'approved':
            if 'shopee_group' in df.columns:
                df.at[item_id, 'shopee_group'] = 'A'
            else:
                df.at[item_id, 'confidence_group'] = 'A'
        # 却下時はグループXに降格
        elif status == 'rejected':
            if 'shopee_group' in df.columns:
                df.at[item_id, 'shopee_group'] = 'X'
            else:
                df.at[item_id, 'confidence_group'] = 'C'
    
    return df

def promote_to_group_a(df, item_ids):
    """
    指定されたアイテムをグループAに昇格
    
    Args:
        df: データフレーム
        item_ids: 昇格させるアイテムのIDリスト
    
    Returns:
        更新されたデータフレーム
    """
    for item_id in item_ids:
        if item_id in df.index:
            if 'shopee_group' in df.columns:
                df.at[item_id, 'shopee_group'] = 'A'
            else:
                df.at[item_id, 'confidence_group'] = 'A'
            df.at[item_id, 'approval_status'] = 'approved'
    
    return df

def get_asin_column(df):
    """ASINカラムを取得"""
    for col in ['asin', 'amazon_asin', 'ASIN']:
        if col in df.columns:
            return col
    return None

def create_empty_status():
    """空のステータスを作成"""
    return {
        'total': 0, 'processed': 0, 'success': 0, 'failed': 0, 'success_rate': 0,
        'group_a': 0, 'group_b': 0, 'group_c': 0, 'group_x': 0, 'valid_candidates': 0,
        'prime_count': 0, 'amazon_seller_count': 0, 'official_seller_count': 0, 'prime_rate': 0,
        'avg_shopee_score': 0, 'high_score_count': 0, 'high_score_rate': 0, 'progress': 0
    }

# ======================== 既存機能（後方互換性維持） ========================

def classify_confidence_groups(df, high_threshold=70, medium_threshold=40):
    """
    既存システム互換性のための分類関数
    
    ⚠️ 推奨: 新システムでは classify_for_shopee_listing を使用してください
    Prime+出品者情報が利用可能な場合は自動的にShopee特化分類を実行
    """
    print("⚠️ 既存システム互換モード: classify_confidence_groups")
    
    # Prime+出品者情報が利用可能かチェック
    has_prime_info = 'is_prime' in df.columns
    has_seller_info = 'seller_type' in df.columns
    has_shopee_score = 'shopee_suitability_score' in df.columns
    
    if has_prime_info and has_seller_info:
        print("   🚀 Prime+出品者情報検出 → Shopee特化分類を実行")
        shopee_classified = classify_for_shopee_listing(df)
        
        # 従来の confidence_group カラムを追加（互換性のため）
        def shopee_to_confidence(shopee_group):
            mapping = {'A': 'A', 'B': 'B', 'C': 'C', 'X': 'C'}
            return mapping.get(shopee_group, 'C')
        
        shopee_classified['confidence_group'] = shopee_classified['shopee_group'].apply(shopee_to_confidence)
        
        return shopee_classified
    
    else:
        print("   📊 従来システムで分類実行")
        return classify_legacy_confidence_groups(df, high_threshold, medium_threshold)

def classify_legacy_confidence_groups(df, high_threshold=70, medium_threshold=40):
    """
    従来の分類ロジック（Prime情報なしの場合）
    """
    df = df.copy()
    
    # 必要なカラムが存在しない場合は追加
    if 'is_prime' not in df.columns:
        df['is_prime'] = False
    
    if 'relevance_score' not in df.columns:
        df['relevance_score'] = 0
    
    # ASIN関連カラムの統一
    asin_column = get_asin_column(df)
    if asin_column is None:
        df['asin'] = ''
        asin_column = 'asin'
    
    # グループ分類（一致度中心）
    conditions = [
        df['relevance_score'] >= high_threshold,
        df['relevance_score'] >= medium_threshold,
        df['relevance_score'] < medium_threshold
    ]
    choices = ['A', 'B', 'C']
    df['confidence_group'] = np.select(conditions, choices, default='C')
    
    # Amazon商品ページリンク生成
    df['amazon_link'] = df[asin_column].apply(
        lambda asin: f"https://www.amazon.co.jp/dp/{asin}" if asin and pd.notna(asin) else ""
    )
    
    # 初期承認ステータス
    if 'approval_status' not in df.columns:
        df['approval_status'] = 'pending'
        
    # グループごとにソート
    df = df.sort_values(by=['confidence_group', 'relevance_score'], 
                        ascending=[True, False])
    
    # 統計出力
    group_counts = df['confidence_group'].value_counts().sort_index()
    print(f"📊 従来型分類結果:")
    print(f"   グループA（高一致度）: {group_counts.get('A', 0)}件")
    print(f"   グループB（中一致度）: {group_counts.get('B', 0)}件")
    print(f"   グループC（低一致度）: {group_counts.get('C', 0)}件")
    
    return df

def calculate_batch_status(df):
    """
    バッチ処理ステータスの計算（互換性維持）
    
    Shopee特化データがある場合は自動的にShopee統計を使用
    """
    # Shopee特化データがあるかチェック
    has_shopee_data = 'shopee_group' in df.columns
    
    if has_shopee_data:
        print("   📊 Shopee特化統計を使用")
        return calculate_batch_status_shopee(df)
    else:
        print("   📊 従来統計を使用")
        return calculate_legacy_batch_status(df)

def calculate_legacy_batch_status(df):
    """
    従来のバッチ処理ステータス計算
    """
    total_items = len(df)
    if total_items == 0:
        return create_empty_status()
    
    # ASIN関連カラムの統一
    asin_column = get_asin_column(df)
    
    # 処理済みカウント（search_statusがある場合）
    if 'search_status' in df.columns:
        processed_count = len(df[df['search_status'].notna()])
        success_count = len(df[df['search_status'] == 'success'])
        failed_count = processed_count - success_count
    elif asin_column:
        # search_statusがない場合はASINの有無で判定
        success_count = len(df[df[asin_column].notna() & (df[asin_column] != '') & (df[asin_column] != 'N/A')])
        processed_count = total_items  # 全件処理済みと仮定
        failed_count = total_items - success_count
    else:
        processed_count = total_items
        success_count = 0
        failed_count = 0
    
    # 成功率計算
    success_rate = (success_count / total_items * 100) if total_items > 0 else 0
    
    # グループごとの件数（confidence_groupがある場合）
    if 'confidence_group' in df.columns:
        group_a_count = len(df[df['confidence_group'] == 'A'])
        group_b_count = len(df[df['confidence_group'] == 'B'])
        group_c_count = len(df[df['confidence_group'] == 'C'])
    else:
        group_a_count = 0
        group_b_count = 0
        group_c_count = 0
    
    # 承認ステータスごとの件数
    if 'approval_status' in df.columns:
        approved_count = len(df[df['approval_status'] == 'approved'])
        rejected_count = len(df[df['approval_status'] == 'rejected'])
        pending_count = len(df[df['approval_status'] == 'pending'])
    else:
        approved_count = group_a_count
        rejected_count = 0
        pending_count = group_b_count
    
    # 進捗率計算
    progress_percentage = (processed_count / total_items * 100) if total_items > 0 else 0
    
    return {
        'total': total_items,
        'processed': processed_count,      
        'success': success_count,          
        'failed': failed_count,            
        'success_rate': success_rate,      
        'group_a': group_a_count,
        'group_b': group_b_count,
        'group_c': group_c_count,
        'group_x': 0,  # 従来版では除外グループなし
        'valid_candidates': group_a_count + group_b_count + group_c_count,
        'approved': approved_count,
        'rejected': rejected_count,
        'pending': pending_count,
        'progress': progress_percentage,
        
        # Shopee統計（互換性のため0で初期化）
        'prime_count': 0,
        'amazon_seller_count': 0,
        'official_seller_count': 0,
        'prime_rate': 0,
        'avg_shopee_score': 0,
        'high_score_count': 0,
        'high_score_rate': 0
    }

def export_to_excel_with_sheets(df, groups=None):
    """
    既存のExcel出力機能（互換性維持）
    
    Shopee特化データがある場合は自動的にShopee最適化出力を使用
    """
    has_shopee_data = 'shopee_group' in df.columns
    
    if has_shopee_data:
        print("   📊 Shopee最適化Excel出力を使用")
        return export_shopee_optimized_excel(df)
    else:
        print("   📊 従来Excel出力を使用")
        return export_legacy_excel_with_sheets(df, groups)

def export_legacy_excel_with_sheets(df, groups=None):
    """
    従来のExcel出力機能
    """
    import io
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font
    
    # バッファを作成
    excel_buffer = io.BytesIO()
    
    # グループが指定されていない場合は自動分類
    if groups is None:
        df_classified = classify_legacy_confidence_groups(df)
        groups = {
            'group_a': df_classified[df_classified['confidence_group'] == 'A'],
            'group_b': df_classified[df_classified['confidence_group'] == 'B'],
            'group_c': df_classified[df_classified['confidence_group'] == 'C']
        }
    
    # Excelファイル作成
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        # サマリーシート
        summary_data = pd.DataFrame({
            'グループ': ['高一致度', '中一致度', '低一致度', '合計'],
            '件数': [
                len(groups['group_a']), 
                len(groups['group_b']), 
                len(groups['group_c']), 
                len(df)
            ],
            '割合': [
                f"{len(groups['group_a'])/len(df)*100:.1f}%" if len(df) > 0 else "0%", 
                f"{len(groups['group_b'])/len(df)*100:.1f}%" if len(df) > 0 else "0%", 
                f"{len(groups['group_c'])/len(df)*100:.1f}%" if len(df) > 0 else "0%",
                "100%"
            ]
        })
        summary_data.to_excel(writer, sheet_name='サマリー', index=False)
        
        # 各グループのシート
        groups['group_a'].to_excel(writer, sheet_name='A_高一致度', index=False)
        groups['group_b'].to_excel(writer, sheet_name='B_中一致度', index=False)
        groups['group_c'].to_excel(writer, sheet_name='C_低一致度', index=False)
        
        # 全データシート
        df.to_excel(writer, sheet_name='全データ', index=False)
        
        # ワークブック取得
        workbook = writer.book
        
        # シート書式設定
        for sheet_name in ['A_高一致度', 'B_中一致度', 'C_低一致度', '全データ']:
            if sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 15)  # ASIN列
                worksheet.set_column('B:C', 40)  # 商品名列
                worksheet.set_column('D:Z', 15)  # その他の列
                
                # ヘッダー行書式設定
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'bg_color': '#D9D9D9',
                    'border': 1
                })
                
                # ヘッダー行に書式適用
                for col_num in range(len(df.columns)):
                    worksheet.write(0, col_num, df.columns[col_num], header_format)
    
    excel_buffer.seek(0)
    return excel_buffer

def generate_demo_data(n_rows=10):
    """
    デモ用のサンプルデータを生成（Shopee特化対応）
    """
    np.random.seed(42)  # 再現性のため
    
    # より現実的なサンプル商品データ（Prime+出品者情報込み）
    products = [
        # 高評価商品（グループA想定）
        ('FANCL mild cleansing oil 120ml', 'ファンケル マイルド クレンジング オイル 120ml', 85, True, 'official_manufacturer'),
        ('MILBON elujuda hair treatment', 'ミルボン エルジューダ ヘアトリートメント', 78, True, 'amazon'),
        ('LEBEL iau serum shampoo 1000ml', 'ルベル イオ セラム シャンプー 1000ml', 82, True, 'official_manufacturer'),
        
        # 中評価商品（グループB想定）  
        ('YOLU calm night repair', 'ヨル カーム ナイト リペア', 65, True, 'third_party'),
        ('ORBIS essence moisturizer', 'オルビス エッセンス モイスチャライザー', 58, True, 'third_party'),
        ('TSUBAKI premium moist shampoo', 'ツバキ プレミアム モイスト シャンプー', 52, True, 'third_party'),
        
        # 低評価商品（グループC想定）
        ('generic hair oil treatment', 'ヘアオイル トリートメント', 45, False, 'third_party'),
        ('unknown brand face cream', 'フェイスクリーム', 38, False, 'third_party'),
        ('basic cleansing foam', 'クレンジング フォーム', 42, False, 'third_party'),
        ('simple moisturizing lotion', 'モイスチャライジング ローション', 35, False, 'third_party'),
    ]
    
    # 必要なら行数を調整
    if n_rows > len(products):
        products = products * (n_rows // len(products) + 1)
    products = products[:n_rows]
    
    # データフレーム生成
    data_rows = []
    for i, (eng_name, jp_name, relevance, is_prime, seller_type) in enumerate(products):
        # Prime+出品者情報に基づくShopee適性スコア計算
        shopee_score = 0
        if is_prime:
            shopee_score += 50
        
        if seller_type == 'amazon':
            shopee_score += 30
        elif seller_type == 'official_manufacturer':
            shopee_score += 25
        elif seller_type == 'third_party':
            shopee_score += 10
        
        shopee_score += min(relevance * 0.2, 20)
        
        data_rows.append({
            'clean_title': eng_name,
            'japanese_name': jp_name,
            'llm_source': 'GPT-4o' if np.random.random() > 0.2 else 'Gemini',
            'amazon_asin': f"B{i+1:09d}",
            'amazon_title': jp_name,
            'amazon_brand': jp_name.split()[0] if ' ' in jp_name else 'Unknown',
            'relevance_score': relevance + np.random.randint(-3, 4),  # ±3のランダム調整
            'is_prime': is_prime,
            'seller_type': seller_type,
            'is_amazon_seller': seller_type == 'amazon',
            'is_official_seller': seller_type == 'official_manufacturer',
            'seller_name': {
                'amazon': 'Amazon.co.jp',
                'official_manufacturer': jp_name.split()[0] + '株式会社',
                'third_party': f"サードパーティ{i+1}"
            }.get(seller_type, 'Unknown'),
            'search_status': 'success',
            'price': f"¥{np.random.randint(800, 8000)}",
            'extracted_brand': jp_name.split()[0] if ' ' in jp_name else '',
            'extracted_quantity': f"{np.random.choice(['120ml', '200ml', '500ml', '1000ml'])}" if np.random.random() > 0.3 else '',
            'relevance_details': f"ブランド一致: +25点, 重要語一致: +{np.random.randint(10,20)}点",
            'shopee_suitability_score': int(shopee_score)
        })
    
    df = pd.DataFrame(data_rows)
    
    # relevance_scoreを0-100の範囲に制限
    df['relevance_score'] = df['relevance_score'].clip(0, 100)
    
    return df

# ======================== 分析・診断機能 ========================

def analyze_classification_quality(df):
    """
    分類品質の分析レポート生成
    
    Args:
        df: 分類済みデータフレーム
    
    Returns:
        dict: 分析結果
    """
    # Shopee特化か従来分類かを判定
    has_shopee_classification = 'shopee_group' in df.columns
    group_column = 'shopee_group' if has_shopee_classification else 'confidence_group'
    
    if group_column not in df.columns:
        return {"error": "分類が実行されていません"}
    
    total = len(df)
    if total == 0:
        return {"error": "データが空です"}
    
    group_counts = df[group_column].value_counts()
    
    # 一致度統計
    relevance_stats = df.groupby(group_column)['relevance_score'].agg(['count', 'mean', 'min', 'max'])
    
    # ASIN取得率
    asin_column = get_asin_column(df)
    asin_rates = {}
    if asin_column:
        for group in group_counts.index:
            group_df = df[df[group_column] == group]
            if len(group_df) > 0:
                asin_success = len(group_df[group_df[asin_column].notna() & (group_df[asin_column] != '')])
                asin_rates[group] = (asin_success / len(group_df)) * 100
            else:
                asin_rates[group] = 0
    
    # Shopee特化統計
    shopee_stats = {}
    if has_shopee_classification:
        if 'shopee_suitability_score' in df.columns:
            shopee_stats['avg_shopee_score'] = df['shopee_suitability_score'].mean()
            shopee_stats['high_score_count'] = len(df[df['shopee_suitability_score'] >= 80])
        
        if 'is_prime' in df.columns:
            shopee_stats['prime_rate'] = (len(df[df['is_prime']]) / total) * 100
        
        if 'seller_type' in df.columns:
            shopee_stats['seller_distribution'] = df['seller_type'].value_counts().to_dict()
    
    return {
        "classification_type": "Shopee特化" if has_shopee_classification else "従来型",
        "total_items": total,
        "group_distribution": group_counts.to_dict(),
        "group_percentages": {group: (count / total) * 100 for group, count in group_counts.items()},
        "relevance_stats": relevance_stats.to_dict() if len(relevance_stats) > 0 else {},
        "asin_success_rates": asin_rates,
        "shopee_stats": shopee_stats,
        "quality_score": calculate_quality_score(df, group_column)
    }

def calculate_quality_score(df, group_column):
    """
    分類品質スコアの計算
    """
    if len(df) == 0:
        return 0
    
    if group_column == 'shopee_group':
        # Shopee特化品質スコア
        group_a_count = len(df[df[group_column] == 'A'])
        total_prime = len(df[df.get('is_prime', False)]) if 'is_prime' in df.columns else 0
        
        # グループAの精密度（Prime商品がちゃんとグループAに分類されているか）
        precision_a = (group_a_count / total_prime) if total_prime > 0 else 0
        
        # Shopee適性スコアの平均
        avg_shopee_score = df.get('shopee_suitability_score', pd.Series([0])).mean() / 100
        
        # 総合品質スコア
        quality_score = (precision_a * 0.4 + avg_shopee_score * 0.6) * 100
    else:
        # 従来品質スコア
        group_a_count = len(df[df[group_column] == 'A'])
        high_relevance_count = len(df[df['relevance_score'] >= 70])
        
        # グループAの精度（高一致度商品がちゃんとグループAに分類されているか）
        precision_a = (group_a_count / high_relevance_count) if high_relevance_count > 0 else 0
        
        # 全体的なバランス
        group_balance = 1 - abs(0.3 - (group_a_count / len(df)))  # 理想は全体の30%程度がグループA
        
        # 総合品質スコア
        quality_score = (precision_a * 0.7 + group_balance * 0.3) * 100
    
    return min(quality_score, 100)

# テスト関数
def test_shopee_classification():
    """
    Shopee特化分類のテスト
    """
    print("🧪 Shopee特化分類テスト開始")
    
    # テストデータ生成
    test_df = generate_demo_data(20)
    
    print(f"\n📊 テストデータ: {len(test_df)}件")
    print("Prime+出品者分布:")
    for _, row in test_df.iterrows():
        print(f"  {row['clean_title'][:30]}... → Prime:{row['is_prime']}, 出品者:{row['seller_type']}, Shopee適性:{row['shopee_suitability_score']}点")
    
    # 分類実行
    classified_df = classify_for_shopee_listing(test_df)
    
    # 分析実行
    analysis = analyze_classification_quality(classified_df)
    
    print(f"\n📈 Shopee特化分類結果分析:")
    print(f"  グループA: {analysis['group_distribution'].get('A', 0)}件 ({analysis['group_percentages'].get('A', 0):.1f}%)")
    print(f"  グループB: {analysis['group_distribution'].get('B', 0)}件 ({analysis['group_percentages'].get('B', 0):.1f}%)")
    print(f"  グループC: {analysis['group_distribution'].get('C', 0)}件 ({analysis['group_percentages'].get('C', 0):.1f}%)")
    print(f"  グループX: {analysis['group_distribution'].get('X', 0)}件 ({analysis['group_percentages'].get('X', 0):.1f}%)")
    print(f"  品質スコア: {analysis['quality_score']:.1f}/100")
    
    if 'shopee_stats' in analysis and analysis['shopee_stats']:
        shopee_stats = analysis['shopee_stats']
        print(f"  平均Shopee適性: {shopee_stats.get('avg_shopee_score', 0):.1f}点")
        print(f"  Prime率: {shopee_stats.get('prime_rate', 0):.1f}%")
        if 'seller_distribution' in shopee_stats:
            print(f"  出品者分布: {shopee_stats['seller_distribution']}")
    
    print("\n✅ Shopee特化分類テスト完了")
    return classified_df, analysis

if __name__ == "__main__":
    # テスト実行
    test_df, analysis = test_shopee_classification()
    print("\n🎯 Shopee特化機能統合テスト完了")