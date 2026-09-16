#!/usr/bin/env python3
"""Ctrip globalsearch for POIs (sights / food lists) in the Ningde area.

Usage: python3 tools/ningde/ctrip_poi.py "北岐滩涂" "太姥山" ...
Prints name / type / zone / 携程评分 / 评价数 / 参考门票价 / url.
"""
import json
import os
import sys
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctrip_search as cs  # noqa: E402

OUT = os.path.join(cs.ROOT, "research", "_raw", "ningde", "pois.json")

KEEP = ("sight", "foodlist", "food", "district", "scenery", "spot")


def rows(kw, t="all"):
    raw = cs.fetch(kw, t)
    try:
        j = json.loads(raw)
    except Exception:
        return []
    out = []
    for it in (j.get("data") or []):
        out.append({
            "kw": kw, "type": it.get("type"), "name": it.get("word"),
            "zone": it.get("zoneName"), "score": it.get("commentScore"),
            "reviews": it.get("commentCount"), "price": it.get("price"),
            "url": (it.get("url") or "").replace("http://", "https://"),
            "desc": (it.get("content") or "")[:120],
        })
    return out


if __name__ == "__main__":
    kws = sys.argv[1:]
    res = []
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for k, r in zip(kws, ex.map(rows, kws)):
            res += r
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in res:
        if r["type"] in KEEP or (r["reviews"] or 0):
            print(f'{r["kw"]}\t{r["type"]}\t{r["name"]}\t{r["zone"]}\t{r["score"]}/{r["reviews"]}\t{r["price"]}\t{r["url"][:80]}')
