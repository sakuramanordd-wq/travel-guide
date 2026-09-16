#!/usr/bin/env python3
"""Fetch many Ctrip POI/city hotel list pages for the Ningde trip, dump raw HTML
into research/_raw/ningde/ and write a combined TSV + JSON of hotel cards."""
import os, sys, json, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RAW = os.path.join(ROOT, "research", "_raw", "ningde")
CACHE = os.path.join(RAW, "ctrip_list")
os.makedirs(CACHE, exist_ok=True)

TARGETS = [
    ("xiapu_city",      20980, None),
    ("xiapu_beiqi",     20980, "北岐滩涂"),
    ("xiapu_dongbi",    20980, "东壁"),
    ("xiapu_huazhu",    20980, "花竹村"),
    ("xiapu_xiaohao",   20980, "小皓"),
    ("xiapu_sansha",    20980, "三沙镇"),
    ("xiapu_yangjiaxi", 20980, "杨家溪"),
    ("xiapu_station",   20980, "霞浦站"),
    ("ningde_city",     378,   None),
    ("ningde_wanda",    378,   "宁德万达广场"),
    ("ningde_station",  378,   "宁德站"),
    ("ningde_dongqiao", 378,   "东侨"),
    ("fuding_city",     246,   None),
    ("fuding_tailaoshan", 246, "太姥山"),
    ("fuding_qinyu",    246,   "秦屿镇"),
    ("fuding_station",  246,   "太姥山站"),
    ("pingnan_baishuiyang", 21127, "白水洋"),
]

def run(name, city, option):
    out_html = os.path.join(CACHE, f"{name}.html")
    if not (os.path.exists(out_html) and os.path.getsize(out_html) > 100000):
        cmd = ["python3", os.path.join(HERE, "ctrip_list.py"), "--city", str(city),
               "--in", "2026-10-01", "--out", "2026-10-02", "--dump", out_html]
        if option:
            cmd += ["--option", option]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            print("ERR", name, r.stderr[:200]); return None
    else:
        cmd = ["python3", os.path.join(HERE, "ctrip_list.py"), out_html]
    # re-parse from the dumped html (works offline)
    html = open(out_html, encoding="utf-8").read()
    sys.path.insert(0, HERE)
    import importlib.util
    spec = importlib.util.spec_from_file_location("cl", os.path.join(HERE, "ctrip_list.py"))
    cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
    cards = cl.cards(cl.decode_payload(html))
    for c in cards:
        c["src_page"] = name
        c["src_city"] = city
        c["src_option"] = option
    return cards

allc = []
for name, city, option in TARGETS:
    try:
        c = run(name, city, option) or []
    except Exception as e:
        print("FAIL", name, type(e).__name__, e); c = []
    print(f"{name:22s} city={city:6d} option={option or '-':10s} cards={len(c)}")
    allc += c
    time.sleep(0.4)

json.dump(allc, open(os.path.join(RAW, "ctrip_list_cards.json"), "w"),
          ensure_ascii=False, indent=1)
# dedupe by hotelId keeping the most specific source page
seen = {}
for c in allc:
    hid = c["hotelId"]
    if hid not in seen or (c["src_option"] and not seen[hid]["src_option"]):
        seen[hid] = c
print("unique hotels:", len(seen))
with open(os.path.join(RAW, "ctrip_list_cards.tsv"), "w", encoding="utf-8") as f:
    f.write("hotelId\tsrc\tname\tdiamond\tscore\treviews\tposition\taddress\trooms\n")
    for hid, c in seen.items():
        rooms = "; ".join(f'{r["room"]}[{r["bed"]}]{"|".join(r["tags"] or [])}' for r in c["rooms"][:2])
        f.write("\t".join([str(hid), c["src_page"], c["name"], str(c["diamond"]), str(c["score"]),
                           str(c["reviews"]), str(c["positionDesc"]), str(c["address"]), rooms]) + "\n")
print("wrote", os.path.join(RAW, "ctrip_list_cards.tsv"))
