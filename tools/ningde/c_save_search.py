#!/usr/bin/env python3
"""c_save_search.py NAME "engine-query" -- run tools/s.py and save output to research/_raw/ningde/NAME.txt with URL header.
Usage: python3 tools/ningde/c_save_search.py c-pier-xxx "sogou:三都澳 礁头码头"
"""
import sys, os, subprocess

BASE = "/home/hukun02/Project/travel-guide"
OUT = os.path.join(BASE, "research/_raw/ningde")

def main():
    name = sys.argv[1]
    spec = sys.argv[2]
    eng, q = spec.split(":", 1)
    if eng == "toutiao":
        cmd = ["python3", "tools/t.py", q]
        url = "https://so.toutiao.com/search?keyword=" + q
    else:
        cmd = ["python3", "tools/s.py", q, eng, "12000"]
        url = {"sogou": "https://www.sogou.com/web?query=", "so360": "https://www.so.com/s?q=",
               "bing": "https://cn.bing.com/search?q="}[eng] + q
    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=120)
    txt = r.stdout or r.stderr
    path = os.path.join(OUT, name + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# SEARCH-RESULT-SNAPSHOT (engine=%s)\n# URL: %s\n# fetched: 2026-09-15\n\n"
                % ("toutiao" if eng == "toutiao" else eng, url))
        f.write(txt)
    print("SAVED", path, len(txt))
    print(txt[:2500])

main()
