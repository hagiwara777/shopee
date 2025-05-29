from asin_processor.sp_api_service import get_prime_and_seller_info, get_credentials

credentials = get_credentials()
if credentials:
    # 既知のASINで直接テスト
    test_asins = [
        "B09J53D9LV",  # ファンケル商品例
        "B0DR952N7X",  # セザンヌ商品例  
        "B00KOTG7AE"   # ミルボン商品例
    ]
    
    for asin in test_asins:
        print(f"\n🧪 テスト: {asin}")
        result = get_prime_and_seller_info(asin, credentials)
        print(f"Prime: {result['is_prime']}, 出品者: {result['seller_name']}, タイプ: {result['seller_type']}")
