#!/usr/bin/env python3
"""Fetch freely-licensed Wikimedia Commons photos for the Fuding (福鼎) guide.

Writes images/*.jpg (scenery) and images/food/*.jpg (dish reference photos) and
merges credits into images/credits.json / images/food/credits.json.
Modeled on tools/ningde/fetch_images.py (same API + credit format).

Run: python3 tools/fuding/fetch_images.py [filename ...]
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "travel-guide-builder/1.0 (personal travel guide; contact: local)"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "images")
FOOD = os.path.join(OUT, "food")

# (subdir, filename, [queries]) — FILE:File:X means "use exactly this Commons file"
TARGETS = [
    # ---------- 风光 / 城市 ----------
    # hero-fuding.jpg: 跳过——已有 taimushan.jpg (Mount Taimu 20230827, 3840x2560) 可作头图
    # 茶山梯田：Commons 无福鼎本地茶园图，用福建安溪云岭茶庄园同类示意（图注须如实标注）
    ("", "fuding-tea-garden.jpg", ["FILE:File:Anxi Yunling Tea Estate.jpg"]),
    # 太姥山绿雪芽古茶树（福鼎白茶始祖，竖构图）
    ("", "lvxueya.jpg", ["FILE:File:Luxueya, White tea tree.jpg"]),
    # 白茶晒青/萎凋 + 采摘
    ("", "baicha-withering.jpg", ["FILE:File:White Tea Withering.jpg"]),
    ("", "baicha-picking.jpg", ["FILE:File:White tea hand-picking.jpg"]),
    # 牛郎岗海滨
    ("", "niulanggang.jpg", ["FILE:File:牛郎岗海滨景区 - Niulang Hill Seashore Scenic Area - 2015.05 - panoramio.jpg"]),
    # 嵛山岛补充图：Commons 仅 Dayushan Island.jpg 一张（已存为 yushan-island.jpg），跳过
    # 福鼎市区（无桐山溪夜景图，用市区远眺替代）
    ("", "fuding-city.jpg", ["FILE:File:高速公路上拍福鼎市区 - panoramio.jpg"]),

    # ---------- 美食参考图（同类菜品示意，非该店实拍） ----------
    # 福鼎肉片：已有 f-rouqian.jpg / f-rouqian2.jpg（真·福鼎肉片），跳过
    ("food", "f-mizhijichi.jpg", ["FILE:File:Honey chicken wings (6630284309).jpg"]),
    # 牛肉丸汤：已有 f-beef-ball.jpg（Beef Ball Soup），跳过
    ("food", "f-yuni.jpg", ["FILE:File:芋泥.jpg"]),
    ("food", "f-yupian.jpg", ["FILE:File:Pickled mustard fish filet soup.jpg"]),
    ("food", "f-guobianhu.jpg", ["FILE:File:Diāng-biĕng-gù with seafood in Fuzhou (20200927131715).jpg"]),
    ("food", "f-rouyan.jpg", ["FILE:File:Rouyan.jpg"]),
    ("food", "f-pipixia.jpg", ["FILE:File:椒盐皮皮虾.jpg"]),
    # 白茶饮品：已有 f-white-tea.jpg（白牡丹茶汤），跳过
]

BAD_TITLE = re.compile(r"(map|plan|diagram|logo|sign|chart|graph|banknote|stamp|screenshot|poster|coat of arms|\.tiff)", re.I)


def api(params):
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.load(r)
            time.sleep(3.0)
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(8.0 * (attempt + 1))
    raise last


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def pick(query, min_w=1100, min_h=700):
    data = api({"action": "query", "generator": "search",
                "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": "6",
                "gsrlimit": "14", "prop": "imageinfo",
                "iiprop": "url|size|extmetadata", "iiurlwidth": "1400"})
    pages = list((data.get("query") or {}).get("pages", {}).values())
    pages.sort(key=lambda p: p.get("index", 99))
    cands = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        title = p.get("title", "")
        if BAD_TITLE.search(title):
            continue
        w, h = ii.get("width", 0), ii.get("height", 0)
        if w < min_w or h < min_h or h / max(w, 1) > 1.3:
            continue
        cands.append((title, ii))
    return cands


def fetch_one(q, min_w, min_h):
    if q.startswith("FILE:"):
        title = q[5:]
        d = api({"action": "query", "titles": title, "prop": "imageinfo",
                 "iiprop": "url|size|extmetadata", "iiurlwidth": "1400"})
        pg = list((d.get("query") or {}).get("pages", {}).values())[0]
        ii = (pg.get("imageinfo") or [{}])[0]
        ok = ii.get("thumburl") or ii.get("url")
        return ([(pg.get("title", title), ii)] if ok else [])
    return pick(q, min_w, min_h)


def main():
    os.makedirs(FOOD, exist_ok=True)
    credits = json.load(open(os.path.join(OUT, "credits.json"), encoding="utf-8"))
    fpath = os.path.join(FOOD, "credits.json")
    fcredits = json.load(open(fpath, encoding="utf-8")) if os.path.exists(fpath) else {}

    only = set(sys.argv[1:])
    for sub, fname, queries in TARGETS:
        if only and fname not in only:
            continue
        store = fcredits if sub == "food" else credits
        dest = os.path.join(OUT, sub, fname)
        if os.path.exists(dest) and fname in store and os.path.getsize(dest) > 20000:
            print(f"skip  {fname}")
            continue
        min_w, min_h = (900, 560) if sub == "food" else (1100, 700)
        chosen = None
        for q in queries:
            try:
                cands = fetch_one(q, min_w, min_h)
            except Exception as e:  # noqa: BLE001
                print(f"ERR   {fname} q={q}: {e}", file=sys.stderr)
                continue
            if cands:
                chosen = cands[0]
                print(f"cands {fname} <- '{q}': " + " | ".join(c[0] for c in cands[:3]))
                break
        if not chosen:
            print(f"MISS  {fname}")
            continue
        title, ii = chosen
        em = ii.get("extmetadata") or {}
        url = ii.get("thumburl") or ii.get("url")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                blob = r.read()
        except Exception as e:  # noqa: BLE001
            print(f"ERR   {fname} download: {e}", file=sys.stderr)
            continue
        open(dest, "wb").write(blob)
        store[fname] = {
            "title": title,
            "author": strip_html(em.get("Artist", {}).get("value", ""))[:400],
            "license": strip_html(em.get("LicenseShortName", {}).get("value", "")),
            "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "bytes": len(blob),
        }
        print(f"ok    {fname} <- {title} ({len(blob)//1024} KB) {store[fname]['license']}")
        json.dump(credits, open(os.path.join(OUT, "credits.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(fcredits, open(fpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("credits:", len(credits), "food:", len(fcredits))


if __name__ == "__main__":
    main()
