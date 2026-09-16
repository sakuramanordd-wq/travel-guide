#!/usr/bin/env python3
"""Fetch freely-licensed Wikimedia Commons photos for the Ningde guide.

Writes images/*.jpg (scenery) and images/food/*.jpg (dish reference photos) and
merges credits into images/credits.json / images/food/credits.json.
Modeled on tools/fetch_nantong_images.py (same API + credit format).

Run: python3 tools/ningde/fetch_images.py [filename ...]
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
    ("", "hero-ningde.jpg", ["FILE:File:Xiapu Sunrise - Flickr - Jaykhuang.jpg"]),
    ("", "xiapu-beiqi-sunrise.jpg", ["FILE:File:Xiapu Sunrise - Flickr - Jaykhuang.jpg"]),
    ("", "xiapu-sbend.jpg", ['FILE:File:"S" Bend, Xiapu, China (28221022361).jpg']),
    ("", "xiapu-xiaohao.jpg", ["FILE:File:Xiaohao Beach, Xiapu 20230827.jpg"]),
    ("", "xiapu-xiaohao2.jpg", ["FILE:File:小浩滩涂6-爵士鼓手 - panoramio.jpg"]),
    ("", "xiapu-gaoluo.jpg", ["FILE:File:Gaoluo Beach, Xiapu 20230826.jpg"]),
    ("", "xiapu-jishi-beach.jpg", ["FILE:File:Jishi Beach, Xiapu 20230826.jpg"]),
    ("", "xiapu-sunset.jpg", ["FILE:File:Xiapu sunset.JPG"]),
    ("", "xiyang-island-sunrise.jpg", ["FILE:File:The Sunrise on a beach of Xiyang Island, East China Sea.jpg"]),
    ("", "xiapu-station.jpg", ["FILE:File:Xiapu Railway Station 20230825.jpg"]),
    ("", "ningde-station.jpg", ["FILE:File:Ningde Railway Station (20170129155814).jpg"]),
    ("", "taimushan-station.jpg", ["FILE:File:Taimushan Zhan - P1220465.JPG"]),
    ("", "fuding-station.jpg", ["FILE:File:Fude Railway Station 202102211146.jpg"]),
    ("", "taimushan.jpg", ["FILE:File:Mount Taimu 20230827.jpg"]),
    ("", "taimushan-rock.jpg", ["FILE:File:Mount Taimu Rock 20230827.jpg"]),
    ("", "taimushan-town.jpg", ["FILE:File:太姥山镇街景.jpg"]),
    ("", "taimushan-inscription.jpg", ["FILE:File:Cliff inscription of Mount Taimu 20230827.jpg"]),
    ("", "baishuiyang.jpg", ["FILE:File:白水洋水上广场 - Baishuiyang Water Square - 2014.07 - panoramio.jpg"]),
    ("", "baishuiyang-stream.jpg", ["FILE:File:奇特的平板溪-白水洋 - panoramio.jpg"]),
    ("", "baishuiyang-gate.jpg", ["FILE:File:白水洋景区入口处 - panoramio.jpg"]),
    ("", "sanduao-boats.jpg", ["FILE:File:三都澳的渔船 - panoramio.jpg"]),
    ("", "sanduao-doumu.jpg", ["FILE:File:快艇上拍三都澳的斗姥岛 - panoramio.jpg"]),
    ("", "sanduao-pier.jpg", ["FILE:File:三都澳斗姥岛的上岛码头 - panoramio.jpg"]),
    ("", "sanduao-church.jpg", ["FILE:File:三都近代建筑群-天主堂正面 (retouched).jpg"]),
    ("", "huotong.jpg", ["FILE:File:霍童洞天景区.jpg"]),
    ("", "huotong-tianhougong.jpg", ["FILE:File:霍童天后宫 01.jpg"]),
    ("", "liyuxi.jpg", ["FILE:File:周宁鲤鱼溪 01.jpg"]),
    ("", "liyuxi-lotus.jpg", ["FILE:File:周宁鲤鱼溪荷花池 03.jpg"]),
    ("", "jiulongji.jpg", ["FILE:File:周宁九龙漈瀑布景区 08.jpg"]),
    ("", "jiulongji2.jpg", ["FILE:File:周宁九龙漈瀑布景区 04.jpg"]),
    # 补缺口（用搜索词，脚本会打印候选）
    ("", "xiapu-dongbi.jpg", ["FILE:File:霞浦県のある島の岸で泊まる漁船団.jpg"]),
    ("", "xiapu-sansha.jpg", ["Sansha Town Xiapu", "Xiapu fishing port", "Xiapu harbour"]),
    ("", "xiapu-yangjiaxi.jpg", ["banyan tree Fujian", "banyan tree China mist", "Fujian banyan grove"]),
    ("", "xiapu-mudflat.jpg", ["Xiapu tidal flat", "Xiapu mud flat sunrise", "Xiapu seaweed"]),
    ("", "yushan-island.jpg", ["Yushan Dao Fuding", "Dayushan Island", "Fuding island grassland"]),
    ("", "fuding-tea.jpg", ["Fuding white tea", "tea plantation Fujian", "white tea processing"]),
    ("", "ningde-city.jpg", ["Ningde Jiaocheng", "Ningde Fujian", "Ningde street"]),
    ("", "xiapu-county.jpg", ["Xiapu County street", "Xiapu town", "Xiapu Fujian"]),
    ("", "pingnan-village.jpg", ["Pingnan Fujian village", "Longtan village Fujian", "Pingnan County"]),
    ("", "longjing-village.jpg", ["Xiapu village houses", "Fujian coastal village"]),

    # ---------- 美食参考图（同类菜品示意，非该店实拍） ----------
    ("food", "f-rouqian.jpg", ["FILE:File:福鼎肉片.jpg"]),
    ("food", "f-rouqian2.jpg", ["FILE:File:福鼎肉片2.jpg"]),
    ("food", "f-guangbing.jpg", ["FILE:File:Fuqing Guangbing's two sides.png"]),
    ("food", "f-kompyang.jpg", ["FILE:File:Jian'ou Kompyang.JPG"]),
    ("food", "f-bianrou.jpg", ["FILE:File:Putien bian rou dumpling soup.jpg"]),
    ("food", "f-wonton.jpg", ["FILE:File:Wonton.jpg"]),
    ("food", "f-taro-cake.jpg", ["FILE:File:Taro Cake dllu.jpg"]),
    ("food", "f-seafood.jpg", ["FILE:File:Jitang Cuan Haibang at Juchunyuan, Fuzhou (20250127115522).jpg"]),
    ("food", "f-crab.jpg", ["FILE:File:SZ 深圳 Shenzhen DMD 東門町美食街 Dong Men Ding Food Street steamed crabs Feb 2017 IX1 (2).jpg"]),
    ("food", "f-fishball.jpg", ["Fuzhou fish ball", "fish ball soup Chinese", "Fujian fish ball"]),
    ("food", "f-white-tea.jpg", ["Fuding white tea", "Bai Mudan tea", "white tea leaves cup"]),
    ("food", "f-noodle.jpg", ["FILE:File:202308 Pickled Mustard Green Noodle with Braised Dapai and Fried Tofu Toppings.jpg"]),
    ("food", "f-oyster-omelette.jpg", ["oyster omelette Fujian", "oyster omelette", "Fujian oyster pancake"]),
    ("food", "f-beef-ball.jpg", ["beef ball soup Chinese", "beef balls bowl", "Chaoshan beef balls"]),
    ("food", "f-congee.jpg", ["FILE:File:Chinese rice congee.jpg"]),
    ("food", "f-seafood-noodle.jpg", ["seafood noodles Chinese", "Fujian seafood noodle soup"]),
    ("food", "f-street-food.jpg", ["Chinese street food stall seafood", "night market seafood China"]),
    ("food", "f-rice-wine.jpg", ["FILE:File:Shaoxing Rice Wine, Huadiao, 10ys, bottle and glass.jpg"]),
    ("food", "f-breakfast.jpg", ["FILE:File:Breakfast selections at a restaurant near Wanshousi, Beijing (20230313082120).jpg"]),
]

BAD_TITLE = re.compile(r"(map|plan|diagram|logo|sign|chart|graph|banknote|stamp|screenshot|poster|coat of arms|\.tiff)", re.I)


def api(params):
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.load(r)
            time.sleep(2.5)
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5.0 * (attempt + 1))
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
