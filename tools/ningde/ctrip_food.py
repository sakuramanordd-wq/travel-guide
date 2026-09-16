#!/usr/bin/env python3
"""Parse Ctrip (携程) restaurant list pages -> restaurants with 评分 / 点评数 / 推荐菜.

URL pattern: https://you.ctrip.com/restaurant/<cityslug><districtid>.html
(district ids come from the sight URLs, e.g. 霞浦 xiapu1154, 福鼎 fuding613,
 宁德 ningde490, 屏南 pingnan2649, 周宁 zhouning2683, 三沙/东壁 → 1154)

Usage: python3 tools/ningde/ctrip_food.py xiapu1154 fuding613 ningde490 ...
Writes research/_raw/ningde/restaurants.json and prints a table.
"""
import concurrent.futures as cf
import html
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUTDIR = os.path.join(ROOT, "research", "_raw", "ningde")
CACHE = os.path.join(ROOT, "research", "_raw", "cache")
os.makedirs(OUTDIR, exist_ok=True)
UA_M = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")


def clean(t):
    t = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</tr>|</li>|</h\d>|</span>|</a>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t).replace("\u3000", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def get_text(city, force=False):
    slug, did = city[: -len(city.lstrip("abcdefghijklmnopqrstuvwxyz"))] or city, re.sub(r"\D", "", city)
    cf_ = os.path.join(CACHE, f"ctrip_food_{city}.txt")
    if os.path.exists(cf_) and os.path.getsize(cf_) > 5000 and not force:
        return open(cf_, encoding="utf-8").read()
    url = f"https://you.ctrip.com/restaurant/{city}.html"
    raw = subprocess.run(["curl", "-sS", "-m", "45", "-L", "-A", UA_M,
                          "-H", "Accept-Language: zh-CN,zh;q=0.9", url],
                         capture_output=True).stdout
    t = clean(raw.decode("utf-8", "ignore"))
    open(cf_, "w", encoding="utf-8").write(t)
    return t


def parse(t, city):
    out = []
    # 「必吃餐馆」：\uead2 店名 → "4.5 分" → "( 39 条点评)" → 游友最爱吃: 菜、菜…
    pat = (r"\uead2\s*([^\n]{2,44})\n\s*(\d(?:\.\d)?)\s*分\s*\n\s*\(\s*([\d,]+)\s*条点评\)"
           r"\n\s*游友最爱吃:\n([\s\S]{0,1200}?)(?=\n\s*\uead2|\n\s*更多|\Z)")
    for m in re.finditer(pat, t):
        name, score, revs, block = m.group(1).strip(), m.group(2), m.group(3), m.group(4)
        parts = [x.strip(" \n") for x in re.split(r"\n、\n", block)]
        dishes = [x for x in parts if 1 < len(x) < 18][:18]
        out.append({"city": city, "name": name, "score": score,
                    "reviews": int(revs.replace(",", "")), "dishes": dishes})
    # 「必吃美食」：菜名 / 介绍 / 详情 / 哪里吃
    dishes = []
    for m in re.finditer(r"\n\s*([^\n]{2,14})\n\s*([^\n]{10,220})\n\s*详情\n([\s\S]{0,300}?)(?=\n\s*[^\n]{2,14}\n\s*[^\n]{10,220}\n\s*详情|\n\s*必吃餐馆|\Z)", t):
        d, intro, where = m.group(1).strip(), m.group(2).strip(), m.group(3)
        if re.search(r"(分|点评|酒店|门票|攻略|更多)", d):
            continue
        names = [w.strip(" \n、") for w in re.split(r"[、,，]|\n", where) if 1 < len(w.strip()) < 30]
        dishes.append({"name": d, "intro": intro[:220], "where": names[:6]})
    return out, dishes[:14]


if __name__ == "__main__":
    cities = sys.argv[1:] or ["xiapu1154", "fuding613", "ningde490"]
    res, dishmap = [], {}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for city, t in zip(cities, ex.map(get_text, cities)):
            rs, ds = parse(t, city)
            res += rs
            dishmap[city] = ds
    json.dump({"restaurants": res, "signature_dishes": dishmap},
              open(os.path.join(OUTDIR, "restaurants.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for r in sorted(res, key=lambda x: -x["reviews"]):
        print(f'{r["city"]}\t{r["name"]}\t{r["score"]}分/{r["reviews"]}条\t{"、".join(r["dishes"][:8])}')
    for c, ds in dishmap.items():
        print(f"--- {c} 必吃美食:", "；".join(f'{d["name"]}({d["where"][:2]})' for d in ds))
