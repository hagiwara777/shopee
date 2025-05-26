# asin_helpers.py - KeyError修正版
import pandas as pd
import numpy as np
from datetime import datetime
import re

def classify_confidence_groups(df, relevance_threshold=80):
    """
    ASINを3つの信頼度グループに分類
    A: Prime + 高一致度
    B: Prime + 低一致度
    C: 非Prime
    
    Args:
        df: 処理するデータフレーム
        relevance_threshold: 高一致度の閾値
    
    Returns:
        分類済みデータフレーム
    """
    # 必要なカラムが存在しない場合は追加
    if 'is_prime' not in df.columns:
        df['is_prime'] = False
    
    if 'relevance_score' not in df.columns:
        df['relevance_score'] = 0
    
    if 'asin' not in df.columns:
        df['asin'] = ''
    
    # グループ分類
    conditions = [
        (df['is_prime'] == True) & (df['relevance_score'] >= relevance_threshold),
        (df['is_prime'] == True) & (df['relevance_score'] < relevance_threshold),
        (df['is_prime'] == False)
    ]
    choices = ['A', 'B', 'C']
    df['confidence_group'] = np.select(conditions, choices, default='C')
    
    # Amazon商品ページリンク生成
    df['amazon_link'] = df['asin'].apply(
        lambda asin: f"https://www.amazon.co.jp/dp/{asin}" if asin and pd.notna(asin) else ""
    )
    
    # 初期承認ステータス
    if 'approval_status' not in df.columns:
        df['approval_status'] = 'pending'
        
    # グループごとにソート
    df = df.sort_values(by=['confidence_group', 'relevance_score'], 
                        ascending=[True, False])
    
    return df

def calculate_batch_status(df):
    """
    バッチ処理ステータスの計算（KeyError修正版）
    """
    total_items = len(df)
    if total_items == 0:
        return {
            'total': 0,
            'processed': 0,  # ← 追加
            'success': 0,    # ← 追加
            'failed': 0,     # ← 追加
            'success_rate': 0,  # ← 追加
            'group_a': 0,
            'group_b': 0,
            'group_c': 0,
            'approved': 0,
            'rejected': 0,
            'pending': 0,
            'progress': 0
        }
    
    # 処理済みカウント（search_statusがある場合）
    if 'search_status' in df.columns:
        processed_count = len(df[df['search_status'].notna()])
        success_count = len(df[df['search_status'] == 'success'])
        failed_count = processed_count - success_count
        success_rate = (success_count / total_items * 100) if total_items > 0 else 0
    else:
        # search_statusがない場合はASINの有無で判定
        asin_column = None
        for col in ['asin', 'amazon_asin', 'ASIN']:
            if col in df.columns:
                asin_column = col
                break
        
        if asin_column:
            success_count = len(df[df[asin_column].notna() & (df[asin_column] != '')])
            processed_count = total_items  # 全件処理済みと仮定
            failed_count = total_items - success_count
            success_rate = (success_count / total_items * 100) if total_items > 0 else 0
        else:
            processed_count = total_items
            success_count = 0
            failed_count = 0
            success_rate = 0
    
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
        'processed': processed_count,      # ← 修正: 追加
        'success': success_count,          # ← 修正: 追加
        'failed': failed_count,            # ← 修正: 追加
        'success_rate': success_rate,      # ← 修正: 追加
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
    グループA/B/Cを別シートに振り分けてExcelファイル出力
    """
    import io
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font
    
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
            'グループ': ['確実に使えるASIN', '要確認ASIN', '参考情報(非Prime)', '合計'],
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
        groups['group_a'].to_excel(writer, sheet_name='A_確実に使えるASIN', index=False)
        groups['group_b'].to_excel(writer, sheet_name='B_要確認ASIN', index=False)
        groups['group_c'].to_excel(writer, sheet_name='C_参考情報', index=False)
        
        # 全データシート
        df.to_excel(writer, sheet_name='全データ', index=False)
        
        # ワークブック取得
        workbook = writer.book
        
        # シート書式設定
        for sheet_name in ['A_確実に使えるASIN', 'B_要確認ASIN', 'C_参考情報', '全データ']:
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
    デモ用のサンプルデータを生成
    """
    np.random.seed(42)  # 再現性のため
    
    # サンプル商品データ
    products = [
        ('shiseido facial cotton 165 sheets', '資生堂 フェイシャルコットン'),
        ('biore uv aqua rich watery essence', 'ビオレ UV アクアリッチ'),
        ('hada labo gokujyun premium lotion', '肌ラボ 極潤プレミアム'),
        ('canmake mermaid skin gel uv', 'キャンメイク マーメイドスキン'),
        ('melano cc vitamin c essence', 'メラノCC 美容液'),
        ('kose softymo deep cleansing oil', 'コーセー ソフティモ クレンジング'),
        ('rohto mentholatum lip baby', 'ロート メンソレータム リップベビー'),
        ('naturie hatomugi skin conditioner', 'ナチュリエ ハトムギ化粧水'),
        ('muji sensitive skin moisturizing milk', '無印良品 敏感肌用乳液'),
        ('kao curel intensive moisture care', '花王 キュレル 保湿クリーム')
    ]
    
    # 必要なら行数を調整
    if n_rows > len(products):
        products = products * (n_rows // len(products) + 1)
    products = products[:n_rows]
    
    # データフレーム生成
    df = pd.DataFrame({
        'clean_title': [p[0] for p in products],
        'japanese_name': [p[1] for p in products],
    })
    
    # ASIN生成
    df['asin'] = [f"B0{i:08d}" for i in range(1, n_rows+1)]
    
    # Prime状態をランダム生成
    df['is_prime'] = np.random.choice([True, False], size=n_rows, p=[0.7, 0.3])
    
    # 一致度スコアをランダム生成
    df['relevance_score'] = np.random.randint(40, 101, size=n_rows)
    
    # 価格をランダム生成
    df['price'] = [f"¥{np.random.randint(1000, 10000)}" for _ in range(n_rows)]
    
    # search_status追加
    df['search_status'] = 'success'
    
    return df