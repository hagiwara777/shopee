#!/usr/bin/env python3
"""
GPT提案のテスト：環境変数修正後の動作確認
"""

from sp_api.api import Products as ProductPricing
from sp_api.base import Marketplaces

def test_fixed_sp_api():
    """修正後のSP-API動作確認"""
    print("🧪 GPT提案修正後のSP-APIテスト開始")
    
    try:
        # GPTの提案：環境変数から自動取得（プレフィックス付き）
        pp = ProductPricing(marketplace=Marketplaces.JP)
        print("✅ ProductPricingインスタンス作成成功（環境変数自動認識）")
        
        # GPTの提案テストコード
        test_asin = "B00KOTG7AE"
        print(f"📞 {test_asin}でget_item_offers呼び出し...")
        
        offers = pp.get_item_offers(test_asin, ItemCondition="New").payload["Offers"]
        
        if offers:
            prime_info = offers[0]["PrimeInformation"]
            print(f"✅ PrimeInformation取得成功:")
            print(f"   IsPrime: {prime_info.get('IsPrime', 'N/A')}")
            print(f"   IsNationalPrime: {prime_info.get('IsNationalPrime', 'N/A')}")
            
            # 出品者情報も確認
            seller_info = offers[0].get("Seller", {})
            print(f"   SellerId: {seller_info.get('SellerId', 'N/A')}")
            print(f"   SellerName: {seller_info.get('Name', 'N/A')}")
            
            print("\n🎉 GPTの指摘通り、get_item_offersは正常動作！")
            return True
        else:
            print("⚠️ オファー情報なし")
            return False
            
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        return False

if __name__ == "__main__":
    success = test_fixed_sp_api()
    if success:
        print("\n🚀 Step 4の再実行準備完了！")
    else:
        print("\n🔧 さらなる調整が必要です")
