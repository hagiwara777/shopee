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

# ======================== ShippingTime最優先システム v7（2グループ版） ========================

def shopee_classify_shipping_simple(row):
    """
    シンプル2グループ分類 - ShippingTime最優先システム v7
    A: 24時間以内発送（DTS規約クリア確実）
    B: それ以外（在庫管理で制御）
    """
    ship_hours = row.get("ship_hours")
    if ship_hours is not None:
        if ship_hours <= 24:
            return "A"
        else:
            return "B"
    else:
        return "B"

def classify_for_shopee_listing_v7(df):
    """
    ShippingTime最優先システム v7 - 2グループ分類版
    グループA: 24時間以内発送（DTS規約クリア確実）
    グループB: それ以外（在庫管理で制御）
    """
    df = df.copy()
    print("🚀 ShippingTime最優先システム v7 開始（2グループ版）...")
    required_columns = {
        'ship_hours': None,
        'ship_bucket': '',
        'is_prime': False,
        'seller_type': 'unknown',
        'shopee_suitability_score': 0,
        'relevance_score': 0
    }
    for col, default_val in required_columns.items():
        if col not in df.columns:
            df[col] = default_val
    df['shopee_group'] = df.apply(shopee_classify_shipping_simple, axis=1)
    priority_map = {'A': 1, 'B': 2}
    df['group_priority'] = df['shopee_group'].map(priority_map)
    df = df.sort_values(
        by=['group_priority', 'ship_hours', 'shopee_suitability_score'],
        ascending=[True, True, False]
    ).reset_index(drop=True)
    group_stats = df['shopee_group'].value_counts().sort_index()
    total_items = len(df)
    print(f"📊 ShippingTime最優先分類結果（2グループ版）:")
    print(f"   🏆 グループA（24時間以内発送）: {group_stats.get('A', 0)}件 - DTS規約クリア確実")
    print(f"   📦 グループB（それ以外）: {group_stats.get('B', 0)}件 - 在庫管理で制御")
    print(f"   📈 総商品数: {total_items}件")
    if 'ship_hours' in df.columns:
        ship_available = len(df[df['ship_hours'].notna()])
        ship_rate = (ship_available / total_items * 100) if total_items > 0 else 0
        avg_ship_hours = df[df['ship_hours'].notna()]['ship_hours'].mean() if ship_available > 0 else 0
        print(f"   ⏰ ShippingTime取得率: {ship_rate:.1f}% ({ship_available}/{total_items})")
        print(f"   ⏰ 平均発送時間: {avg_ship_hours:.1f}時間")
    if total_items > 0:
        avg_shopee_score = df['shopee_suitability_score'].mean()
        avg_relevance = df['relevance_score'].mean()
        prime_rate = len(df[df['is_prime'] == True]) / total_items * 100
        print(f"   🎯 平均Shopee適性: {avg_shopee_score:.1f}点")
        print(f"   🎯 平均一致度: {avg_relevance:.1f}%")
        print(f"   🎯 Prime率: {prime_rate:.1f}%")
    return df

def calculate_batch_status_shopee_v7(df):
    """
    ShippingTime最優先システム v7 バッチ処理ステータス計算（2グループ版）
    """
    total_items = len(df)
    if total_items == 0:
        return create_empty_status_2groups()
    asin_column = get_asin_column(df)
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
    group_a = len(df[df['shopee_group'] == 'A']) if 'shopee_group' in df.columns else 0
    group_b = len(df[df['shopee_group'] == 'B']) if 'shopee_group' in df.columns else 0
    ship_available = len(df[df['ship_hours'].notna()]) if 'ship_hours' in df.columns else 0
    ship_rate = (ship_available / total_items * 100) if total_items > 0 else 0
    avg_ship_hours = df[df['ship_hours'].notna()]['ship_hours'].mean() if ship_available > 0 else 0
    fast_shipping_count = len(df[df['ship_hours'] <= 24]) if 'ship_hours' in df.columns else 0
    fast_shipping_rate = (fast_shipping_count / total_items * 100) if total_items > 0 else 0
    prime_count = len(df[df.get('is_prime', False)]) if 'is_prime' in df.columns else 0
    return {
        'total': total_items,
        'processed': processed_count,
        'success': success_count,
        'failed': failed_count,
        'success_rate': success_rate,
        'group_a': group_a,
        'group_b': group_b,
        'valid_candidates': total_items,
        'ship_available': ship_available,
        'ship_rate': ship_rate,
        'avg_ship_hours': avg_ship_hours,
        'fast_shipping_count': fast_shipping_count,
        'fast_shipping_rate': fast_shipping_rate,
        'prime_count': prime_count,
        'prime_rate': (prime_count / total_items * 100) if total_items > 0 else 0,
        'progress': (processed_count / total_items * 100) if total_items > 0 else 0
    }

def create_empty_status_2groups():
    """2グループ版空ステータス作成"""
    return {
        'total': 0, 'processed': 0, 'success': 0, 'failed': 0, 'success_rate': 0,
        'group_a': 0, 'group_b': 0, 'valid_candidates': 0,
        'ship_available': 0, 'ship_rate': 0, 'avg_ship_hours': 0,
        'fast_shipping_count': 0, 'fast_shipping_rate': 0,
        'prime_count': 0, 'prime_rate': 0, 'progress': 0
    }

# ======================== ShippingTime v8 高度分析機能 ========================

def analyze_category_shipping_patterns(df):
    """
    カテゴリ別ShippingTime取得パターン分析
    「美容は欠損30%、家電は5%」などの傾向把握
    """
    print("🔍 カテゴリ別ShippingTime取得パターン分析開始...")
    
    category_analysis = {}
    
    # カテゴリカラムの特定
    category_columns = ['main_category', 'amazon_brand', 'seller_type', 'brand']
    available_category = None
    
    for col in category_columns:
        if col in df.columns and df[col].notna().sum() > 0:
            available_category = col
            break
    
    if not available_category:
        print("⚠️ カテゴリ情報が見つかりません")
        return {}
    
    print(f"📊 {available_category}別分析実行中...")
    
    # カテゴリごとの取得率分析
    for category, subset in df.groupby(available_category):
        if pd.notna(category) and len(subset) >= 3:  # 最低3件以上のカテゴリのみ
            analysis = monitor_shipping_time_rate_v8(subset, bucket=str(category))
            category_analysis[str(category)] = analysis
    
    # 取得率ランキング
    if category_analysis:
        sorted_categories = sorted(
            category_analysis.items(), 
            key=lambda x: x[1]['success_rate'], 
            reverse=True
        )
        
        print(f"\n🏆 {available_category}別取得率ランキング:")
        for i, (cat, data) in enumerate(sorted_categories[:10]):
            print(f"   {i+1}. {cat}: {data['success_rate']:.1f}% ({data['with_shipping']}/{data['total']})")
        
        # 要注意カテゴリ（取得率70%未満）
        low_rate_categories = [(cat, data) for cat, data in category_analysis.items() 
                              if data['success_rate'] < 70 and data['total'] >= 5]
        
        if low_rate_categories:
            print(f"\n⚠️ 要注意カテゴリ（取得率<70%）:")
            for cat, data in low_rate_categories:
                print(f"   🔴 {cat}: {data['success_rate']:.1f}% - 改善要検討")
    
    return category_analysis

def monitor_shipping_time_rate_v8(df, bucket="overall"):
    """
    ShippingTime取得率監視 v8 - カテゴリ別ヒートマップ対応
    """
    total = len(df)
    if total == 0:
        print(f"📊 {bucket}: データなし")
        return {}
    
    with_ship = df['ship_hours'].notna().sum() if 'ship_hours' in df.columns else 0
    miss_rate = 100 * (total - with_ship) / total
    success_rate = 100 - miss_rate
    
    # 基本統計
    print(f"📊 {bucket} ShippingTime取得率: {success_rate:.1f}% ({with_ship}/{total})")
    print(f"📊 {bucket} ShippingTime欠損率: {miss_rate:.1f}% ({total - with_ship}/{total})")
    
    # 詳細分析
    analysis = {
        "bucket": bucket,
        "total": total,
        "with_shipping": with_ship,
        "success_rate": success_rate,
        "miss_rate": miss_rate
    }
    
    # フォールバック効果分析
    if 'classification_reason' in df.columns:
        fallback_analysis = df['classification_reason'].value_counts()
        analysis["fallback_effectiveness"] = fallback_analysis.to_dict()
        
        # 主要フォールバック率
        amazon_fallback = fallback_analysis.get("Amazon本体フォールバック", 0)
        fba_fallback = fallback_analysis.get("FBAフォールバック", 0)
        
        print(f"   🏆 Amazon本体フォールバック: {amazon_fallback}件 ({amazon_fallback/total*100:.1f}%)")
        print(f"   📦 FBAフォールバック: {fba_fallback}件 ({fba_fallback/total*100:.1f}%)")
    
    # 発送時間分布（取得できた商品のみ）
    if 'ship_hours' in df.columns and with_ship > 0:
        valid_hours = df[df['ship_hours'].notna()]['ship_hours']
        fast_shipping = len(valid_hours[valid_hours <= 24])
        medium_shipping = len(valid_hours[(valid_hours > 24) & (valid_hours <= 48)])
        slow_shipping = len(valid_hours[valid_hours > 48])
        
        print(f"   ⚡ 24時間以内: {fast_shipping}件 ({fast_shipping/with_ship*100:.1f}%)")
        print(f"   🟡 25-48時間: {medium_shipping}件 ({medium_shipping/with_ship*100:.1f}%)")
        print(f"   🔴 48時間超: {slow_shipping}件 ({slow_shipping/with_ship*100:.1f}%)")
        
        analysis["shipping_distribution"] = {
            "fast_24h": fast_shipping,
            "medium_48h": medium_shipping,
            "slow_48h_plus": slow_shipping,
            "avg_hours": valid_hours.mean(),
            "median_hours": valid_hours.median()
        }
    
    return analysis

def track_missing_asins(df):
    """
    欠損ASIN追跡フラグ機能
    「なぜ欠損したか」を後で分析用
    """
    print("🔍 ShippingTime欠損ASIN追跡分析開始...")
    
    if 'ship_hours' not in df.columns:
        print("⚠️ ship_hoursカラムが見つかりません")
        return df
    
    # 欠損フラグ追加
    df['shipping_missing'] = df['ship_hours'].isna()
    missing_count = df['shipping_missing'].sum()
    total_count = len(df)
    
    print(f"📊 ShippingTime欠損: {missing_count}/{total_count}件 ({missing_count/total_count*100:.1f}%)")
    
    # 欠損理由の分類
    missing_reasons = []
    
    for idx, row in df[df['shipping_missing']].iterrows():
        if row.get('api_source') == 'fallback':
            reason = "API呼び出し失敗"
        elif row.get('seller_type') == 'third_party':
            reason = "サードパーティ出品者"
        elif not row.get('is_prime', False):
            reason = "非Prime商品"
        elif row.get('classification_reason', '').startswith('最終'):
            reason = "全フォールバック失敗"
        else:
            reason = "不明"
        
        missing_reasons.append(reason)
    
    # 欠損理由統計
    if missing_reasons:
        from collections import Counter
        reason_counts = Counter(missing_reasons)
        
        print(f"📋 欠損理由別統計:")
        for reason, count in reason_counts.most_common():
            print(f"   📌 {reason}: {count}件 ({count/missing_count*100:.1f}%)")
        
        # 欠損理由をデータフレームに追加
        df.loc[df['shipping_missing'], 'missing_reason'] = missing_reasons
    
    return df

def generate_improvement_roadmap(analysis_results):
    """
    段階的精度向上ロードマップ生成
    Phase1〜4の改善提案
    """
    print("🗺️ ShippingTime改善ロードマップ生成中...")
    
    overall_rate = analysis_results.get('success_rate', 0)
    
    roadmap = {
        "current_status": f"ShippingTime取得率: {overall_rate:.1f}%",
        "phases": []
    }
    
    # Phase 1: 基盤完成（現在）
    phase1 = {
        "phase": "Phase 1 - 基盤完成",
        "status": "✅ 完了" if overall_rate >= 60 else "🔄 進行中",
        "targets": [
            "ShippingTime + Prime fallback",
            "バッチAPI活用",
            "Amazon本体/FBA優先判定"
        ],
        "expected_rate": "60-70%"
    }
    roadmap["phases"].append(phase1)
    
    # Phase 2: カテゴリ別最適化
    phase2 = {
        "phase": "Phase 2 - カテゴリ別最適化",
        "status": "📋 計画中",
        "targets": [
            "カテゴリ別しきい値調整",
            "ヘルスケア: 36h許容",
            "家電: 24h厳格",
            "低取得率カテゴリ重点改善"
        ],
        "expected_rate": "70-80%",
        "implementation": [
            "カテゴリ別監視強化",
            "しきい値動的調整",
            "カテゴリ別フォールバック戦略"
        ]
    }
    roadmap["phases"].append(phase2)
    
    # Phase 3: ML予測導入
    phase3 = {
        "phase": "Phase 3 - ML予測導入", 
        "status": "🔬 研究段階",
        "targets": [
            "LightGBM/XGBoostによる欠損予測",
            "ブランド・価格・レビュー数から発送時間推定",
            "予測精度80%以上"
        ],
        "expected_rate": "80-90%",
        "features": [
            "商品価格", "レビュー数", "ブランド", 
            "出品者履歴", "カテゴリ", "季節性"
        ]
    }
    roadmap["phases"].append(phase3)
    
    # Phase 4: 利益最大化最適化
    phase4 = {
        "phase": "Phase 4 - 利益最大化最適化",
        "status": "🚀 将来計画",
        "targets": [
            "需要予測 × 発送リスク最適化",
            "利益最大化を目的関数とした選択",
            "リアルタイム動的調整"
        ],
        "expected_rate": "90%+",
        "optimization": [
            "売上寄与度重み付け",
            "在庫回転率考慮",
            "競合分析統合"
        ]
    }
    roadmap["phases"].append(phase4)
    
    # 現在推奨するアクション
    if overall_rate < 70:
        roadmap["immediate_actions"] = [
            "🔧 バッチAPI利用率向上",
            "⚠️ リトライ間隔最適化",
            "📊 カテゴリ別分析実施"
        ]
    elif overall_rate < 80:
        roadmap["immediate_actions"] = [
            "✅ Phase2着手: カテゴリ別しきい値",
            "📈 低取得率カテゴリ重点改善",
            "🎯 ML予測準備"
        ]
    else:
        roadmap["immediate_actions"] = [
            "🎉 高取得率達成",
            "🔬 ML予測研究開始",
            "📊 利益最大化分析準備"
        ]
    
    # ロードマップ表示
    print(f"\n📊 現在ステータス: {roadmap['current_status']}")
    for phase in roadmap["phases"]:
        print(f"\n{phase['status']} {phase['phase']}")
        print(f"   目標取得率: {phase['expected_rate']}")
        for target in phase['targets']:
            print(f"   • {target}")
    
    print(f"\n🎯 即座実行推奨:")
    for action in roadmap["immediate_actions"]:
        print(f"   {action}")
    
    return roadmap

# 既存のmonitor_shipping_time_rate関数をv8版で置き換え
monitor_shipping_time_rate = monitor_shipping_time_rate_v8

def export_shopee_optimized_excel(df):
    """
    Shopee出品最適化Excel出力（2グループ版）
    グループA: 即座出品可能
    グループB: 在庫管理制御
    """
    import io
    
    excel_buffer = io.BytesIO()
    
    # 2グループ別に分類
    groups = {
        'A': df[df['shopee_group'] == 'A'] if 'shopee_group' in df.columns else pd.DataFrame(),
        'B': df[df['shopee_group'] == 'B'] if 'shopee_group' in df.columns else pd.DataFrame()
    }
    
    # 分類カラムがない場合の緊急フォールバック
    if 'shopee_group' not in df.columns:
        print("⚠️ shopee_groupカラムなし - 全商品をグループBに設定")
        groups['A'] = pd.DataFrame()
        groups['B'] = df.copy()
    
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        # サマリーシート
        create_shopee_summary_sheet_2groups(writer, df, groups)
        
        # 2グループ別シート
        sheet_configs = [
            ('A', '🏆_即座出品_24h以内', '24時間以内発送 - DTS規約クリア確実'),
            ('B', '📦_在庫管理制御_それ以外', 'Aの条件外は全部ここ（在庫管理で制御）')
        ]
        
        for group_key, sheet_name, description in sheet_configs:
            group_df = groups[group_key]
            if len(group_df) > 0:
                create_shopee_group_sheet_v2(writer, group_df, sheet_name, description)
        
        # 統計シート
        create_shopee_stats_sheet_2groups(writer, df)
    
    excel_buffer.seek(0)
    return excel_buffer

def create_shopee_summary_sheet_2groups(writer, df, groups):
    """2グループ版サマリーシート作成"""
    summary_data = []
    
    for group_key in ['A', 'B']:
        group_df = groups[group_key]
        count = len(group_df)
        
        if count > 0:
            avg_shopee_score = group_df.get('shopee_suitability_score', pd.Series([0])).mean()
            avg_relevance = group_df.get('relevance_score', pd.Series([0])).mean()
            prime_rate = (len(group_df[group_df.get('is_prime', False)]) / count * 100) if count > 0 else 0
            
            # ShippingTime統計
            if 'ship_hours' in group_df.columns:
                ship_available = len(group_df[group_df['ship_hours'].notna()])
                avg_ship_hours = group_df[group_df['ship_hours'].notna()]['ship_hours'].mean() if ship_available > 0 else 0
            else:
                ship_available = 0
                avg_ship_hours = 0
        else:
            avg_shopee_score = avg_relevance = prime_rate = avg_ship_hours = 0
            ship_available = 0
        
        group_names = {
            'A': '🏆 即座出品可能（24時間以内発送）',
            'B': '📦 在庫管理制御（それ以外）'
        }
        
        summary_data.append({
            'グループ': group_names[group_key],
            '件数': count,
            '割合': f"{count/len(df)*100:.1f}%" if len(df) > 0 else "0%",
            'Shopee適性': f"{avg_shopee_score:.1f}点",
            '一致度': f"{avg_relevance:.1f}%",
            'Prime率': f"{prime_rate:.1f}%",
            'ShippingTime取得': f"{ship_available}件",
            '平均発送時間': f"{avg_ship_hours:.1f}h" if avg_ship_hours > 0 else "N/A"
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_excel(writer, sheet_name='📊_Shopee出品サマリー_v8', index=False)

def create_shopee_group_sheet_v2(writer, group_df, sheet_name, description):
    """Shopeeグループ別シート作成 v2（2グループ対応）"""
    # 必要カラムのみ抽出・整理
    output_columns = [
        'asin', 'amazon_asin', 'amazon_title', 'japanese_name', 
        'shopee_suitability_score', 'relevance_score',
        'ship_hours', 'ship_bucket',  # ShippingTime情報追加
        'is_prime', 'seller_name', 'seller_type',
        'amazon_brand', 'llm_source'
    ]
    
    # 存在するカラムのみ選択
    available_columns = [col for col in output_columns if col in group_df.columns]
    
    if available_columns:
        output_df = group_df[available_columns].copy()
        
        # 説明行を追加
        description_row = pd.DataFrame([[ '=' * 50, description, '=' * 50 ] + [''] * (len(available_columns) - 3)], 
                                      columns=available_columns)
        
        # 説明＋データを結合
        final_df = pd.concat([description_row, output_df], ignore_index=True)
        final_df.to_excel(writer, sheet_name=sheet_name, index=False)

def create_shopee_stats_sheet_2groups(writer, df):
    """2グループ版統計シート作成"""
    stats_data = []
    
    # 基本統計
    total = len(df)
    success = len(df[df.get('search_status') == 'success']) if 'search_status' in df.columns else len(df[df.get('asin', '') != ''])
    
    stats_data.extend([
        ['=== ShippingTime最優先システム v8 統計 ===', ''],
        ['基本統計', ''],
        ['総商品数', total],
        ['ASIN取得成功', success],
        ['成功率', f"{success/total*100:.1f}%" if total > 0 else "0%"],
        ['', ''],
    ])
    
    # 2グループ統計
    if 'shopee_group' in df.columns:
        group_counts = df['shopee_group'].value_counts()
        stats_data.extend([
            ['グループ統計（2グループ版）', ''],
            ['グループA（即座出品）', group_counts.get('A', 0)],
            ['グループB（在庫管理制御）', group_counts.get('B', 0)],
            ['', '']
        ])
    
    # ShippingTime統計
    if 'ship_hours' in df.columns:
        ship_available = len(df[df['ship_hours'].notna()])
        ship_rate = (ship_available / total * 100) if total > 0 else 0
        avg_ship_hours = df[df['ship_hours'].notna()]['ship_hours'].mean() if ship_available > 0 else 0
        fast_shipping = len(df[df['ship_hours'] <= 24]) if ship_available > 0 else 0
        
        stats_data.extend([
            ['ShippingTime統計', ''],
            ['ShippingTime取得数', ship_available],
            ['取得率', f"{ship_rate:.1f}%"],
            ['平均発送時間', f"{avg_ship_hours:.1f}時間"],
            ['24時間以内発送', f"{fast_shipping}件"],
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
        ])
    
    stats_df = pd.DataFrame(stats_data, columns=['項目', '値'])
    stats_df.to_excel(writer, sheet_name='📈_詳細統計_v8', index=False)

# ======================== 分析・診断機能（2グループ版） ========================

def analyze_classification_quality(df):
    """
    分類品質の分析レポート生成（2グループ版）
    
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
    
    # ShippingTime統計
    shipping_stats = {}
    if has_shopee_classification and 'ship_hours' in df.columns:
        ship_available = len(df[df['ship_hours'].notna()])
        shipping_stats['ship_rate'] = (ship_available / total) * 100 if total > 0 else 0
        shipping_stats['avg_ship_hours'] = df[df['ship_hours'].notna()]['ship_hours'].mean() if ship_available > 0 else 0
        shipping_stats['fast_shipping_count'] = len(df[df['ship_hours'] <= 24]) if ship_available > 0 else 0
        
        if 'shopee_suitability_score' in df.columns:
            shipping_stats['avg_shopee_score'] = df['shopee_suitability_score'].mean()
        
        if 'is_prime' in df.columns:
            shipping_stats['prime_rate'] = (len(df[df['is_prime']]) / total) * 100
        
        if 'seller_type' in df.columns:
            shipping_stats['seller_distribution'] = df['seller_type'].value_counts().to_dict()
    
    return {
        "classification_type": "ShippingTime最優先（2グループ版）" if has_shopee_classification else "従来型",
        "total_items": total,
        "group_distribution": group_counts.to_dict(),
        "group_percentages": {group: (count / total) * 100 for group, count in group_counts.items()},
        "relevance_stats": relevance_stats.to_dict() if len(relevance_stats) > 0 else {},
        "asin_success_rates": asin_rates,
        "shipping_stats": shipping_stats,
        "quality_score": calculate_quality_score_2groups(df, group_column)
    }

def calculate_quality_score_2groups(df, group_column):
    """
    2グループ版分類品質スコアの計算
    """
    if len(df) == 0:
        return 0
    
    if group_column == 'shopee_group':
        # ShippingTime最優先品質スコア（2グループ版）
        group_a_count = len(df[df[group_column] == 'A'])
        
        # ShippingTime取得率
        ship_available = len(df[df['ship_hours'].notna()]) if 'ship_hours' in df.columns else 0
        ship_rate = (ship_available / len(df)) if len(df) > 0 else 0
        
        # 24時間以内発送の精度
        fast_shipping_accuracy = 1.0
        if ship_available > 0:
            group_a_with_ship = df[(df[group_column] == 'A') & (df['ship_hours'].notna())]
            if len(group_a_with_ship) > 0:
                fast_accurate = len(group_a_with_ship[group_a_with_ship['ship_hours'] <= 24])
                fast_shipping_accuracy = fast_accurate / len(group_a_with_ship)
        
        # 2グループバランス
        group_balance = 1 - abs(0.3 - (group_a_count / len(df)))  # 理想は30%程度がグループA
        
        # 総合品質スコア
        quality_score = (ship_rate * 0.4 + fast_shipping_accuracy * 0.4 + group_balance * 0.2) * 100
    else:
        # 従来品質スコア
        group_a_count = len(df[df[group_column] == 'A'])
        high_relevance_count = len(df[df['relevance_score'] >= 70])
        
        # グループAの精度
        precision_a = (group_a_count / high_relevance_count) if high_relevance_count > 0 else 0
        
        # 全体的なバランス
        group_balance = 1 - abs(0.3 - (group_a_count / len(df)))
        
        # 総合品質スコア
        quality_score = (precision_a * 0.7 + group_balance * 0.3) * 100
    
    return min(quality_score, 100)

# ======================== 個別承認システム機能（2グループ版） ========================

def initialize_approval_system(df):
    """
    承認システムの初期化（2グループ版）
    
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
                'ship_hours': row.get('ship_hours'),
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
    アイテムを却下
    
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
    承認状態をデータフレームに適用（2グループ版）
    """
    df_updated = df.copy()
    
    # 承認されたアイテムをグループAに昇格
    for approved_item in approval_state['approved_items']:
        item_index = approved_item['index']
        if item_index in df_updated.index:
            df_updated.at[item_index, 'shopee_group'] = 'A'
            df_updated.at[item_index, 'approval_status'] = 'approved'
    
    # 却下されたアイテムは除外（2グループ版では削除）
    for rejected_item in approval_state['rejected_items']:
        item_index = rejected_item['index']
        if item_index in df_updated.index:
            df_updated.at[item_index, 'approval_status'] = 'rejected'
    
    print(f"📊 承認状態適用完了: {len(approval_state['approved_items'])}件承認, {len(approval_state['rejected_items'])}件却下")
    return df_updated

def get_approval_statistics(approval_state):
    """
    承認システムの統計情報取得
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
        
        filtered_items.append(item)
    
    return filtered_items

def export_approval_report(approval_state):
    """
    承認レポートのエクスポート
    """
    report_data = []
    
    # 承認済みアイテム
    for item in approval_state['approved_items']:
        report_data.append({
            'ステータス': '承認済み',
            'ASIN': item['asin'],
            '商品名': item['title'],
            'Shopee適性': item['shopee_score'],
            '一致度': item['relevance_score'],
            '発送時間': item.get('ship_hours', 'N/A'),
            '承認理由': item.get('approval_reason', ''),
            '承認日時': item.get('approval_date', '')
        })
    
    # 却下アイテム
    for item in approval_state['rejected_items']:
        report_data.append({
            'ステータス': '却下',
            'ASIN': item['asin'],
            '商品名': item['title'],
            'Shopee適性': item['shopee_score'],
            '一致度': item['relevance_score'],
            '発送時間': item.get('ship_hours', 'N/A'),
            '承認理由': item.get('rejection_reason', ''),
            '承認日時': item.get('rejection_date', '')
        })
    
    # 承認待ちアイテム
    for item in approval_state['pending_items']:
        report_data.append({
            'ステータス': '承認待ち',
            'ASIN': item['asin'],
            '商品名': item['title'],
            'Shopee適性': item['shopee_score'],
            '一致度': item['relevance_score'],
            '発送時間': item.get('ship_hours', 'N/A'),
            '承認理由': '',
            '承認日時': ''
        })
    
    report_df = pd.DataFrame(report_data)
    return report_df

def suggest_auto_approval_candidates(approval_state, criteria=None):
    """
    自動承認候補の提案
    """
    if criteria is None:
        # 2グループ版デフォルト基準
        criteria = {
            'min_shopee_score': 75,
            'min_relevance_score': 60,
            'max_ship_hours': 24  # ShippingTime基準追加
        }
    
    candidates = []
    
    for item in approval_state['pending_items']:
        # 基準チェック
        meets_criteria = True
        reasons = []
        
        # Shopee適性スコア
        if item.get('shopee_score', 0) >= criteria.get('min_shopee_score', 75):
            reasons.append(f"高Shopee適性({item.get('shopee_score', 0)}点)")
        else:
            meets_criteria = False
        
        # 一致度
        if item.get('relevance_score', 0) >= criteria.get('min_relevance_score', 60):
            reasons.append(f"高一致度({item.get('relevance_score', 0)}%)")
        else:
            meets_criteria = False
        
        # ShippingTime基準（v8新機能）
        ship_hours = item.get('ship_hours')
        if ship_hours is not None and ship_hours <= criteria.get('max_ship_hours', 24):
            reasons.append(f"高速発送({ship_hours}時間)")
        elif ship_hours is None and item.get('is_prime', False):
            reasons.append("Prime商品（発送時間不明）")
        else:
            meets_criteria = False
        
        if meets_criteria:
            candidate = item.copy()
            candidate['auto_approval_reasons'] = reasons
            candidates.append(candidate)
    
    print(f"🤖 自動承認候補: {len(candidates)}件")
    return candidates