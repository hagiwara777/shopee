from sp_api.api import Catalog

def search_asin_by_title(jp_title):
    try:
        catalog = Catalog()
        result = catalog.search_catalog_items(keywords=jp_title)
        items = result.payload.get("items", [])
        if items:
            return items[0].get("asin", "")
        else:
            return ""
    except Exception as e:
        print(f"ASIN検索失敗: {e}")
        return ""
