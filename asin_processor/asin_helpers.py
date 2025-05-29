# Prime判定最優先システム（asin_helpers.py 置き換え用）
import pandas as pd
import numpy as np
from datetime import datetime
import re

# ======================== Prime判定最優先システム ========================

def calculate_prime_confidence_score(row):
    """
    Prime情報の信頼性スコアを計算（0-100点）
    """
    confidence_score = 50  # ベーススコア
    seller_name = str(row.get('seller_name', ''))
    if 'Amazon.co.jp' in seller_name or 'Amazon' == seller_name:
        confidence_score += 30
    elif '推定' in seller_name or 'Estimated' in seller_name:
        confidence_score -= 30
    elif seller_name and seller_name != 'nan':
        confidence_score += 10
    asin = str(row.get('asin', row.get('amazon_asin', '')))
    if asin.startswith('B0DR') or asin.startswith('B0DS'):
        confidence_score -= 20
    elif asin.startswith('B00') or asin.startswith('B01'):
        confidence_score += 10
    seller_type = str(row.get('seller_type', ''))
    is_prime = row.get('is_prime', False)
    if is_prime and seller_type == 'amazon':
        confidence_score += 20
    elif is_prime and seller_type == 'official_manufacturer':
        confidence_score += 15
    elif is_prime and seller_type == 'third_party':
        confidence_score += 5
    elif not is_prime and seller_type == 'amazon':
        confidence_score -= 25
    return max(0, min(100, confidence_score))

def classify_by_prime_priority(row):
    """
    Prime最優先の分類ロジック
    """
    is_prime = row.get('is_prime', False)
    seller_type = str(row.get('seller_type', 'unknown')).lower()
    prime_confidence = calculate_prime_confidence_score(row)
    if is_prime and prime_confidence >= 70:
        if seller_type in ['amazon', 'official_manufacturer']:
            return {
                'group': 'A',
                'reason': f'Prime確実({prime_confidence}点) + 優良出品者',
                'confidence': 'high',
                'prime_status': 'confirmed'
            }
        else:
            return {
                'group': 'B',
                'reason': f'Prime確実({prime_confidence}点) + サードパーティ',
                'confidence': 'medium',
                'prime_status': 'confirmed'
            }
    elif is_prime and prime_confidence >= 40:
        return {
            'group': 'B',
            'reason': f'Prime疑い({prime_confidence}点) - 要確認',
            'confidence': 'medium',
            'prime_status': 'needs_verification'
        }
    elif is_prime and prime_confidence < 40:
        return {
            'group': 'C',
            'reason': f'Prime情報低信頼性({prime_confidence}点)',
            'confidence': 'low',
            'prime_status': 'suspicious'
        }
    else:
        return {
            'group': 'C',
            'reason': 'Prime非対応',
            'confidence': 'high',
            'prime_status': 'not_prime'
        }

def classify_for_shopee_listing_prime_priority(df):
    """
    Prime判定最優先のShopee特化分類
    """
    df = df.copy()
    print("🏆 Prime判定最優先システム開始...")
    required_columns = {
        'is_prime': False,
        'seller_type': 'unknown',
        'seller_name': '',
        'shopee_suitability_score': 0,
        'relevance_score': 0
    }
    for col, default_val in required_columns.items():
        if col not in df.columns:
            df[col] = default_val
    df['prime_confidence_score'] = df.apply(calculate_prime_confidence_score, axis=1)
    classification_results = df.apply(classify_by_prime_priority, axis=1)
    df['shopee_group'] = classification_results.apply(lambda x: x['group'])
    df['classification_reason'] = classification_results.apply(lambda x: x['reason'])
    df['classification_confidence'] = classification_results.apply(lambda x: x['confidence'])
    df['prime_status'] = classification_results.apply(lambda x: x['prime_status'])
    priority_map = {
        'confirmed': 1, 'needs_verification': 2, 'suspicious': 3, 'not_prime': 4
    }
    df['prime_priority'] = df['prime_status'].map(priority_map)
    seller_priority_map = {
        'amazon': 1, 'official_manufacturer': 2, 'third_party': 3, 'unknown': 4
    }
    df['seller_priority'] = df['seller_type'].astype(str).str.lower().map(seller_priority_map).fillna(4)
    df = df.sort_values(
        by=['prime_priority', 'seller_priority', 'shopee_suitability_score'], 
        ascending=[True, True, False]
    ).reset_index(drop=True)
    group_stats = df['shopee_group'].value_counts().sort_index()
    prime_stats = df['prime_status'].value_counts()
    confidence_stats = df['prime_confidence_score'].describe()
    print(f"📊 Prime最優先分類結果:")
    print(f"   🏆 グループA（Prime確実+優良出品者）: {group_stats.get('A', 0)}件")
    print(f"   🟡 グループB（Prime疑い・要確認）: {group_stats.get('B', 0)}件")
    print(f"   🔵 グループC（非Prime・低信頼性）: {group_stats.get('C', 0)}件")
    print(f"\n🎯 Prime信頼性統計:")
    print(f"   Prime確実: {prime_stats.get('confirmed', 0)}件")
    print(f"   Prime要確認: {prime_stats.get('needs_verification', 0)}件")
    print(f"   Prime疑わしい: {prime_stats.get('suspicious', 0)}件")
    print(f"   非Prime: {prime_stats.get('not_prime', 0)}件")
    print(f"\n📈 Prime信頼性スコア: 平均{confidence_stats['mean']:.1f}点 (最小{confidence_stats['min']:.0f} - 最大{confidence_stats['max']:.0f})")
    return df

def generate_prime_verification_report(df):
    """
    Prime検証レポートの生成
    """
    total_items = len(df)
    if total_items == 0:
        return {"error": "データが空です"}
    report = {
        "総商品数": total_items,
        "Prime信頼性統計": {},
        "要注意商品": [],
        "推奨アクション": []
    }
    prime_status_counts = df['prime_status'].value_counts().to_dict()
    confidence_stats = df['prime_confidence_score'].describe().to_dict()
    report["Prime信頼性統計"] = {
        "Prime確実": prime_status_counts.get('confirmed', 0),
        "Prime要確認": prime_status_counts.get('needs_verification', 0),
        "Prime疑わしい": prime_status_counts.get('suspicious', 0),
        "非Prime": prime_status_counts.get('not_prime', 0),
        "平均信頼性スコア": f"{confidence_stats['mean']:.1f}点"
    }
    suspicious_items = df[
        (df['prime_status'] == 'suspicious') | 
        (df['prime_confidence_score'] < 50) |
        (df['seller_name'].astype(str).str.contains('推定', na=False))
    ]
    for idx, row in suspicious_items.iterrows():
        asin = row.get('asin', row.get('amazon_asin', 'N/A'))
        report["要注意商品"].append({
            "ASIN": asin,
            "商品名": row.get('clean_title', 'N/A')[:50],
            "Prime信頼性": f"{row.get('prime_confidence_score', 0)}点",
            "問題": row.get('classification_reason', 'N/A'),
            "Amazon_URL": f"https://www.amazon.co.jp/dp/{asin}"
        })
    high_risk_count = len(df[df['prime_confidence_score'] < 40])
    medium_risk_count = len(df[(df['prime_confidence_score'] >= 40) & (df['prime_confidence_score'] < 70)])
    if high_risk_count > 0:
        report["推奨アクション"].append(f"🚨 {high_risk_count}件の高リスク商品のAmazon商品ページを手動確認")
    if medium_risk_count > 0:
        report["推奨アクション"].append(f"⚠️ {medium_risk_count}件の中リスク商品の出品前確認を推奨")
    confirmed_count = len(df[df['prime_status'] == 'confirmed'])
    if confirmed_count > 0:
        report["推奨アクション"].append(f"✅ {confirmed_count}件のPrime確實商品は安全に出品可能")
    return report

def create_prime_priority_demo_data():
    """
    Prime最優先システム用のデモデータ生成
    """
    np.random.seed(42)
    products = [
        ('FANCL mild cleansing oil', 'ファンケル マイルド クレンジング オイル', True, 'amazon', 'Amazon.co.jp', 92),
        ('MILBON elujuda hair treatment', 'ミルボン エルジューダ', True, 'amazon', 'Amazon.co.jp', 88),
        ('Shiseido senka perfect whip', '資生堂 専科 パーフェクト ホイップ', True, 'official_manufacturer', '資生堂株式会社', 90),
        ('DHC deep cleansing oil', 'DHC ディープ クレンジング オイル', True, 'official_manufacturer', 'DHC公式', 87),
        ('TSUBAKI premium repair mask', 'ツバキ プレミアム リペア マスク', True, 'amazon', 'Amazon推定', 75),
        ('ROHTO hadalabo lotion', 'ロート 肌ラボ 化粧水', True, 'third_party', 'サードパーティ出品者A', 68),
        ("KIEHL'S ultra facial cream", 'キールズ ウルトラ クリーム', True, 'third_party', '化粧品専門店X', 80),
        ('LANEIGE water sleeping mask', 'ラネージュ ウォーター マスク', True, 'third_party', 'コスメ販売店Y', 76),
        ('Generic vitamin C serum', 'ビタミンC 美容液', False, 'third_party', '個人出品者A', 45),
        ('Unknown brand face mask', '無名ブランド フェイスマスク', False, 'third_party', '個人出品者B', 38),
        ('Suspicious Prime product', '疑わしいPrime商品', True, 'unknown', '不明出品者', 30),
    ]
    data_rows = []
    for i, (eng_name, jp_name, is_prime, seller_type, seller_name, base_score) in enumerate(products):
        if i < 4:
            asin = f"B00{i+1:06d}ABC"
        elif i < 8:
            asin = f"B01{i+1:06d}DEF"
        else:
            asin = f"B0DR{i+1:05d}XYZ"
        data_rows.append({
            'clean_title': eng_name,
            'japanese_name': jp_name,
            'asin': asin,
            'amazon_asin': asin,
            'amazon_title': jp_name,
            'is_prime': is_prime,
            'seller_type': seller_type,
            'seller_name': seller_name,
            'shopee_suitability_score': base_score + np.random.randint(-5, 6),
            'relevance_score': base_score + np.random.randint(-10, 11),
            'match_percentage': base_score + np.random.randint(-8, 9),
            'brand': jp_name.split()[0] if ' ' in jp_name else 'Unknown',
            'search_status': 'success',
            'llm_source': 'GPT-4o' if np.random.random() > 0.3 else 'Gemini'
        })
    df = pd.DataFrame(data_rows)
    for score_col in ['shopee_suitability_score', 'relevance_score', 'match_percentage']:
        df[score_col] = df[score_col].clip(0, 100)
    return df

def calculate_batch_status_prime_priority(df):
    """
    Prime最優先システム用のバッチ統計
    """
    total_items = len(df)
    if total_items == 0:
        return create_empty_status_prime_priority()
    prime_status_counts = df['prime_status'].value_counts() if 'prime_status' in df.columns else {}
    prime_confidence_avg = df['prime_confidence_score'].mean() if 'prime_confidence_score' in df.columns else 0
    group_counts = df['shopee_group'].value_counts() if 'shopee_group' in df.columns else {}
    asin_column = get_asin_column(df)
    if asin_column:
        success_count = len(df[df[asin_column].notna() & (df[asin_column] != '') & (df[asin_column] != 'N/A')])
    else:
        success_count = 0
    success_rate = (success_count / total_items * 100) if total_items > 0 else 0
    return {
        'total': total_items,
        'processed': total_items,
        'success': success_count,
        'failed': total_items - success_count,
        'success_rate': success_rate,
        'prime_confirmed': prime_status_counts.get('confirmed', 0),
        'prime_needs_verification': prime_status_counts.get('needs_verification', 0),
        'prime_suspicious': prime_status_counts.get('suspicious', 0),
        'prime_not_prime': prime_status_counts.get('not_prime', 0),
        'prime_confidence_avg': prime_confidence_avg,
        'group_a': group_counts.get('A', 0),
        'group_b': group_counts.get('B', 0),
        'group_c': group_counts.get('C', 0),
        'prime_count': prime_status_counts.get('confirmed', 0) + prime_status_counts.get('needs_verification', 0),
        'prime_rate': ((prime_status_counts.get('confirmed', 0) + prime_status_counts.get('needs_verification', 0)) / total_items * 100) if total_items > 0 else 0,
        'progress': 100,
        'valid_candidates': total_items
    }

def create_empty_status_prime_priority():
    """Prime最優先システム用の空ステータス"""
    return {
        'total': 0, 'processed': 0, 'success': 0, 'failed': 0, 'success_rate': 0,
        'prime_confirmed': 0, 'prime_needs_verification': 0, 'prime_suspicious': 0, 'prime_not_prime': 0, 'prime_confidence_avg': 0,
        'group_a': 0, 'group_b': 0, 'group_c': 0,
        'prime_count': 0, 'prime_rate': 0, 'progress': 0, 'valid_candidates': 0
    }

def get_asin_column(df):
    """ASINカラムを取得"""
    for col in ['asin', 'amazon_asin', 'ASIN']:
        if col in df.columns:
            return col
    return None

# ======================== 既存関数の置き換え ========================

# メイン分類関数をPrime最優先版に置き換え
classify_for_shopee_listing = classify_for_shopee_listing_prime_priority
calculate_batch_status_shopee = calculate_batch_status_prime_priority

generate_demo_data = create_prime_priority_demo_data

# ======================== テスト関数 ========================

def test_prime_priority_system():
    """
    Prime最優先システムのテスト
    """
    print("🧪 Prime最優先システムテスト開始")
    test_df = create_prime_priority_demo_data()
    print(f"\n📊 テストデータ: {len(test_df)}件")
    classified_df = classify_for_shopee_listing_prime_priority(test_df)
    print(f"\n📈 分類結果詳細:")
    for idx, row in classified_df.iterrows():
        asin = row['asin']
        group = row['shopee_group']
        prime_score = row['prime_confidence_score']
        reason = row['classification_reason']
        print(f"  {asin}: グループ{group} (Prime信頼性{prime_score}点) - {reason}")
    report = generate_prime_verification_report(classified_df)
    print(f"\n📋 Prime検証レポート:")
    for key, value in report.items():
        if key != "要注意商品":
            print(f"  {key}: {value}")
    return classified_df, report

if __name__ == "__main__":
    print("🎯 Prime最優先システムテスト開始")
    test_df, report = test_prime_priority_system()
    print("\n🎯 Prime最優先システムテスト完了")

# asin_helpers.py - 3グループ対応完全版（Prime+出品者情報統合+個別承認システム）
import pandas as pd
import numpy as np
from datetime import datetime
import re

# ======================== Shopee出品特化機能（3グループ版） ========================

def classify_for_shopee_listing(df):
    """
    Shopee出品特化型分類（3グループ版）
    
    グループA: Prime + Amazon/公式メーカー（最優秀 - 即座に出品可能）
    グループB: Prime + サードパーティ（良好 - 確認後出品推奨）
    グループC: 非Prime（参考 - 慎重検討）
    """
    df = df.copy()
    
    print("🎯 Shopee出品特化型分類開始（3グループ版）...")
    
    # 必要なカラムの確認・補完
    required_columns = {
        'is_prime': False,
        'seller_type': 'unknown',
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
    
    def shopee_classify_3groups(row):
        """3グループShopee出品特化分類ロジック"""
        seller_name = str(row.get('seller_name', ''))
        if '推定' in seller_name:
            return 'B'
        is_prime = row.get('is_prime', False)
        seller_type = row.get('seller_type', 'unknown')
        # 🏆 グループA: Prime + Amazon/公式メーカー（最優秀）
        if is_prime and seller_type in ['amazon', 'official_manufacturer']:
            return 'A'
        # 🟡 グループB: Prime + サードパーティ（良好）
        elif is_prime and seller_type == 'third_party':
            return 'B'
        # 🔵 グループC: 非Prime（すべて含める）
        else:
            return 'C'
    
    # 分類実行
    df['shopee_group'] = df.apply(shopee_classify_3groups, axis=1)
    
    # 優先度設定（グループ内ソート用）
    priority_map = {'A': 1, 'B': 2, 'C': 3}
    df['group_priority'] = df['shopee_group'].map(priority_map)
    
    # ソート：グループ優先度 → Shopee適性スコア降順 → 一致度降順
    df = df.sort_values(
        by=['group_priority', 'shopee_suitability_score', 'relevance_score'], 
        ascending=[True, False, False]
    ).reset_index(drop=True)
    
    # 統計情報出力
    group_stats = df['shopee_group'].value_counts().sort_index()
    total_items = len(df)
    
    print(f"📊 Shopee出品特化分類結果（3グループ版）:")
    print(f"   🏆 グループA（Prime+Amazon/公式）: {group_stats.get('A', 0)}件 - 即座に出品可能")
    print(f"   🟡 グループB（Prime+サードパーティ）: {group_stats.get('B', 0)}件 - 確認後出品推奨")
    print(f"   🔵 グループC（非Prime）: {group_stats.get('C', 0)}件 - 慎重検討")
    print(f"   📈 総商品数: {total_items}件（全て出品候補）")
    
    # 品質統計
    if total_items > 0:
        avg_shopee_score = df['shopee_suitability_score'].mean()
        avg_relevance = df['relevance_score'].mean()
        prime_rate = len(df[df['is_prime'] == True]) / total_items * 100
        print(f"   🎯 平均Shopee適性: {avg_shopee_score:.1f}点")
        print(f"   🎯 平均一致度: {avg_relevance:.1f}%")
        print(f"   🎯 Prime率: {prime_rate:.1f}%")
    
    # グループ別詳細統計
    for group in ['A', 'B', 'C']:
        group_df = df[df['shopee_group'] == group]
        if len(group_df) > 0:
            group_avg_score = group_df['shopee_suitability_score'].mean()
            group_avg_relevance = group_df['relevance_score'].mean()
            group_prime_rate = len(group_df[group_df['is_prime'] == True]) / len(group_df) * 100
            print(f"     グループ{group}: Shopee適性{group_avg_score:.1f}点 | 一致度{group_avg_relevance:.1f}% | Prime率{group_prime_rate:.1f}%")
    
    return df

def calculate_batch_status_shopee(df):
    """
    Shopee特化バッチ処理ステータス計算（3グループ版）
    """
    total_items = len(df)
    if total_items == 0:
        return create_empty_status_3groups()
    
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
    
    # 3グループ統計
    if 'shopee_group' in df.columns:
        group_counts = df['shopee_group'].value_counts()
        stats_data = {
            'group_a': group_counts.get('A', 0),
            'group_b': group_counts.get('B', 0),
            'group_c': group_counts.get('C', 0)
        }
    else:
        stats_data = {'group_a': 0, 'group_b': 0, 'group_c': 0}
    
    # Prime統計
    prime_count = len(df[df.get('is_prime', False)]) if 'is_prime' in df.columns else 0
    amazon_seller_count = len(df[df.get('seller_type', '') == 'amazon']) if 'seller_type' in df.columns else 0
    official_seller_count = len(df[df.get('seller_type', '') == 'official_manufacturer']) if 'seller_type' in df.columns else 0
    third_party_count = len(df[df.get('seller_type', '') == 'third_party']) if 'seller_type' in df.columns else 0
    
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
        
        # 3グループ統計
        'group_a': stats_data['group_a'],
        'group_b': stats_data['group_b'],
        'group_c': stats_data['group_c'],
        'valid_candidates': total_items,  # 3グループ版では全て有効候補
        
        # Prime・出品者統計
        'prime_count': prime_count,
        'amazon_seller_count': amazon_seller_count,
        'official_seller_count': official_seller_count,
        'third_party_count': third_party_count,
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
    Shopee出品最適化Excel出力（3グループ版）
    """
    import io
    
    excel_buffer = io.BytesIO()
    
    # 3グループ別に分類
    groups = {
        'A': df[df['shopee_group'] == 'A'],
        'B': df[df['shopee_group'] == 'B'], 
        'C': df[df['shopee_group'] == 'C']
    }
    
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        # サマリーシート
        create_shopee_summary_sheet_3groups(writer, df, groups)
        
        # 3グループ別シート
        sheet_configs = [
            ('A', '🏆_即座出品可能_Prime+公式', '最優先で出品すべき商品'),
            ('B', '🟡_確認後出品_Prime+他社', '確認後に出品推奨する商品'),
            ('C', '🔵_検討対象_非Prime', '慎重に検討すべき商品')
        ]
        
        for group_key, sheet_name, description in sheet_configs:
            group_df = groups[group_key]
            if len(group_df) > 0:
                create_shopee_group_sheet(writer, group_df, sheet_name, description)
        
        # 統計シート
        create_shopee_stats_sheet_3groups(writer, df)
    
    excel_buffer.seek(0)
    return excel_buffer

def create_shopee_summary_sheet_3groups(writer, df, groups):
    """3グループ版サマリーシート作成"""
    summary_data = []
    
    for group_key in ['A', 'B', 'C']:
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
            'C': '🔵 検討対象（非Prime）'
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

def create_shopee_stats_sheet_3groups(writer, df):
    """3グループ版統計シート作成"""
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
    
    # 3グループ統計
    if 'shopee_group' in df.columns:
        group_counts = df['shopee_group'].value_counts()
        stats_data.extend([
            ['グループ統計', ''],
            ['グループA（即座出品）', group_counts.get('A', 0)],
            ['グループB（確認後出品）', group_counts.get('B', 0)],
            ['グループC（慎重検討）', group_counts.get('C', 0)],
            ['', '']
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

def create_empty_status_3groups():
    """3グループ版空ステータス作成"""
    return {
        'total': 0, 'processed': 0, 'success': 0, 'failed': 0, 'success_rate': 0,
        'group_a': 0, 'group_b': 0, 'group_c': 0, 'valid_candidates': 0,
        'prime_count': 0, 'amazon_seller_count': 0, 'official_seller_count': 0, 'third_party_count': 0, 'prime_rate': 0,
        'avg_shopee_score': 0, 'high_score_count': 0, 'high_score_rate': 0, 'progress': 0
    }

def update_approval_status(df, item_id, status):
    """
    承認状態を更新（3グループ版）
    
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
            if 'shopee_group' in df.columns:
                df.at[item_id, 'shopee_group'] = 'A'
            else:
                df.at[item_id, 'confidence_group'] = 'A'
        # 却下時はグループCに降格（3グループ版）
        elif status == 'rejected':
            if 'shopee_group' in df.columns:
                df.at[item_id, 'shopee_group'] = 'C'
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
        print("   🚀 Prime+出品者情報検出 → Shopee特化分類（3グループ版）を実行")
        shopee_classified = classify_for_shopee_listing(df)
        
        # 従来の confidence_group カラムを追加（互換性のため）
        def shopee_to_confidence(shopee_group):
            mapping = {'A': 'A', 'B': 'B', 'C': 'C'}
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
        print("   📊 Shopee特化統計（3グループ版）を使用")
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
        return create_empty_status_3groups()
    
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
        'valid_candidates': group_a_count + group_b_count + group_c_count,
        'approved': approved_count,
        'rejected': rejected_count,
        'pending': pending_count,
        'progress': progress_percentage,
        
        # Shopee統計（互換性のため0で初期化）
        'prime_count': 0,
        'amazon_seller_count': 0,
        'official_seller_count': 0,
        'third_party_count': 0,
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
        print("   📊 Shopee最適化Excel出力（3グループ版）を使用")
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

def generate_demo_data(n_rows=16):
    """
    3グループ対応デモ用のサンプルデータを生成
    """
    np.random.seed(42)  # 再現性のため
    
    # 3グループ対応サンプル商品データ
    products = [
        # グループA: Prime + Amazon/公式メーカー (6件)
        ('FANCL mild cleansing oil 120ml', 'ファンケル マイルド クレンジング オイル 120ml', 85, True, 'official_manufacturer'),
        ('MILBON elujuda hair treatment', 'ミルボン エルジューダ ヘアトリートメント', 78, True, 'amazon'),
        ('Biore aqua rich watery essence', 'ビオレ アクア リッチ ウォータリー エッセンス', 82, True, 'amazon'),
        ('DHC deep cleansing oil', 'DHC ディープ クレンジング オイル', 80, True, 'official_manufacturer'),
        ('Shiseido senka perfect whip', '資生堂 専科 パーフェクト ホイップ', 83, True, 'amazon'),
        ('KOSE softymo deep cleansing oil', 'コーセー ソフティモ ディープ クレンジング オイル', 77, True, 'official_manufacturer'),
        
        # グループB: Prime + サードパーティ (6件)
        ('TSUBAKI premium repair mask', 'ツバキ プレミアム リペア マスク', 65, True, 'third_party'),
        ('ROHTO hadalabo gokujyun lotion', 'ロート 肌ラボ 極潤 化粧水', 68, True, 'third_party'),
        ('KANEBO suisai beauty clear powder', 'カネボウ スイサイ ビューティクリア パウダー', 62, True, 'third_party'),
        ('LANEIGE water sleeping mask', 'ラネージュ ウォーター スリーピング マスク', 70, True, 'third_party'),
        ('KIEHL\'S ultra facial cream', 'キールズ ウルトラ フェイシャル クリーム', 72, True, 'third_party'),
        ('INNISFREE green tea seed serum', 'イニスフリー グリーンティー シード セラム', 67, True, 'third_party'),
        
        # グループC: 非Prime (4件)
        ('Generic vitamin C serum', 'ビタミンC 美容液', 45, False, 'third_party'),
        ('Unknown brand face mask', '無名ブランド フェイスマスク', 38, False, 'third_party'),
        ('Basic moisturizer cream', 'ベーシック モイスチャライザー', 42, False, 'third_party'),
        ('Simple cleansing foam', 'シンプル クレンジング フォーム', 40, False, 'third_party'),
    ]
    
    # 必要に応じて行数調整
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
            'amazon_asin': f"B{i+1:09d}X{np.random.randint(10, 99)}",
            'asin': f"B{i+1:09d}X{np.random.randint(10, 99)}",
            'amazon_title': jp_name,
            'amazon_brand': jp_name.split()[0] if ' ' in jp_name else 'Unknown',
            'brand': jp_name.split()[0] if ' ' in jp_name else 'Unknown',
            'relevance_score': relevance + np.random.randint(-3, 4),
            'match_percentage': relevance + np.random.randint(-5, 6),
            'is_prime': is_prime,
            'seller_type': seller_type,
            'seller_name': {
                'amazon': 'Amazon.co.jp',
                'official_manufacturer': jp_name.split()[0] + '株式会社',
                'third_party': f"サードパーティ出品者{i+1}"
            }.get(seller_type, 'Unknown'),
            'search_status': 'success',
            'price': f"¥{np.random.randint(800, 8000)}",
            'extracted_brand': jp_name.split()[0] if ' ' in jp_name else '',
            'extracted_quantity': f"{np.random.choice(['120ml', '200ml', '500ml', '1000ml'])}" if np.random.random() > 0.3 else '',
            'relevance_details': f"ブランド一致: +25点, 重要語一致: +{np.random.randint(10,20)}点",
            'shopee_suitability_score': int(shopee_score)
        })
    
    df = pd.DataFrame(data_rows)
    
    # スコアを0-100の範囲に制限
    df['relevance_score'] = df['relevance_score'].clip(0, 100)
    df['match_percentage'] = df['match_percentage'].clip(0, 100)
    
    return df

# ======================== 分析・診断機能（3グループ版） ========================

def analyze_classification_quality(df):
    """
    分類品質の分析レポート生成（3グループ版）
    
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
        "classification_type": "Shopee特化（3グループ版）" if has_shopee_classification else "従来型",
        "total_items": total,
        "group_distribution": group_counts.to_dict(),
        "group_percentages": {group: (count / total) * 100 for group, count in group_counts.items()},
        "relevance_stats": relevance_stats.to_dict() if len(relevance_stats) > 0 else {},
        "asin_success_rates": asin_rates,
        "shopee_stats": shopee_stats,
        "quality_score": calculate_quality_score_3groups(df, group_column)
    }

def calculate_quality_score_3groups(df, group_column):
    """
    3グループ版分類品質スコアの計算
    """
    if len(df) == 0:
        return 0
    
    if group_column == 'shopee_group':
        # Shopee特化品質スコア（3グループ版）
        group_a_count = len(df[df[group_column] == 'A'])
        total_prime = len(df[df.get('is_prime', False)]) if 'is_prime' in df.columns else 0
        
        # グループAの精密度（Prime商品がちゃんとグループAに分類されているか）
        precision_a = (group_a_count / total_prime) if total_prime > 0 else 0
        
        # Shopee適性スコアの平均
        avg_shopee_score = df.get('shopee_suitability_score', pd.Series([0])).mean() / 100
        
        # 3グループバランス（理想的な分布）
        group_balance = 1 - abs(0.4 - (group_a_count / len(df)))  # 理想は全体の40%程度がグループA
        
        # 総合品質スコア
        quality_score = (precision_a * 0.4 + avg_shopee_score * 0.4 + group_balance * 0.2) * 100
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

# ======================== 個別承認システム機能（3グループ版） ========================

def initialize_approval_system(df):
    """
    承認システムの初期化（3グループ版）
    
    Args:
        df: 分類済みデータフレーム
    
    Returns:
        dict: 承認システムの初期状態
    """
    approval_state = {
        'pending_items': [],  # 承認待ちアイテム
        'approved_items': [],  # 承認済みアイテム 
        'rejected_items': [],  # 却下アイテム
        'approval_history': [],  # 承認履歴
        'last_updated': datetime.now()
    }
    
    # グループBのアイテムを承認待ちに設定
    if 'shopee_group' in df.columns:
        group_b_items = df[df['shopee_group'] == 'B'].copy()
        
        for idx, row in group_b_items.iterrows():
            item_data = {
                'index': idx,
                'asin': row.get('amazon_asin', row.get('asin', '')),
                'title': row.get('amazon_title', row.get('clean_title', '')),
                'brand': row.get('amazon_brand', row.get('brand', '')),
                'shopee_score': row.get('shopee_suitability_score', 0),
                'relevance_score': row.get('relevance_score', 0),
                'is_prime': row.get('is_prime', False),
                'seller_name': row.get('seller_name', ''),
                'seller_type': row.get('seller_type', ''),
                'status': 'pending',
                'amazon_url': f"https://www.amazon.co.jp/dp/{row.get('amazon_asin', row.get('asin', ''))}" if row.get('amazon_asin', row.get('asin', '')) else '',
                'original_data': row.to_dict()
            }
            approval_state['pending_items'].append(item_data)
    
    print(f"📋 承認システム初期化完了: {len(approval_state['pending_items'])}件の承認待ちアイテム")
    return approval_state

def approve_item(approval_state, item_index, reason="", approver="システム"):
    """
    アイテムを承認（グループAに昇格）
    
    Args:
        approval_state: 承認システム状態
        item_index: アイテムのインデックス
        reason: 承認理由
        approver: 承認者名
    
    Returns:
        tuple: (更新された承認状態, 成功フラグ)
    """
    try:
        # 承認待ちアイテムから該当アイテムを検索
        item_to_approve = None
        item_position = -1
        
        for i, item in enumerate(approval_state['pending_items']):
            if item['index'] == item_index:
                item_to_approve = item
                item_position = i
                break
        
        if item_to_approve is None:
            return approval_state, False
        
        # アイテムを承認済みに移動
        item_to_approve['status'] = 'approved'
        item_to_approve['approval_reason'] = reason
        item_to_approve['approver'] = approver
        item_to_approve['approval_date'] = datetime.now()
        
        approval_state['approved_items'].append(item_to_approve)
        approval_state['pending_items'].pop(item_position)
        
        # 承認履歴に記録
        history_entry = {
            'action': 'approved',
            'item_index': item_index,
            'asin': item_to_approve['asin'],
            'title': item_to_approve['title'][:50] + '...',
            'reason': reason,
            'approver': approver,
            'timestamp': datetime.now()
        }
        approval_state['approval_history'].append(history_entry)
        approval_state['last_updated'] = datetime.now()
        
        print(f"✅ アイテム承認完了: {item_to_approve['asin']} - {item_to_approve['title'][:30]}...")
        return approval_state, True
        
    except Exception as e:
        print(f"❌ 承認エラー: {str(e)}")
        return approval_state, False

def reject_item(approval_state, item_index, reason="", approver="システム"):
    """
    アイテムを却下（グループCに降格）
    
    Args:
        approval_state: 承認システム状態
        item_index: アイテムのインデックス
        reason: 却下理由
        approver: 承認者名
    
    Returns:
        tuple: (更新された承認状態, 成功フラグ)
    """
    try:
        # 承認待ちアイテムから該当アイテムを検索
        item_to_reject = None
        item_position = -1
        
        for i, item in enumerate(approval_state['pending_items']):
            if item['index'] == item_index:
                item_to_reject = item
                item_position = i
                break
        
        if item_to_reject is None:
            return approval_state, False
        
        # アイテムを却下済みに移動
        item_to_reject['status'] = 'rejected'
        item_to_reject['rejection_reason'] = reason
        item_to_reject['approver'] = approver
        item_to_reject['rejection_date'] = datetime.now()
        
        approval_state['rejected_items'].append(item_to_reject)
        approval_state['pending_items'].pop(item_position)
        
        # 承認履歴に記録
        history_entry = {
            'action': 'rejected',
            'item_index': item_index,
            'asin': item_to_reject['asin'],
            'title': item_to_reject['title'][:50] + '...',
            'reason': reason,
            'approver': approver,
            'timestamp': datetime.now()
        }
        approval_state['approval_history'].append(history_entry)
        approval_state['last_updated'] = datetime.now()
        
        print(f"❌ アイテム却下完了: {item_to_reject['asin']} - {item_to_reject['title'][:30]}...")
        return approval_state, True
        
    except Exception as e:
        print(f"❌ 却下エラー: {str(e)}")
        return approval_state, False

def bulk_approve_items(approval_state, item_indices, reason="一括承認", approver="システム"):
    """
    複数アイテムの一括承認
    
    Args:
        approval_state: 承認システム状態
        item_indices: 承認するアイテムのインデックスリスト
        reason: 承認理由
        approver: 承認者名
    
    Returns:
        tuple: (更新された承認状態, 成功カウント)
    """
    success_count = 0
    
    for item_index in item_indices:
        updated_state, success = approve_item(approval_state, item_index, reason, approver)
        if success:
            success_count += 1
            approval_state = updated_state
    
    print(f"📦 一括承認完了: {success_count}/{len(item_indices)}件成功")
    return approval_state, success_count

def apply_approval_to_dataframe(df, approval_state):
    """
    承認状態をデータフレームに適用（3グループ版）
    
    Args:
        df: 元のデータフレーム
        approval_state: 承認システム状態
    
    Returns:
        pd.DataFrame: 承認状態が適用されたデータフレーム
    """
    df_updated = df.copy()
    
    # 承認されたアイテムをグループAに昇格
    for approved_item in approval_state['approved_items']:
        item_index = approved_item['index']
        if item_index in df_updated.index:
            df_updated.at[item_index, 'shopee_group'] = 'A'
            df_updated.at[item_index, 'approval_status'] = 'approved'
            df_updated.at[item_index, 'approval_reason'] = approved_item.get('approval_reason', '')
            df_updated.at[item_index, 'approver'] = approved_item.get('approver', '')
            df_updated.at[item_index, 'approval_date'] = approved_item.get('approval_date', '')
    
    # 却下されたアイテムをグループCに降格
    for rejected_item in approval_state['rejected_items']:
        item_index = rejected_item['index']
        if item_index in df_updated.index:
            df_updated.at[item_index, 'shopee_group'] = 'C'
            df_updated.at[item_index, 'approval_status'] = 'rejected'
            df_updated.at[item_index, 'rejection_reason'] = rejected_item.get('rejection_reason', '')
            df_updated.at[item_index, 'approver'] = rejected_item.get('approver', '')
            df_updated.at[item_index, 'rejection_date'] = rejected_item.get('rejection_date', '')
    
    print(f"📊 承認状態適用完了: {len(approval_state['approved_items'])}件承認, {len(approval_state['rejected_items'])}件却下")
    return df_updated

def get_approval_statistics(approval_state):
    """
    承認システムの統計情報取得
    
    Args:
        approval_state: 承認システム状態
    
    Returns:
        dict: 統計情報
    """
    total_items = len(approval_state['pending_items']) + len(approval_state['approved_items']) + len(approval_state['rejected_items'])
    
    if total_items == 0:
        return {
            'total_items': 0,
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'progress': 0,
            'approval_rate': 0,
            'last_updated': approval_state['last_updated']
        }
    
    stats = {
        'total_items': total_items,
        'pending': len(approval_state['pending_items']),
        'approved': len(approval_state['approved_items']),
        'rejected': len(approval_state['rejected_items']),
        'progress': ((len(approval_state['approved_items']) + len(approval_state['rejected_items'])) / total_items * 100),
        'approval_rate': (len(approval_state['approved_items']) / total_items * 100),
        'last_updated': approval_state['last_updated']
    }
    
    return stats

def filter_pending_items(approval_state, filters=None):
    """
    承認待ちアイテムのフィルタリング
    
    Args:
        approval_state: 承認システム状態
        filters: フィルタ条件辞書
            - min_shopee_score: Shopee適性スコアの最小値
            - min_relevance_score: 一致度の最小値
            - seller_types: 出品者タイプのリスト
            - brands: ブランドのリスト
    
    Returns:
        list: フィルタされたアイテムリスト
    """
    if filters is None:
        return approval_state['pending_items']
    
    filtered_items = []
    
    for item in approval_state['pending_items']:
        # Shopee適性スコアフィルタ
        if 'min_shopee_score' in filters:
            if item.get('shopee_score', 0) < filters['min_shopee_score']:
                continue
        
        # 一致度フィルタ
        if 'min_relevance_score' in filters:
            if item.get('relevance_score', 0) < filters['min_relevance_score']:
                continue
        
        # 出品者タイプフィルタ
        if 'seller_types' in filters:
            if item.get('seller_type', '') not in filters['seller_types']:
                continue
        
        # ブランドフィルタ
        if 'brands' in filters:
            if item.get('brand', '') not in filters['brands']:
                continue
        
        filtered_items.append(item)
    
    print(f"🔍 フィルタ適用: {len(approval_state['pending_items'])}件 → {len(filtered_items)}件")
    return filtered_items

def export_approval_report(approval_state):
    """
    承認レポートのエクスポート
    
    Args:
        approval_state: 承認システム状態
    
    Returns:
        pd.DataFrame: 承認レポート
    """
    report_data = []
    
    # 承認済みアイテム
    for item in approval_state['approved_items']:
        report_data.append({
            'ステータス': '承認済み',
            'ASIN': item['asin'],
            '商品名': item['title'],
            'ブランド': item['brand'],
            'Shopee適性': item['shopee_score'],
            '一致度': item['relevance_score'],
            '出品者': item['seller_name'],
            '承認理由': item.get('approval_reason', ''),
            '承認者': item.get('approver', ''),
            '承認日時': item.get('approval_date', '')
        })
    
    # 却下アイテム
    for item in approval_state['rejected_items']:
        report_data.append({
            'ステータス': '却下',
            'ASIN': item['asin'],
            '商品名': item['title'],
            'ブランド': item['brand'],
            'Shopee適性': item['shopee_score'],
            '一致度': item['relevance_score'],
            '出品者': item['seller_name'],
            '承認理由': item.get('rejection_reason', ''),
            '承認者': item.get('approver', ''),
            '承認日時': item.get('rejection_date', '')
        })
    
    # 承認待ちアイテム
    for item in approval_state['pending_items']:
        report_data.append({
            'ステータス': '承認待ち',
            'ASIN': item['asin'],
            '商品名': item['title'],
            'ブランド': item['brand'],
            'Shopee適性': item['shopee_score'],
            '一致度': item['relevance_score'],
            '出品者': item['seller_name'],
            '承認理由': '',
            '承認者': '',
            '承認日時': ''
        })
    
    report_df = pd.DataFrame(report_data)
    return report_df

def suggest_auto_approval_candidates(approval_state, criteria=None):
    """
    自動承認候補の提案
    
    Args:
        approval_state: 承認システム状態
        criteria: 自動承認基準辞書
    
    Returns:
        list: 自動承認候補アイテムリスト
    """
    if criteria is None:
        # デフォルト基準
        criteria = {
            'min_shopee_score': 80,
            'min_relevance_score': 60,
            'preferred_seller_types': ['amazon', 'official_manufacturer']
        }
    
    candidates = []
    
    for item in approval_state['pending_items']:
        # 基準チェック
        meets_criteria = True
        reasons = []
        
        # Shopee適性スコア
        if item.get('shopee_score', 0) >= criteria.get('min_shopee_score', 80):
            reasons.append(f"高Shopee適性({item.get('shopee_score', 0)}点)")
        else:
            meets_criteria = False
        
        # 一致度
        if item.get('relevance_score', 0) >= criteria.get('min_relevance_score', 60):
            reasons.append(f"高一致度({item.get('relevance_score', 0)}%)")
        else:
            meets_criteria = False
        
        # 出品者タイプ
        if item.get('seller_type', '') in criteria.get('preferred_seller_types', []):
            reasons.append(f"優良出品者({item.get('seller_type', '')})")
        else:
            meets_criteria = False
        
        if meets_criteria:
            candidate = item.copy()
            candidate['auto_approval_reasons'] = reasons
            candidates.append(candidate)
    
    print(f"🤖 自動承認候補: {len(candidates)}件")
    return candidates

# テスト関数
def test_shopee_classification():
    """
    Shopee特化分類のテスト（3グループ版）
    """
    print("🧪 Shopee特化分類テスト開始（3グループ版）")
    
    # テストデータ生成
    test_df = generate_demo_data(16)
    
    print(f"\n📊 テストデータ: {len(test_df)}件")
    print("Prime+出品者分布:")
    for _, row in test_df.iterrows():
        print(f"  {row['clean_title'][:30]}... → Prime:{row['is_prime']}, 出品者:{row['seller_type']}, Shopee適性:{row['shopee_suitability_score']}点")
    
    # 分類実行
    classified_df = classify_for_shopee_listing(test_df)
    
    # 分析実行
    analysis = analyze_classification_quality(classified_df)
    
    print(f"\n📈 Shopee特化分類結果分析（3グループ版）:")
    print(f"  グループA: {analysis['group_distribution'].get('A', 0)}件 ({analysis['group_percentages'].get('A', 0):.1f}%)")
    print(f"  グループB: {analysis['group_distribution'].get('B', 0)}件 ({analysis['group_percentages'].get('B', 0):.1f}%)")
    print(f"  グループC: {analysis['group_distribution'].get('C', 0)}件 ({analysis['group_percentages'].get('C', 0):.1f}%)")
    print(f"  品質スコア: {analysis['quality_score']:.1f}/100")
    
    if 'shopee_stats' in analysis and analysis['shopee_stats']:
        shopee_stats = analysis['shopee_stats']
        print(f"  平均Shopee適性: {shopee_stats.get('avg_shopee_score', 0):.1f}点")
        print(f"  Prime率: {shopee_stats.get('prime_rate', 0):.1f}%")
        if 'seller_distribution' in shopee_stats:
            print(f"  出品者分布: {shopee_stats['seller_distribution']}")
    
    print("\n✅ Shopee特化分類テスト完了（3グループ版）")
    return classified_df, analysis

def test_approval_system():
    """
    承認システムのテスト（3グループ版）
    """
    print("🧪 個別承認システムテスト開始（3グループ版）")
    
    # テストデータ生成
    test_df = generate_demo_data(16)
    classified_df = classify_for_shopee_listing(test_df)
    
    # 承認システム初期化
    approval_state = initialize_approval_system(classified_df)
    
    print(f"\n📊 承認システム統計:")
    stats = get_approval_statistics(approval_state)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 自動承認候補
    candidates = suggest_auto_approval_candidates(approval_state)
    print(f"\n🤖 自動承認候補: {len(candidates)}件")
    
    # 1件承認テスト
    if approval_state['pending_items']:
        test_item = approval_state['pending_items'][0]
        updated_state, success = approve_item(approval_state, test_item['index'], "テスト承認")
        print(f"\n✅ テスト承認結果: {success}")
        
        # 承認状態をデータフレームに適用
        final_df = apply_approval_to_dataframe(classified_df, updated_state)
        
        # 最終統計
        final_stats = get_approval_statistics(updated_state)
        print(f"\n📈 最終統計:")
        for key, value in final_stats.items():
            print(f"  {key}: {value}")
    
    print("\n✅ 個別承認システムテスト完了（3グループ版）")
    return approval_state, classified_df

if __name__ == "__main__":
    # テスト実行
    print("🎯 3グループ対応 Shopee特化機能統合テスト開始")
    test_df, analysis = test_shopee_classification()
    approval_state, test_df = test_approval_system()
    print("\n🎯 3グループ対応 Shopee特化機能統合テスト完了")