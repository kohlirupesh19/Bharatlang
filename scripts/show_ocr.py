import json, sys, glob
sys.stdout.reconfigure(encoding="utf-8")
f = glob.glob(r"C:\dev\Bharatlang\eval_data\ocr_probe\*\results.json")[0]
pages = next(iter(json.load(open(f, encoding="utf-8")).values()))
b0 = pages[0]["blocks"][0]
print("block keys:", list(b0.keys()))
for p in pages:
    print(f"--- page {p.get('page')} blocks={len(p['blocks'])}")
    for b in p["blocks"][:40]:
        text = b.get("text") or b.get("html") or ""
        print(f"[{b.get('label', b.get('block_type'))}] {text[:400]}")
