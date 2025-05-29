# test_step4.py - Step 4統合テスト用ファイル

import time
import json

# import文（ディレクトリ構造に合わせて調整）
try:
    from asin_processor.sp_api_service import (
        search_asin_with_enhanced_prime_seller,
        get_prime_and_seller_info, 
        get_credentials,
        load_brand_dict,
        extract_brand_and_quantity
    )
    print("✅ Step 4: インポート成功")
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    print("🔧 確認事項:")
    print("1. Step 4の修正がsp_api_service.pyに適用されているか")
    print("2. 必要な関数が全て定義されているか")
    exit(1)

def test_step4_brand_extraction():
    """
    Step 4: ブランド名抽出テスト
    """
    print("🧪 Step 4-1: ブランド名抽出テスト")
    
    test_titles = [
        "FANCL mild cleansing oil 120ml",
        "MILBON elujuda hair treatment",
        "Shiseido Senka Perfect Whip",
        "DHC Deep Cleansing Oil",
        "Cezanne Bright Colorcealer 10 Clear Blue"
    ]
    
    try:
        brand_dict = load_brand_dict()
        print(f"   📚 ブランド辞書読み込み: {len(brand_dict)}ブランド")
        
        for title in test_titles:
            try:
                extracted_info = extract_brand_and_quantity(title, brand_dict)
                brand_name = extracted_info.get('brand', '')
                
                print(f"   📋 '{title[:30]}...' → ブランド: '{brand_name}'")
                
            except Exception as e:
                print(f"   ❌ ブランド抽出エラー: {title[:30]}... → {str(e)}")
    
    except Exception as e:
        print(f"   ❌ ブランド辞書読み込みエラー: {str(e)}")
    
    print("   📊 ブランド名抽出テスト完了\n")

def test_step4_api_integration():
    """
    Step 4: SP-API統合テスト（実際のAPI呼び出し）
    """
    print("🧪 Step 4-2: SP-API統合テスト")
    
    # 認証情報確認
    credentials = get_credentials()
    if not credentials:
        print("   ❌ 認証情報が取得できません")
        print("   🔧 .envファイルの設定を確認してください")
        return False
    
    print("   ✅ 認証情報取得成功")
    
    # テストケース（実際の商品タイトル）
    test_cases = [
        {
            'title': 'FANCL mild cleansing oil',
            'expected_brand': 'FANCL',
            'expected_category': 'A',  # Prime + Amazon/公式期待
            'description': 'ファンケル商品（公式メーカー期待）'
        },
        {
            'title': 'MILBON elujuda hair treatment',
            'expected_brand': 'MILBON',
            'expected_category': 'A',  # Prime + 公式期待
            'description': 'ミルボン商品（公式メーカー期待）'
        },
        {
            'title': 'Cezanne Bright Colorcealer',
            'expected_brand': 'Cezanne',
            'expected_category': 'B',  # Prime + サードパーティ期待
            'description': 'セザンヌ商品（サードパーティ期待）'
        }
    ]
    
    results = []
    
    print(f"\n   🔬 統合検索テスト実行:")
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n   --- テスト {i}: {case['description']} ---")
        print(f"   タイトル: {case['title']}")
        
        try:
            # Step 4で修正された統合検索を実行
            start_time = time.time()
            result = search_asin_with_enhanced_prime_seller(case['title'])
            end_time = time.time()
            
            if result.get('search_status') == 'success':
                # 結果分析
                asin = result.get('asin', 'N/A')
                category = result.get('category', 'Unknown')
                is_prime = result.get('is_prime', False)
                is_amazon = result.get('is_amazon_seller', False)
                is_official = result.get('is_official_seller', False)
                brand_name = result.get('brand_name', '')
                seller_name = result.get('seller_name', 'Unknown')
                api_source = result.get('api_source', 'Unknown')
                
                # 期待結果との比較
                category_match = (category == case['expected_category'])
                brand_match = (brand_name == case['expected_brand']) if case['expected_brand'] else True
                
                # 結果表示
                category_status = "✅" if category_match else "❌"
                brand_status = "✅" if brand_match else "⚠️"
                
                print(f"   📊 結果 ({end_time - start_time:.1f}秒):")
                print(f"      ASIN: {asin}")
                print(f"      {category_status} 分類: {category} (期待: {case['expected_category']})")
                print(f"      {brand_status} ブランド: '{brand_name}' (期待: '{case['expected_brand']}')")
                print(f"      Prime判定: {is_prime}")
                print(f"      Amazon本体: {is_amazon}")
                print(f"      公式メーカー: {is_official}")
                print(f"      出品者: {seller_name}")
                print(f"      API使用: {api_source}")
                
                # Amazon商品ページURL
                amazon_url = f"https://www.amazon.co.jp/dp/{asin}"
                print(f"      🔗 手動確認URL: {amazon_url}")
                
                results.append({
                    'title': case['title'],
                    'asin': asin,
                    'category': category,
                    'category_match': category_match,
                    'brand_match': brand_match,
                    'is_prime': is_prime,
                    'api_source': api_source,
                    'success': True,
                    'processing_time': end_time - start_time
                })
                
            else:
                print(f"   ❌ 検索失敗: {result.get('error_message', 'Unknown error')}")
                results.append({
                    'title': case['title'],
                    'success': False,
                    'error': result.get('error_message', 'Unknown error')
                })
            
        except Exception as e:
            print(f"   ❌ テストエラー: {str(e)}")
            results.append({
                'title': case['title'],
                'success': False,
                'error': str(e)
            })
        
        # API制限対策（重要）
        if i < len(test_cases):
            print(f"   ⏱️ API制限対策: 2秒休憩...")
            time.sleep(2)
    
    # 統計結果
    success_count = sum(1 for r in results if r.get('success', False))
    category_match_count = sum(1 for r in results if r.get('category_match', False))
    brand_match_count = sum(1 for r in results if r.get('brand_match', False))
    
    print(f"\n   📊 Step 4統合テスト結果:")
    print(f"      検索成功: {success_count}/{len(test_cases)}")
    print(f"      分類精度: {category_match_count}/{success_count} (期待分類と一致)")
    print(f"      ブランド精度: {brand_match_count}/{success_count} (期待ブランドと一致)")
    
    if success_count > 0:
        avg_time = sum(r.get('processing_time', 0) for r in results if r.get('success', False)) / success_count
        print(f"      平均処理時間: {avg_time:.1f}秒")
    
    return results

def test_step4_detailed_analysis():
    """
    Step 4: 詳細分析テスト（特定ASINの深掘り）
    """
    print("🧪 Step 4-3: 詳細分析テスト")
    
    credentials = get_credentials()
    if not credentials:
        print("   ❌ 認証情報が取得できません")
        return
    
    # 問題のあったASINでの詳細確認
    test_asin = 'B0DR952N7X'  # 以前問題があった商品
    brand_name = 'Cezanne'
    
    print(f"   🔍 詳細分析対象: {test_asin} (ブランド: {brand_name})")
    
    try:
        # Step 4で修正されたget_prime_and_seller_info関数を直接呼び出し
        result = get_prime_and_seller_info(test_asin, credentials, brand_name)
        
        print(f"\n   📋 詳細結果:")
        result_display = {
            'ASIN': result.get('asin'),
            'Prime判定': result.get('is_prime'),
            '出品者ID': result.get('seller_id'),
            '出品者名': result.get('seller_name'),
            'Amazon本体': result.get('is_amazon_seller'),
            '公式メーカー': result.get('is_official_seller'),
            '最終分類': result.get('category'),
            '分類説明': result.get('category_description'),
            'API使用': result.get('api_source'),
        }
        
        for key, value in result_display.items():
            print(f"      {key}: {value}")
        
        # 手動確認情報
        amazon_url = f"https://www.amazon.co.jp/dp/{test_asin}"
        print(f"\n   🔗 手動確認URL: {amazon_url}")
        print(f"   💡 実際のAmazon商品ページでPrime状況と出品者を確認してください")
        
        # エラーの場合
        if result.get('error_reason'):
            print(f"   ⚠️ エラー理由: {result['error_reason']}")
        
    except Exception as e:
        print(f"   ❌ 詳細分析エラー: {str(e)}")

def main():
    """
    Step 4メインテスト実行
    """
    print("🚀 Step 4: 統合機能テスト開始")
    print("="*50)
    
    # テスト1: ブランド名抽出
    test_step4_brand_extraction()
    
    # テスト2: SP-API統合テスト
    results = test_step4_api_integration()
    
    print("\n" + "="*50)
    
    # テスト3: 詳細分析テスト
    test_step4_detailed_analysis()
    
    print("\n" + "="*50)
    print("🎉 Step 4: 統合機能テスト完了")
    
    # 最終評価
    if results:
        success_count = sum(1 for r in results if r.get('success', False))
        if success_count >= 2:
            print("✅ Step 4合格: Step 5に進む準備完了！")
        else:
            print("⚠️ Step 4で問題が検出されました。結果を確認してください。")
    
    print("🔄 次のステップ: Step 5 (asin_helpers.py修正) の準備")

if __name__ == "__main__":
    main()