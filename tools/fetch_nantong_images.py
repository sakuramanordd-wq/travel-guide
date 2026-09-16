#!/usr/bin/env python3
"""Fetch freely-licensed photos from Wikimedia Commons for the Nantong guide.

Writes images/*.jpg (scenery) and images/food/*.jpg (dish reference photos),
plus merges credits into images/credits.json / images/food/credits.json.
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
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
FOOD = os.path.join(OUT, "food")

# (subdir, filename, [search queries]) — first acceptable hit wins
TARGETS = [
    # ---------- 城市 / 风光：全部指定 Commons 上的具体文件，避免搜错 ----------
    ("", "hero-nantong.jpg", ["FILE:File:Nantong Langshan Scenic Spot (Wolf Hill).jpg"]),
    ("", "langshan.jpg", ["FILE:File:Guangjiao Temple on Wolf Hill.JPG"]),
    ("", "langshan-temple.jpg", ["FILE:File:Buddhist temple on Wolf Hill.JPG"]),
    ("", "langshan-luobinwang.jpg", ["FILE:File:Nantong - Langshan - Luo Binwang's tomb 1.jpg"]),
    ("", "langshan-zhangjian.jpg", ["FILE:File:Nantong - Langshan - Zhang Jian statue.jpg"]),
    ("", "haohe.jpg", ["FILE:File:City of Nantong and the River Hao.jpg"]),
    ("", "haohe-night.jpg", ["FILE:File:Hao River in The Evening.JPG"]),
    ("", "nantong-skyline.jpg", ["FILE:File:Nantong skyline flanking the Hao River.jpg"]),
    ("", "nantong-cbd.jpg", ["FILE:File:南通中央商务区.jpg"]),
    ("", "nantong-museum.jpg", ["FILE:File:南通博物苑1.jpg"]),
    ("", "nantong-museum-old.jpg", ["FILE:File:The Middle Building of Nantong Museum 2013-01.JPG"]),
    ("", "museum-kite.jpg", ["FILE:File:Nantong Museum - kite 1.jpg"]),
    ("", "tangzha.jpg", ["FILE:File:Dasheng Cotton Mill in Nantong, Jiangsu, China 20260220-1.jpg"]),
    ("", "tangzha-1895.jpg", ["FILE:File:1895 Square at Tangzha Old Town in Chongchuan, Nantong, Jiangsu, China 20260220.jpg"]),
    ("", "tangzha-statue.jpg", ["FILE:File:Statue of Zhang Jian at Tangzha Old Town in Chongchuan, Nantong, Jiangsu, China 20260220.jpg"]),
    ("", "dasheng-haimen.jpg", ["FILE:File:Bell Tower of Dasheng Cotton Mill in Haimen, Nantong, Jiangsu.jpg"]),
    ("", "zhonglou-nantong.jpg", ["FILE:File:Nantong Bell Tower and Watch Tower 26 2013-01.jpg"]),
    ("", "qiaolou-nantong.jpg", ["FILE:File:Nantong Bell Tower and Watch Tower 01 2013-01.jpg"]),
    ("", "tianning-nantong.jpg", ["FILE:File:Tianning Temple in Nantong 01 2013-01.jpg"]),
    ("", "wenfeng-pagoda.jpg", ["FILE:File:Nantong Wenfeng Tower 09 2013-01.JPG"]),
    ("", "wenfeng-pagoda2.jpg", ["FILE:File:南通文峰塔1.jpg"]),
    ("", "confucius-nantong.jpg", ["FILE:File:Nantong Confucian Temple 01 2013-01.JPG"]),
    ("", "guandimiao-alley.jpg", ["FILE:File:House of the Ming and Qing Dynasty in South Guandimiao Alley 01 2013-01.jpg"]),
    ("", "northgate-nantong.jpg", ["FILE:File:Historic Site of the North Gate of Nantong 01 2013-01.JPG"]),
    ("", "abacus-museum.jpg", ["FILE:File:China Abacuses Museum 01 2013-01.JPG"]),
    ("", "audit-museum.jpg", ["FILE:File:China Audit Museum 01 2013-01.JPG"]),
    ("", "chenghuang-nantong.jpg", ["FILE:File:Temple of Mystery of Nantong 01 2013-01.JPG"]),
    ("", "nantong-middle-school.jpg", ["FILE:File:Bell tower, campus of Nantong Middle School, PRC.jpg"]),
    ("", "nantong-station.jpg", ["FILE:File:CRH2A-2030 at Nantong Railway Station 20251026.jpg"]),
    ("", "nantong-airport.jpg", ["FILE:File:Facade, Terminal 3, Nantong Xingdong International Airport 20260619.jpg"]),
    ("", "sutong-bridge.jpg", ["FILE:File:Sutong Bridge.jpg"]),
    ("", "hutong-bridge.jpg", ["FILE:File:Husutong Yangtze River Bridge2.JPG"]),
    ("", "nantong-port.jpg", ["FILE:File:江苏南通港长江面上汽渡船 - panoramio.jpg"]),
    ("", "tourist-bus.jpg", ["FILE:File:Nantong Tourist Bus Line 2 at Gongnong Nanlu in Jiangsu, China 20250802.jpg"]),
    ("", "metro-exit.jpg", ["FILE:File:Exit 4 of Tangzha Park Station in Nantong.jpg"]),
    ("", "rugao-shuihuiyuan.jpg", ["FILE:File:水绘园.jpg"]),
    ("", "rugao-shuihuiyuan-door.jpg", ["FILE:File:Big door.jpg"]),
    ("", "rugao-dinghui.jpg", ["FILE:File:定慧禅寺佛塔.jpg"]),
    ("", "rugao-station.jpg", ["FILE:File:202308 Rugao Railway Station.jpg"]),
    ("", "bencha-ancient-town.jpg", ["FILE:File:Bencha Ancient Town.jpg"]),
    ("", "rudong-xiaoyangkou.jpg", ["FILE:File:Xiaoyangkou (15248630404).jpg"]),
    ("", "haimen-changle.jpg", ["FILE:File:张謇纪念馆本馆.jpg"]),
    ("", "haimen-gate.jpg", ["FILE:File:张謇纪念馆入口处，匾额为江泽民书写.jpg"]),
    ("", "haimen-ferry.jpg", ["FILE:File:Ferry of Chonghai Ferry in Haimen, Nantong, Jiangsu, China 20250802.jpg"]),
    ("", "qidong-night.jpg", ["FILE:File:Qidong night view.jpg"]),
    ("", "qidong-seawall.jpg", ["FILE:File:启东市东部海堤观潮台.jpg"]),
    ("", "qidong-rapeflower.jpg", ["FILE:File:启东油菜花盛开.JPG"]),
    ("", "lvsi-jiqingan.jpg", ["FILE:File:位于吕四鹤城公园的集庆庵.jpg"]),
    ("", "lvsi-street.jpg", ["FILE:File:欣乐鹤城商业街.jpg"]),
    ("", "zhangjian-memorial.jpg", ["FILE:File:The Gate of Zhang Jian Memorial Hall.jpg"]),
    ("", "yangtze-ferry.jpg", ["FILE:File:江苏南通港长江面上汽渡船 - panoramio (1).jpg"]),

    # ---------- 美食参考图（同类菜品示意，不是该店实拍） ----------
    ("food", "f-wenge.jpg", ["FILE:File:Meretrix lusoria 01.jpg"]),
    ("food", "f-wenge-tang.jpg", ["FILE:File:Red mushroom and fresh Duotou clams soup at PUTIEN (20200606174213).jpg"]),
    ("food", "f-tangbao.jpg", ["FILE:File:开封第一楼小笼包.JPG"]),
    ("food", "f-xiaolongbao.jpg", ["FILE:File:Xiaolongbao-breakfast.jpg"]),
    ("food", "f-gangpan.jpg", ["FILE:File:Shaobing5.jpg"]),
    ("food", "f-cuibing.jpg", ["FILE:File:Suzhou-style rice cake.jpg"]),
    ("food", "f-yuebing.jpg", ["FILE:File:Savoury Suzhou-style meat mooncake.jpg"]),
    ("food", "f-mian.jpg", ["FILE:File:202308 Pickled Mustard Green Noodle with Braised Dapai and Fried Tofu Toppings.jpg"]),
    ("food", "f-yutangmian.jpg", ["FILE:File:Noodles soup with fish eggs and fish dumplings with octopus ball.jpg"]),
    ("food", "f-hundun.jpg", ["FILE:File:FOOD Wonton Soup.jpg"]),
    ("food", "f-guotie.jpg", ["FILE:File:Guotie 锅贴 potstickers from 乐陵（laoling）.jpg"]),
    ("food", "f-haixian.jpg", ["FILE:File:SZ 深圳 Shenzhen DMD 東門町美食街 Dong Men Ding Food Street steamed crabs Feb 2017 IX1 (2).jpg"]),
    ("food", "f-yu.jpg", ["FILE:File:Cantonese style steamed fish and special side dishes in lunch.jpg"]),
    ("food", "f-yangrou.jpg", ["FILE:File:Yangrou Mixian at a restaurant in Panzhihua (20231002123322).jpg"]),
    ("food", "f-zaocha.jpg", ["FILE:File:HK Sheung Wan morning tea Dim Sum 燒賣 Shaomai n Glass bowl Feb-2012.jpg"]),
    ("food", "f-zaocan.jpg", ["FILE:File:Breakfast selections at a restaurant near Wanshousi, Beijing (20230313082120).jpg"]),
    ("food", "f-congee.jpg", ["FILE:File:Chinese rice congee.jpg"]),
    ("food", "f-luwei.jpg", ["FILE:File:2007-10-24 Lou Mei in Taipei.jpg"]),
    ("food", "f-gaodian.jpg", ["FILE:File:Imprinted Black Sesame Rice Cake - Making (01).jpg"]),
    ("food", "f-huangjiu.jpg", ["FILE:File:Shaoxing Rice Wine, Huadiao, 10ys, bottle and glass.jpg"]),
    ("food", "f-cha.jpg", ["FILE:File:Tai Won Mein restaurant Chinese tea Greenwich Church Street, Greenwich London England.jpg"]),
    ("food", "f-coffee.jpg", ["FILE:File:Caffe Latte cup.jpg"]),
    ("food", "f-jiachang.jpg", ["FILE:File:Special foods & cuisines in Chongqing - Family Dinner 5th.jpg"]),
    ("food", "f-shucai.jpg", ["FILE:File:Greens with garlic - San Francisco, CA.jpg"]),
    ("food", "f-chaofan.jpg", ["FILE:File:Yeung Chow Fried Rice in Hong Kong Fast Food Shop.JPG"]),
    ("food", "f-haixian-platter.jpg", ["FILE:File:Jitang Cuan Haibang at Juchunyuan, Fuzhou (20250127115522).jpg"]),
]

BAD_TITLE = re.compile(r"(map|plan|diagram|logo|sign|chart|graph|banknote|stamp|screenshot|poster|coat of arms)", re.I)


def api(params):
    params = dict(params)
    params["format"] = "json"
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
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def pick(query, min_w=1100, min_h=700):
    data = api({
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6",
        "gsrlimit": "14",
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": "1400",
    })
    pages = list((data.get("query") or {}).get("pages", {}).values())
    pages.sort(key=lambda p: p.get("index", 99))
    cands = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        title = p.get("title", "")
        if BAD_TITLE.search(title):
            continue
        w, h = ii.get("width", 0), ii.get("height", 0)
        if w < min_w or h < min_h:
            continue
        if h / max(w, 1) > 1.3:
            continue
        cands.append((title, ii))
    return cands


def main():
    os.makedirs(FOOD, exist_ok=True)
    credits = json.load(open(os.path.join(OUT, "credits.json"), encoding="utf-8"))
    fcredits_path = os.path.join(FOOD, "credits.json")
    fcredits = json.load(open(fcredits_path, encoding="utf-8")) if os.path.exists(fcredits_path) else {}

    only = set(sys.argv[1:])
    for sub, fname, queries in TARGETS:
        if only and fname not in only:
            continue
        store = fcredits if sub == "food" else credits
        dest = os.path.join(OUT, sub, fname)
        if os.path.exists(dest) and fname in store and os.path.getsize(dest) > 20000:
            print(f"skip  {fname} (exists)")
            continue
        min_w, min_h = (900, 560) if sub == "food" else (1100, 700)
        chosen = None
        for q in queries:
            try:
                if q.startswith("FILE:"):
                    title = q[5:]
                    d = api({"action": "query", "titles": title, "prop": "imageinfo",
                             "iiprop": "url|size|extmetadata", "iiurlwidth": "1400"})
                    pg = list((d.get("query") or {}).get("pages", {}).values())[0]
                    ii = (pg.get("imageinfo") or [{}])[0]
                    ok = ii.get("thumburl") or ii.get("url")
                    cands = [(pg.get("title", title), ii)] if ok else []
                else:
                    cands = pick(q, min_w, min_h)
            except Exception as e:  # noqa: BLE001
                print(f"ERR   {fname} query={q}: {e}", file=sys.stderr)
                continue
            if cands:
                chosen = cands[0]
                print(f"cands {fname} <- '{q}': " + " | ".join(c[0] for c in cands[:3]))
                break
        if not chosen:
            print(f"MISS  {fname}: no candidate")
            continue
        title, ii = chosen
        em = ii.get("extmetadata") or {}
        url = ii.get("thumburl") or ii.get("url")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r, open(dest, "wb") as f:
                f.write(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"ERR   download {fname}: {e}", file=sys.stderr)
            continue
        store[fname] = {
            "title": title,
            "author": strip_html((em.get("Artist") or {}).get("value", "")),
            "license": strip_html((em.get("LicenseShortName") or {}).get("value", "")),
            "page": ii.get("descriptionurl", ""),
            "bytes": os.path.getsize(dest),
        }
        print(f"OK    {fname} <- {title} [{store[fname]['license']}] {os.path.getsize(dest)//1024}KB")

    json.dump(credits, open(os.path.join(OUT, "credits.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(fcredits, open(fcredits_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote credits:", len(credits), "scenery /", len(fcredits), "food")


if __name__ == "__main__":
    main()
