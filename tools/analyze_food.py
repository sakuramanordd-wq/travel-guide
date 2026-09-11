#!/usr/bin/env python3
"""把 research/tabelog_rankings.json 变成「按区域 / 按品类」的候选清单。

用法:
  python3 tools/analyze_food.py                 # 每个区域 top 榜
  python3 tools/analyze_food.py ramen           # 只看某个品类
"""
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "research", "tabelog_rankings.json")


def genre_of(area_genre):
    parts = area_genre.split("/")
    return parts[-1].strip() if len(parts) > 1 else ""


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    want = sys.argv[1] if len(sys.argv) > 1 else None
    if want:
        rows = {}
        for area, items in data.items():
            for it in items:
                if want in genre_of(it["area_genre"]):
                    rows[it["id"]] = it
        rows = sorted(rows.values(), key=lambda r: (-(r["score"] or 0), -(r["reviews"] or 0)))
        for r in rows:
            print("%-5s %-6s %-38s %-40s %s" % (r["score"], r["reviews"], r["name"][:36],
                                                r["area_genre"][:38], (r["budget"] or [""])[0]))
        print(len(rows), "rows")
        return
    for area, items in data.items():
        uniq = {it["id"]: it for it in items}
        top = sorted(uniq.values(), key=lambda r: (-(r["score"] or 0), -(r["reviews"] or 0)))
        top = [r for r in top if (r["reviews"] or 0) >= 60][:22]
        print("\n== %s（%d 家候选，评分≥ / 评论≥60）" % (area, len(uniq)))
        for r in top:
            print("  %-5s %-6s %-34s %-32s %s" % (r["score"], r["reviews"], r["name"][:32],
                                                  genre_of(r["area_genre"])[:30], (r["budget"] or [""])[0]))


if __name__ == "__main__":
    main()
