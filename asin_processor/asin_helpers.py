# asin_helpers.py - 改良版グループ分類対応（完全修正版）
import pandas as pd
import numpy as np
from datetime import datetime
import re

def classify_confidence_groups(df, high_threshold=70, medium_threshold=40):
    """
    ASINを3つの信頼度グループに分類（改良版）
    Prime判定に依存せず、一致度とASIN存在で分類
    
    A: 一致度70%以上 & ASIN有り（確実に使える）
    B: 一致度40-69% & ASIN有り（要確認）
    C: 一致度39%以下 または ASIN無し（参考）
    
    Args:
        df: 処理するデータフレーム
        high_threshold: グループA分類の閾値（デフォルト70%）
        medium_threshold: グループB分類の閾値（デフォルト40%）
    
    Returns:
        分類済みデータフレーム
    """
    df = df.copy()
    
    # 必要なカラムが存在しない場合は追加・補完
    if 'is_prime' not in df.columns:
        df['is_prime'] = False
    
    if 'relevance_score' not in df.columns:
        df['relevance_score'] = 0
    
    # ASIN関連カラムの統一（複数のカラム名に対応）
    asin_column = None
    for col in ['asin', 'amazon_asin', 'ASIN']:
        if col in df.columns:
            asin_column = col
            break
    
    if asin_column is None:
        df['asin'] = ''
        asin_column = 'asin'
    
    # ASINの存在チェック
    df['has_asin'] = df[asin_column].notna() & (df[asin_column] != '') & (df[asin_column] != 'N/A')
    
    # 改良版グループ分類（Prime判定に依存しない）
    def classify_group(row):
        relevance = row.get('relevance_score', 0)
        has_asin = row.get('has_asin', False)
        
        # ASIN無しは必ずグループC
        if not has_asin:
            return 'C'
        
        # ASIN有りの場合は一致度で分類
        if relevance >= high_threshold:  # 70%以上
            return 'A'
        elif relevance >= medium_threshold:  # 40-69%
            return 'B'
        else:  # 39%以下
            return 'C'
    
    df['confidence_group'] = df.apply(classify_group, axis=1)
    
    # Amazon商品ページリンク生成
    df['amazon_link'] = df[asin_column].apply(
        lambda asin: f"https://www.amazon.co.jp/dp/{asin}" if asin and pd.notna(asin) and asin != '' else ""
    )
    
    # 初期承認ステータス
    if 'approval_status' not in df.columns:
        # グループAは自動承認、その他はpending
        df['approval_status'] = df['confidence_group'].apply(
            lambda group: 'approved' if group == 'A' else 'pending'
        )
    
    # グループごとにソート（グループA→B→C、各グループ内は一致度降順）
    df = df.sort_values(
        by=['confidence_group', 'relevance_score'], 
        ascending=[True, False]
    ).reset_index(drop=True)
    
    # デバッグ情報出力
    group_counts = df['confidence_group'].value_counts().sort_index()
    print(f"📊 改良版グループ分類結果:")
    print(f"   グループA（確実）: {group_counts.get('A', 0)}件")
    print(f"   グループB（要確認）: {group_counts.get('B', 0)}件")
    print(f"   グループC（参考）: {group_counts.get('C', 0)}件")
    
    # 一致度分布の表示
    if len(df) > 0:
        avg_relevance = df['relevance_score'].mean()
        max_relevance = df['relevance_score'].max()
        print(f"   平均一致度: {avg_relevance:.1f}%")
        print(f"   最高一致度: {max_relevance:.1f}%")
    
    return df

def calculate_batch_status(df):
    """
    バッチ処理ステータスの計算（改良版）
    """
    total_items = len(df)
    if total_items == 0:
        return {
            'total': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'success_rate': 0,
            'group_a': 0,
            'group_b': 0,
            'group_c': 0,
            'approved': 0,
            'rejected': 0,
            'pending': 0,
            'progress': 0
        }
    
    # ASIN関連カラムの統一
    asin_column = None
    for col in ['asin', 'amazon_asin', 'ASIN']:
        if col in df.columns:
            asin_column = col
            break
    
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
        pending_count = group_b_count + group_c_count
    
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
        'approved': approved_count,
        'rejected': rejected_count,
        'pending': pending_count,
        'progress': progress_percentage
    }

def export_to_excel_with_sheets(df, groups=None):
    """
    グループA/B/Cを別シートに振り分けてExcelファイル出力（改良版）
    """
    import io
    
    # バッファを作成
    excel_buffer = io.BytesIO()
    
    # グループが指定されていない場合は自動分類
    if groups is None:
        df_classified = classify_confidence_groups(df)
        groups = {
            'group_a': df_classified[df_classified['confidence_group'] == 'A'],
            'group_b': df_classified[df_classified['confidence_group'] == 'B'],
            'group_c': df_classified[df_classified['confidence_group'] == 'C']
        }
    
    # Excelファイル作成
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        # サマリーシート
        summary_data = pd.DataFrame({
            'グループ': ['A: 確実に使えるASIN', 'B: 要確認ASIN', 'C: 参考情報', '合計'],
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
            ],
            '説明': [
                '一致度70%以上、即座に使用可能',
                '一致度40-69%、手動確認推奨',
                '一致度39%以下または検索失敗',
                '全体データ'
            ]
        })
        summary_data.to_excel(writer, sheet_name='📊_サマリー', index=False)
        
        # 各グループのシート
        if len(groups['group_a']) > 0:
            groups['group_a'].to_excel(writer, sheet_name='✅_グループA_確実', index=False)
        
        if len(groups['group_b']) > 0:
            groups['group_b'].to_excel(writer, sheet_name='⚠️_グループB_要確認', index=False)
        
        if len(groups['group_c']) > 0:
            groups['group_c'].to_excel(writer, sheet_name='📝_グループC_参考', index=False)
        
        # 全データシート
        df.to_excel(writer, sheet_name='📋_全データ', index=False)
        
        # ワークブック取得してフォーマット設定
        workbook = writer.book
        
        # シート書式設定
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            
            # 列幅の調整
            if 'サマリー' not in sheet_name:
                worksheet.set_column('A:A', 12)  # ASIN列
                worksheet.set_column('B:D', 35)  # 商品名・日本語化列
                worksheet.set_column('E:H', 15)  # その他の列
                worksheet.set_column('I:Z', 12)  # 残りの列
            
            # ヘッダー行書式設定
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'bg_color': '#E6F3FF',
                'border': 1,
                'font_size': 10
            })
            
            # データ行書式設定
            cell_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1,
                'font_size': 9
            })
    
    excel_buffer.seek(0)
    return excel_buffer

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
        
        # 承認時は自動的にグループAに昇格
        if status == 'approved':
            df.at[item_id, 'confidence_group'] = 'A'
        # 却下時はグループCに降格
        elif status == 'rejected':
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
            df.at[item_id, 'confidence_group'] = 'A'
            df.at[item_id, 'approval_status'] = 'approved'
    
    return df

def generate_demo_data(n_rows=10):
    """
    デモ用のサンプルデータを生成（改良版）
    """
    np.random.seed(42)  # 再現性のため
    
    # より現実的なサンプル商品データ（一致度を現実的な分布に）
    products = [
        # 高一致度商品（グループA想定）
        ('FANCL mild cleansing oil 120ml', 'ファンケル マイルド クレンジング オイル 120ml', 85),
        ('MILBON elujuda hair treatment', 'ミルボン エルジューダ ヘアトリートメント', 78),
        ('LEBEL iau serum shampoo 1000ml', 'ルベル イオ セラム シャンプー 1000ml', 82),
        
        # 中一致度商品（グループB想定）  
        ('YOLU calm night repair', 'ヨル カーム ナイト リペア', 65),
        ('ORBIS essence moisturizer', 'オルビス エッセンス モイスチャライザー', 58),
        ('TSUBAKI premium moist shampoo', 'ツバキ プレミアム モイスト シャンプー', 52),
        
        # 低一致度商品（グループC想定）
        ('generic hair oil treatment', 'ヘアオイル トリートメント', 32),
        ('unknown brand face cream', 'フェイスクリーム', 28),
        ('basic cleansing foam', 'クレンジング フォーム', 35),
        ('simple moisturizing lotion', 'モイスチャライジング ローション', 25),
    ]
    
    # 必要なら行数を調整
    if n_rows > len(products):
        products = products * (n_rows // len(products) + 1)
    products = products[:n_rows]
    
    # データフレーム生成
    data_rows = []
    for i, (eng_name, jp_name, relevance) in enumerate(products):
        # 一致度に基づいてASINの有無を決定（低い場合は検索失敗する可能性）
        has_asin = relevance > 30 and np.random.random() > 0.1  # 30%以下は高確率で検索失敗
        
        data_rows.append({
            'clean_title': eng_name,
            'japanese_name': jp_name,
            'llm_source': 'GPT-4o' if np.random.random() > 0.2 else 'Gemini',  # 80%はGPT-4o
            'amazon_asin': f"B{i+1:09d}" if has_asin else '',
            'amazon_title': jp_name if has_asin else '',
            'amazon_brand': jp_name.split()[0] if has_asin and ' ' in jp_name else '',
            'relevance_score': relevance + np.random.randint(-5, 6),  # ±5のランダム調整
            'is_prime': np.random.choice([True, False], p=[0.7, 0.3]),
            'search_status': 'success' if has_asin else 'no_results',
            'price': f"¥{np.random.randint(800, 8000)}" if has_asin else '',
            'extracted_brand': jp_name.split()[0] if ' ' in jp_name else '',
            'extracted_quantity': f"{np.random.choice(['120ml', '200ml', '500ml', '1000ml'])}" if np.random.random() > 0.3 else '',
            'relevance_details': f"ブランド一致: +25点, 重要語一致: +{np.random.randint(10,20)}点"
        })
    
    df = pd.DataFrame(data_rows)
    
    # relevance_scoreを0-100の範囲に制限
    df['relevance_score'] = df['relevance_score'].clip(0, 100)
    
    return df

def analyze_classification_quality(df):
    """
    分類品質の分析レポート生成
    
    Args:
        df: 分類済みデータフレーム
    
    Returns:
        dict: 分析結果
    """
    if 'confidence_group' not in df.columns:
        return {"error": "分類が実行されていません"}
    
    total = len(df)
    if total == 0:
        return {"error": "データが空です"}
    
    group_counts = df['confidence_group'].value_counts()
    
    # 一致度統計
    relevance_stats = df.groupby('confidence_group')['relevance_score'].agg(['count', 'mean', 'min', 'max'])
    
    # ASIN取得率
    asin_column = None
    for col in ['asin', 'amazon_asin', 'ASIN']:
        if col in df.columns:
            asin_column = col
            break
    
    asin_rates = {}
    if asin_column:
        for group in ['A', 'B', 'C']:
            group_df = df[df['confidence_group'] == group]
            if len(group_df) > 0:
                asin_success = len(group_df[group_df[asin_column].notna() & (group_df[asin_column] != '')])
                asin_rates[group] = (asin_success / len(group_df)) * 100
            else:
                asin_rates[group] = 0
    
    return {
        "total_items": total,
        "group_distribution": {
            "A": group_counts.get('A', 0),
            "B": group_counts.get('B', 0), 
            "C": group_counts.get('C', 0)
        },
        "group_percentages": {
            "A": (group_counts.get('A', 0) / total) * 100,
            "B": (group_counts.get('B', 0) / total) * 100,
            "C": (group_counts.get('C', 0) / total) * 100
        },
        "relevance_stats": relevance_stats.to_dict() if len(relevance_stats) > 0 else {},
        "asin_success_rates": asin_rates,
        "quality_score": calculate_quality_score(df)
    }

def calculate_quality_score(df):
    """
    分類品質スコアの計算
    """
    if len(df) == 0:
        return 0
    
    group_a_count = len(df[df['confidence_group'] == 'A'])
    high_relevance_count = len(df[df['relevance_score'] >= 70])
    
    # グループAの精度（高一致度商品がちゃんとグループAに分類されているか）
    precision_a = (group_a_count / high_relevance_count) if high_relevance_count > 0 else 0
    
    # 全体的なバランス（極端に偏っていないか）
    group_balance = 1 - abs(0.5 - (group_a_count / len(df)))  # 理想は全体の30-50%がグループA
    
    # 総合品質スコア
    quality_score = (precision_a * 0.7 + group_balance * 0.3) * 100
    
    return min(quality_score, 100)

# テスト関数
def test_improved_classification():
    """
    改良版分類のテスト
    """
    print("🧪 改良版グループ分類テスト開始")
    
    # テストデータ生成
    test_df = generate_demo_data(20)
    
    print(f"\n📊 テストデータ: {len(test_df)}件")
    print("一致度分布:")
    for _, row in test_df.iterrows():
        print(f"  {row['clean_title'][:30]}... → {row['relevance_score']}%")
    
    # 分類実行
    classified_df = classify_confidence_groups(test_df)
    
    # 分析実行
    analysis = analyze_classification_quality(classified_df)
    
    print(f"\n📈 分類結果分析:")
    print(f"  グループA: {analysis['group_distribution']['A']}件 ({analysis['group_percentages']['A']:.1f}%)")
    print(f"  グループB: {analysis['group_distribution']['B']}件 ({analysis['group_percentages']['B']:.1f}%)")
    print(f"  グループC: {analysis['group_distribution']['C']}件 ({analysis['group_percentages']['C']:.1f}%)")
    print(f"  品質スコア: {analysis['quality_score']:.1f}/100")
    
    return classified_df, analysis

if __name__ == "__main__":
    # テスト実行
    test_df, analysis = test_improved_classification()
    print("\n✅ 改良版グループ分類テスト完了")