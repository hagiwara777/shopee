#!/usr/bin/env python3
"""
GPT提案A対応版：環境変数名をSP_API_プレフィックス付きに統一
"""

import os
import sys
import traceback

def complete_sp_api_test():
    """完全なSP-APIテスト（GPT提案A対応版）"""
    print("🚀 完全版SP-APIテスト開始（GPT提案A対応）")
    
    # GPTの指摘通り：SP_API_プレフィックス付き環境変数を確認
    print("\n🔍 環境変数確認（SP_API_プレフィックス付き）:")
    required_vars = [
        "SP_API_LWA_APP_ID",
        "SP_API_LWA_CLIENT_SECRET", 
        "SP_API_LWA_REFRESH_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: 設定済み")
        else:
            print(f"   ❌ {var}: 未設定")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ 必須環境変数が不足: {', '.join(missing_vars)}")
        print("解決方法: export $(grep -v '^#' .env | xargs)")
        return False
    
    # SP-API呼び出しテスト
    print("\n📞 SP-API呼び出しテスト:")
    try:
        from sp_api.api import Products as ProductPricing
        from sp_api.base import Marketplaces
        
        # GPTの指摘通り：SP_API_プレフィックス付き環境変数から認証情報作成
        credentials = {
            "lwa_app_id": os.getenv("SP_API_LWA_APP_ID"),
            "lwa_client_secret": os.getenv("SP_API_LWA_CLIENT_SECRET"),
            "refresh_token": os.getenv("SP_API_LWA_REFRESH_TOKEN")
        }
        
        # AWS認証情報（存在する場合）
        aws_access_key = os.getenv("SP_API_AWS_ACCESS_KEY")
        aws_secret_key = os.getenv("SP_API_AWS_SECRET_KEY")
        role_arn = os.getenv("SP_API_ROLE_ARN")
        
        if aws_access_key and aws_secret_key:
            credentials.update({
                "aws_access_key": aws_access_key,
                "aws_secret_key": aws_secret_key
            })
        
        if role_arn:
            credentials["role_arn"] = role_arn
        
        pp = ProductPricing(credentials=credentials, marketplace=Marketplaces.JP)
        print("   ✅ ProductPricingインスタンス作成成功")
        
        # GPTの指摘通り：get_item_offersでPrime判定テスト
        test_asin = "B00KOTG7AE"
        print(f"   📞 {test_asin}でget_item_offers呼び出し...")
        
        offers = pp.get_item_offers(test_asin, ItemCondition="New").payload["Offers"]
        
        if offers:
            offer = offers[0]
            prime_info = offer.get("PrimeInformation", {})
            seller_info = offer.get("Seller", {})
            
            print(f"\n🎉 API呼び出し成功（GPTの指摘通り）:")
            print(f"   Prime判定: {prime_info.get('IsPrime', 'N/A')}")
            print(f"   National Prime: {prime_info.get('IsNationalPrime', 'N/A')}")
            print(f"   出品者ID: {seller_info.get('SellerId', 'N/A')}")
            print(f"   出品者名: {seller_info.get('Name', 'N/A')}")
            
            print(f"\n✅ 結論:")
            print(f"   - 環境変数名統一: 完了 ✅")
            print(f"   - get_item_offers: 正常動作 ✅")
            print(f"   - Step 4問題: 解決予定 ✅")
            
            return True
        else:
            print("   ⚠️ オファー情報なし")
            return False
            
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        
        # GPTの指摘通り：エラー分析
        error_str = str(e)
        if "MissingCredentials" in error_str:
            print("   🔧 解決策: 環境変数名をSP_API_プレフィックス付きに統一")
        elif "Unauthorized" in error_str or "403" in error_str:
            print("   🔧 解決策: SP-APIの認証情報を確認")
        elif "429" in error_str:
            print("   🔧 解決策: レート制限、少し待ってから再実行")
        else:
            print(f"   🔧 予期しないエラー: {error_str}")
        
        print("   📊 エラー詳細:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = complete_sp_api_test()
    if success:
        print("\n🚀 Step 4再実行準備完了！")
        print("   次のコマンド: python3 test_step4.py")
    else:
        print("\n🔧 問題を解決してから再実行してください")
