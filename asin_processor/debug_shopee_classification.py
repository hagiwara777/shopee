# debug_shopee_classification.py - Shopee分類デバッグスクリプト
import pandas as pd
import sys
sys.path.append('/workspaces/shopee/asin_processor')

from sp_api_service import search_asin_with_enhanced_prime_seller, test_sp_api_connection
from asin_helpers import classify_for_shopee_listing, generate_demo_data

def debug_single_product(product_name):
    """単一商品の詳細デバッグ"""
    print(f"\n🔍 詳細デバッグ: {product_name}")
    print("=" * 50)
    
    # Prime+出品者情報統合検索実行
    result = search_asin_with_enhanced_prime_seller(product_name)
    
    print(f"📊 検索結果詳細:")
    print(f"   search_status: {result.get('search_status', 'N/A')}")
    print(f"   asin: {result.get('asin', 'N/A')}")
    print(f"   amazon_asin: {result.get('amazon_asin', 'N/A')}")
    print(f"   error_message: {result.get('error_message', 'N/A')}")
    
    if result.get('search_status') == 'success':
        print(f"\n✅ ASIN取得成功:")
        print(f"   商品名: {result.get('amazon_title', 'N/A')[:50]}...")
        print(f"   ブランド: {result.get('amazon_brand', 'N/A')}")
        print(f"   一致度: {result.get('relevance_score', 0)}%")
        
        print(f"\n🏆 Prime+出品者情報:")
        print(f"   is_prime: {result.get('is_prime', 'N/A')}")
        print(f"   seller_name: {result.get('seller_name', 'N/A')}")
        print(f"   seller_type: {result.get('seller_type', 'N/A')}")
        print(f"   is_amazon_seller: {result.get('is_amazon_seller', 'N/A')}")
        print(f"   is_official_seller: {result.get('is_official_seller', 'N/A')}")
        print(f"   prime_status: {result.get('prime_status', 'N/A')}")
        
        print(f"\n🎯 Shopee適性:")
        print(f"   shopee_suitability_score: {result.get('shopee_suitability_score', 0)}点")
        print(f"   shopee_group: {result.get('shopee_group', 'N/A')}")
        
        # グループ分類ロジックの詳細確認
        print(f"\n🔍 分類ロジック確認:")
        asin = result.get('asin') or result.get('amazon_asin')
        has_asin = bool(asin and asin != '')
        is_prime = result.get('is_prime', False)
        seller_type = result.get('seller_type', 'unknown')
        relevance_score = result.get('relevance_score', 0)
        
        print(f"   has_asin: {has_asin} (ASIN: {asin})")
        print(f"   is_prime: {is_prime}")
        print(f"   seller_type: {seller_type}")
        print(f"   relevance_score: {relevance_score}")
        
        # 分類判定
        if not has_asin:
            expected_group = 'X'
            reason = 'ASIN無し'
        elif is_prime and seller_type in ['amazon', 'official_manufacturer']:
            expected_group = 'A'
            reason = 'Prime+Amazon/公式'
        elif is_prime and seller_type == 'third_party':
            expected_group = 'B'
            reason = 'Prime+サードパーティ'
        elif not is_prime and relevance_score >= 40:
            expected_group = 'C'
            reason = '非Prime+中一致度以上'
        else:
            expected_group = 'X'
            reason = '除外条件'
        
        print(f"   期待グループ: {expected_group} ({reason})")
        print(f"   実際グループ: {result.get('shopee_group', 'N/A')}")
        
        if expected_group != result.get('shopee_group'):
            print(f"   ⚠️ グループ不一致！")
        
    else:
        print(f"\n❌ ASIN取得失敗:")
        print(f"   エラー: {result.get('error', 'Unknown')}")
        print(f"   日本語化: {result.get('japanese_name', 'N/A')} ({result.get('llm_source', 'N/A')})")
    
    return result

def debug_batch_results(df):
    """バッチ結果の詳細デバッグ"""
    print(f"\n📊 バッチ結果デバッグ:")
    print("=" * 50)
    
    print(f"総件数: {len(df)}")
    
    # 必要カラムの存在確認
    required_columns = [
        'search_status', 'asin', 'amazon_asin', 'is_prime', 
        'seller_type', 'shopee_group', 'shopee_suitability_score'
    ]
    
    print(f"\n📋 カラム存在確認:")
    for col in required_columns:
        exists = col in df.columns
        print(f"   {col}: {'✅' if exists else '❌'}")
    
    # search_status分布
    if 'search_status' in df.columns:
        print(f"\n🔍 search_status分布:")
        status_counts = df['search_status'].value_counts()
        for status, count in status_counts.items():
            print(f"   {status}: {count}件")
    
    # ASIN取得状況
    asin_column = None
    for col in ['asin', 'amazon_asin']:
        if col in df.columns:
            asin_column = col
            break
    
    if asin_column:
        print(f"\n📍 ASIN取得状況 ({asin_column}):")
        valid_asin = df[df[asin_column].notna() & (df[asin_column] != '')][asin_column]
        print(f"   有効ASIN: {len(valid_asin)}件")
        print(f"   無効ASIN: {len(df) - len(valid_asin)}件")
        
        if len(valid_asin) > 0:
            print(f"   有効ASIN例: {valid_asin.iloc[0]}")
    
    # Prime情報
    if 'is_prime' in df.columns:
        print(f"\n🏆 Prime情報:")
        prime_counts = df['is_prime'].value_counts()
        for status, count in prime_counts.items():
            print(f"   is_prime={status}: {count}件")
    
    # 出品者タイプ
    if 'seller_type' in df.columns:
        print(f"\n🏢 出品者タイプ:")
        seller_counts = df['seller_type'].value_counts()
        for seller_type, count in seller_counts.items():
            print(f"   {seller_type}: {count}件")
    
    # Shopeeグループ
    if 'shopee_group' in df.columns:
        print(f"\n🎯 Shopeeグループ:")
        group_counts = df['shopee_group'].value_counts()
        for group, count in group_counts.items():
            print(f"   グループ{group}: {count}件")
    
    # 個別ケース分析（最初の3件）
    print(f"\n🔍 個別ケース分析（最初の3件）:")
    for idx, row in df.head(3).iterrows():
        print(f"\n   ケース {idx+1}:")
        print(f"      商品名: {row.get('clean_title', 'N/A')[:40]}...")
        print(f"      search_status: {row.get('search_status', 'N/A')}")
        print(f"      asin: {row.get(asin_column, 'N/A') if asin_column else 'N/A'}")
        print(f"      is_prime: {row.get('is_prime', 'N/A')}")
        print(f"      seller_type: {row.get('seller_type', 'N/A')}")
        print(f"      shopee_group: {row.get('shopee_group', 'N/A')}")
        print(f"      shopee_score: {row.get('shopee_suitability_score', 'N/A')}")

def main():
    """メインデバッグ実行"""
    print("🧪 Shopee分類デバッグスクリプト開始")
    print("=" * 60)
    
    # 1. SP-API接続テスト
    print("1. SP-API接続テスト")
    connection_ok = test_sp_api_connection()
    print(f"   結果: {'✅ 正常' if connection_ok else '❌ エラー'}")
    
    if not connection_ok:
        print("❌ SP-API接続に問題があります。環境変数を確認してください。")
        return
    
    # 2. 単一商品テスト
    print(f"\n2. 単一商品詳細テスト")
    test_products = [
        "FANCL mild cleansing oil",
        "MILBON elujuda hair treatment", 
        "ORBIS essence moisturizer"
    ]
    
    for product in test_products:
        debug_single_product(product)
    
    # 3. デモデータでバッチテスト
    print(f"\n3. デモデータバッチテスト")
    demo_data = generate_demo_data(5)
    print(f"デモデータ生成: {len(demo_data)}件")
    
    # デモデータを分類
    classified_demo = classify_for_shopee_listing(demo_data)
    debug_batch_results(classified_demo)
    
    print(f"\n✅ デバッグスクリプト完了")

if __name__ == "__main__":
    main()