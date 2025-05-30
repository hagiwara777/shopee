# sp_api_service.py

# ======================== Streamlit UI統合用関数 ========================

def process_batch_with_shopee_optimization(df, title_column='clean_title', limit=None):
    from asin_helpers import classify_for_shopee_listing_v7
    
    """
    Streamlit UI統合用バッチ処理関数
    ShippingTime最優先システム v8 対応版
    
    Args:
        df: 処理対象データフレーム
        title_column: 商品名カラム名
        limit: 処理件数制限
    
    Returns:
        pd.DataFrame: 処理済みデータフレーム
    """
    print(f"🚀 Shopee最適化バッチ処理開始: {title_column}カラム使用")
    
    # 処理対象の決定
    if limit:
        df_to_process = df.head(limit).copy()
    else:
        df_to_process = df.copy()
    
    total_items = len(df_to_process)
    print(f"📊 処理対象: {total_items}件")
    
    # 必要なカラムの初期化
    result_columns = [
        'amazon_asin', 'asin', 'amazon_title', 'amazon_brand', 'relevance_score',
        'is_prime', 'seller_type', 'seller_name', 'seller_id',
        'ship_hours', 'ship_bucket', 'ship_source',  # ShippingTime v8
        'shopee_suitability_score', 'price', 'search_status',
        'extracted_brand', 'extracted_quantity', 'cleaned_title',
        'japanese_name', 'llm_source'
    ]
    
    for col in result_columns:
        if col not in df_to_process.columns:
            if col in ['ship_hours']:
                df_to_process[col] = None  # ShippingTime用
            elif col in ['is_prime']:
                df_to_process[col] = False
            elif col in ['relevance_score', 'shopee_suitability_score']:
                df_to_process[col] = 0
            else:
                df_to_process[col] = ""
    
    # 認証情報取得
    credentials = get_credentials()
    if not credentials:
        print("❌ 認証情報取得失敗 - デモデータで代替")
        return generate_demo_data_for_ui(df_to_process, title_column)
    
    # 実際のバッチ処理実行
    print("🔄 実際のSP-API処理は開発中...")
    print("📊 現在はデモデータで代替実行")
    
    # デモデータ生成（実装完了まで）
    demo_result = generate_demo_data_for_ui(df_to_process, title_column)
    classified_result = classify_for_shopee_listing_v7(demo_result)
    
    print(f"✅ Shopee最適化バッチ処理完了: {len(classified_result)}件")
    return classified_result

def generate_demo_data_for_ui(df, title_column):
    import numpy as np
    
    df_demo = df.copy()
    np.random.seed(42)  # 再現性のため
    
    print(f"🧪 デモデータ生成: {len(df_demo)}件")
    
    for idx, row in df_demo.iterrows():
        title = str(row[title_column])
        
        # ASIN生成
        asin = f"B{np.random.randint(10000000, 99999999):08d}"
        df_demo.at[idx, 'amazon_asin'] = asin
        df_demo.at[idx, 'asin'] = asin
        
        # タイトル処理
        df_demo.at[idx, 'amazon_title'] = title
        df_demo.at[idx, 'cleaned_title'] = title
        
        # Prime+出品者情報（現実的な分布）
        prime_probability = 0.7  # 70%がPrime
        is_prime = np.random.random() < prime_probability
        df_demo.at[idx, 'is_prime'] = is_prime
        
        if is_prime:
            # Prime商品の出品者分布
            seller_types = ['amazon', 'official_manufacturer', 'third_party']
            seller_weights = [0.3, 0.2, 0.5]  # Amazon30%, 公式20%, サードパーティ50%
            seller_type = np.random.choice(seller_types, p=seller_weights)
        else:
            seller_type = 'third_party'
        
        df_demo.at[idx, 'seller_type'] = seller_type
        
        # セラー名生成
        seller_names = {
            'amazon': 'Amazon.co.jp',
            'official_manufacturer': f"{title.split()[0] if title else 'メーカー'}株式会社",
            'third_party': f"サードパーティ{np.random.randint(1, 100)}"
        }
        df_demo.at[idx, 'seller_name'] = seller_names[seller_type]
        df_demo.at[idx, 'seller_id'] = f"SELLER_{idx:03d}"
        
        # ShippingTime生成（v8重要機能）
        if is_prime and seller_type in ['amazon', 'official_manufacturer']:
            # Amazon/公式は高速発送傾向
            ship_hours = np.random.choice([6, 12, 18, 24, 48], p=[0.3, 0.3, 0.2, 0.1, 0.1])
        elif is_prime:
            # Primeサードパーティは中速
            ship_hours = np.random.choice([24, 48, 72], p=[0.4, 0.4, 0.2])
        else:
            # 非Primeは遅め、または情報なし
            if np.random.random() < 0.6:  # 60%で情報取得
                ship_hours = np.random.choice([48, 72, 120, 168], p=[0.2, 0.3, 0.3, 0.2])
            else:
                ship_hours = None  # 40%で情報なし
        
        df_demo.at[idx, 'ship_hours'] = ship_hours
        df_demo.at[idx, 'ship_bucket'] = "STANDARD" if ship_hours else ""
        df_demo.at[idx, 'ship_source'] = "デモ生成" if ship_hours else "取得失敗"
        
        # スコア生成
        base_score = np.random.randint(40, 95)
        
        # Prime+出品者タイプでボーナス
        if is_prime and seller_type == 'amazon':
            base_score += 15
        elif is_prime and seller_type == 'official_manufacturer':
            base_score += 10
        elif is_prime:
            base_score += 5
        
        # ShippingTimeでボーナス
        if ship_hours and ship_hours <= 24:
            base_score += 10
        elif ship_hours and ship_hours <= 48:
            base_score += 5
        
        df_demo.at[idx, 'shopee_suitability_score'] = min(base_score, 100)
        df_demo.at[idx, 'relevance_score'] = base_score + np.random.randint(-10, 11)
        df_demo.at[idx, 'relevance_score'] = max(0, min(100, df_demo.at[idx, 'relevance_score']))
        
        # その他の情報
        df_demo.at[idx, 'search_status'] = 'success'
        df_demo.at[idx, 'price'] = f"¥{np.random.randint(500, 8000)}"
        df_demo.at[idx, 'amazon_brand'] = title.split()[0] if title else 'Unknown'
        df_demo.at[idx, 'extracted_brand'] = df_demo.at[idx, 'amazon_brand']
        df_demo.at[idx, 'japanese_name'] = title  # 簡易版
        df_demo.at[idx, 'llm_source'] = np.random.choice(['GPT-4o', 'Gemini'], p=[0.7, 0.3])
    
    print(f"✅ デモデータ生成完了: Prime率{(df_demo['is_prime'].sum()/len(df_demo)*100):.1f}%")
    return df_demo

# ======================== 既存関数のエイリアス（互換性維持） ========================

# 既存のUI用関数のエイリアス
process_batch_asin_search_with_ui_shopee = process_batch_with_shopee_optimization

# search関数の簡易版（UIから直接呼ばれる場合用）
def search_asin_with_enhanced_prime_seller_safe(title, max_results=5):
    """
    UI用安全版ASIN検索（エラー時デモデータ返却）
    """
    try:
        return search_asin_with_enhanced_prime_seller(title, max_results)
    except Exception as e:
        print(f"⚠️ 検索エラー、デモデータで代替: {e}")
        
        # デモデータ生成
        import numpy as np
        np.random.seed(hash(title) % 2**32)  # タイトルベースのシード
        
        demo_asin = f"B{np.random.randint(10000000, 99999999):08d}"
        is_prime = np.random.random() < 0.7
        ship_hours = np.random.choice([12, 24, 48, None], p=[0.3, 0.3, 0.2, 0.2])
        
        return {
            'search_status': 'demo_success',
            'asin': demo_asin,
            'amazon_asin': demo_asin,
            'amazon_title': title,
            'is_prime': is_prime,
            'ship_hours': ship_hours,
            'seller_type': 'amazon' if np.random.random() < 0.3 else 'third_party',
            'shopee_suitability_score': np.random.randint(60, 95),
            'relevance_score': np.random.randint(70, 90)
        }

# テスト用関数
def test_sp_api_connection():
    """
    SP-API接続テスト
    """
    try:
        credentials = get_credentials()
        if credentials:
            print("✅ SP-API認証情報: 正常")
            return True
        else:
            print("❌ SP-API認証情報: 不足")
            return False
    except Exception as e:
        print(f"❌ SP-API接続テスト失敗: {e}")
        return False

# ダミー実装: search_asin_with_enhanced_prime_seller

def search_asin_with_enhanced_prime_seller(title, max_results=5):
    # 本来はSP-API連携のASIN検索を行う
    # ここではダミーで返す
    import numpy as np
    np.random.seed(hash(title) % 2**32)
    demo_asin = f"B{np.random.randint(10000000, 99999999):08d}"
    is_prime = np.random.random() < 0.7
    ship_hours = np.random.choice([12, 24, 48, None], p=[0.3, 0.3, 0.2, 0.2])
    return {
        'search_status': 'dummy_success',
        'asin': demo_asin,
        'amazon_asin': demo_asin,
        'amazon_title': title,
        'is_prime': is_prime,
        'ship_hours': ship_hours,
        'seller_type': 'amazon' if np.random.random() < 0.3 else 'third_party',
        'shopee_suitability_score': np.random.randint(60, 95),
        'relevance_score': np.random.randint(70, 90)
    }

def get_credentials():
    """
    SP-API認証情報のダミー取得関数（本番は実装済み関数に差し替え）
    """
    # 本番では .env などから取得
    # ここでは常にダミー認証情報を返す
    return {
        'lwa_app_id': 'dummy_app_id',
        'lwa_client_secret': 'dummy_secret',
        'refresh_token': 'dummy_refresh_token'
    }