# fix_brands_to_list.py （再掲・安全実行）
import json, collections, pathlib
p = pathlib.Path("data/brands.json")
d = json.loads(p.read_text(encoding="utf-8"))
if isinstance(d, dict):
    new = collections.defaultdict(list)
    for k, v in d.items():
        new[v].append(k) if v != k else new[v].append(k)
    p.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ brands.json を “英語キー : [バリエーション…]” 形式に変換しました")
else:
    print("既にリスト型、または想定外の形式です")
