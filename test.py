from asin_processor.sp_api_service import similar, is_official_seller
import jellyfish

# Step 3: 個別関数テストコード
# これをPythonファイルまたはJupyter Notebookで実行してください

def test_step3_individual_functions():
    """
    Step 3で追加した個別関数のテスト
    """
    print("🧪 Step 3: 個別関数テスト開始")
    
    # 1. similar関数（Jaro-Winkler類似度）のテスト
    print("\n📊 1. similar関数テスト:")
    
    test_cases_similarity = [
        ("FANCL", "ファンケル", False),  # 英語⇔日本語：低類似度期待
        ("FANCL", "FANCL", True),        # 完全一致：高類似度期待
        ("MILBON", "ミルボン", False),    # 英語⇔日本語：低類似度期待
        ("MILBON", "MILBON株式会社", True),  # 部分一致：高類似度期待
        ("Shiseido", "資生堂", False),    # 英語⇔日本語：低類似度期待
        ("資生堂", "資生堂株式会社", True),   # 日本語類似：高類似度期待
    ]
    
    for brand, seller, expected in test_cases_similarity:
        try:
            result = similar(brand, seller, 0.9)
            score = jellyfish.jaro_winkler_similarity(brand.lower(), seller.lower())
            status = "✅" if result == expected else "❌"
            
            print(f"   {status} '{brand}' vs '{seller}': {result} (スコア: {score:.3f}, 期待: {expected})")
        except Exception as e:
            print(f"   ❌ エラー: {brand} vs {seller} → {str(e)}")
    
    # 2. is_official_seller関数のテスト
    print("\n🏭 2. is_official_seller関数テスト:")
    
    test_cases_official = [
        # (seller_id, seller_name, brand_name, expected, test_type)
        ("A1234567890ABCDE", "テスト出品者", "FANCL", True, "ホワイトリスト"),  # ホワイトリストID
        ("UNKNOWN123", "FANCL", "FANCL", True, "完全一致"),                    # 完全一致
        ("UNKNOWN456", "FANCL株式会社", "FANCL", True, "類似度"),              # 類似度判定
        ("UNKNOWN789", "テスト公式ストア", "テスト", True, "正規表現"),          # 正規表現（公式）
        ("UNKNOWNABC", "TestStore_jp", "Test", True, "正規表現"),             # 正規表現（_jp）
        ("UNKNOWNXYZ", "一般出品者", "FANCL", False, "非該当"),                # 非該当
    ]
    
    for seller_id, seller_name, brand_name, expected, test_type in test_cases_official:
        try:
            result = is_official_seller(seller_id, seller_name, brand_name)
            status = "✅" if result == expected else "❌"
            
            print(f"   {status} {test_type}: {result} (期待: {expected})")
            print(f"      ID: {seller_id}, 出品者: {seller_name}, ブランド: {brand_name}")
        except Exception as e:
            print(f"   ❌ エラー: {test_type} → {str(e)}")
    
    print("\n📊 個別関数テスト完了")

# テスト実行
if __name__ == "__main__":
    test_step3_individual_functions()