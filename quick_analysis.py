import pandas as pd

try:
    # Excelファイル読み込み
    df = pd.read_excel('output_with_asin_20250523_002442.xlsx')
    total = len(df)
    
    print('🎯 500品大規模テスト結果分析')
    print('=' * 40)
    print(f'📊 総データ数: {total}件')
    print()
    
    # ASIN成功率
    asin_success = (df["ASIN"].notna() & (df["ASIN"] != "")).sum()
    asin_rate = asin_success / total * 100
    print(f'🛒 ASIN取得成功: {asin_success}/{total} ({asin_rate:.1f}%)')
    
    # 日本語化成功率
    japanese_success = df["japanese_name"].notna().sum()
    japanese_rate = japanese_success / total * 100
    print(f'🇯🇵 日本語化成功: {japanese_success}/{total} ({japanese_rate:.1f}%)')
    
    # ブランド抽出成功率
    brand_success = (df["brand"].notna() & (df["brand"] != "") & (df["brand"] != "undefined")).sum()
    brand_rate = brand_success / total * 100
    print(f'🏷️ ブランド抽出成功: {brand_success}/{total} ({brand_rate:.1f}%)')
    
    # データクレンジング成功率
    clean_success = df["clean_title"].notna().sum()
    clean_rate = clean_success / total * 100
    print(f'✅ データクレンジング成功: {clean_success}/{total} ({clean_rate:.1f}%)')
    
    print()
    print('🏆 品質評価:')
    
    def get_grade(rate):
        if rate >= 85: return "🟢 優秀"
        elif rate >= 70: return "🟡 良好"
        else: return "🔴 要改善"
    
    print(f'  ASIN取得: {get_grade(asin_rate)}')
    print(f'  日本語化: {get_grade(japanese_rate)}')
    print(f'  ブランド抽出: {get_grade(brand_rate)}')
    print(f'  データクレンジング: {get_grade(clean_rate)}')
    
    # 総合スコア
    overall_score = (asin_rate + japanese_rate + brand_rate + clean_rate) / 4
    print()
    print(f'📊 総合スコア: {overall_score:.1f}% - {get_grade(overall_score)}')
    
    # エラー例を表示
    print()
    print('❌ ASIN取得失敗例（先頭3件）:')
    asin_failed = df[(df["ASIN"].isna()) | (df["ASIN"] == "")]
    for i, row in asin_failed.head(3).iterrows():
        title = row.get('clean_title', 'N/A')
        print(f'  - {title[:60]}...')
    
    print()
    print('❌ ブランド抽出失敗例（先頭3件）:')
    brand_failed = df[(df["brand"].isna()) | (df["brand"] == "") | (df["brand"] == "undefined")]
    for i, row in brand_failed.head(3).iterrows():
        title = row.get('clean_title', 'N/A')
        print(f'  - {title[:60]}...')

except Exception as e:
    print(f"エラーが発生しました: {e}")
    print("ファイルパスとファイル存在を確認してください。")