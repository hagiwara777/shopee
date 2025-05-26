# asin_helpers.py - Shopee出品特化グルーピング（Prime+出品者情報対応）

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

# 後方互換性のための関数（既存コードとの互換性維持）
def classify_confidence_groups(df, high_threshold=70, medium_threshold=40):
    """
    後方互換性のためのラッパー関数
    新システムではclassify_for_shopee_listingを使用することを推奨
    """
    print("⚠️ 後方互換性モード: classify_confidence_groups")
    print("   推奨: classify_for_shopee_listing への移行")
    
    # Shopee特化分類を実行
    shopee_classified = classify_for_shopee_listing(df)
    
    # 従来の confidence_group カラムを追加（互換性のため）
    def shopee_to_confidence(shopee_group):
        mapping = {'A': 'A', 'B': 'B', 'C': 'C', 'X': 'C'}
        return mapping.get(shopee_group, 'C')
    
    shopee_classified['confidence_group'] = shopee_classified['shopee_group'].apply(shopee_to_confidence)
    
    return shopee_classified