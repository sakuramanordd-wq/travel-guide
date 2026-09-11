#!/usr/bin/env python3
"""Fetch freely-licensed dish / storefront photos from Wikimedia Commons for the
food cards of the Osaka-Kansai guide.

Writes images/food/*.jpg plus images/food/credits.json (title, author, license, source page).

Where Commons has a photo of the actual shop (e.g. 千房, だるま), that file is used;
otherwise a photo of the same dish is used and the page labels it as a reference photo.
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
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images", "food")

# target filename -> list of Commons search queries (first hit wins); "FILE:File:..." = exact file
TARGETS = [
    # ---- 宇治线（Day 4）----
    ("f-uji-nakamura.jpg", ["Nakamura Tokichi Uji", "matcha jelly Uji", "宇治 抹茶 生茶ゼリイ"]),
    ("f-uji-itoen.jpg", ["Itoh Kyuemon Uji", "matcha soba noodles", "宇治抹茶 そば"]),
    ("f-uji-tsuen.jpg", ["Tsuen Uji tea house", "matcha ice cream Uji", "宇治橋 通圓"]),
    ("f-uji-surugaya.jpg", ["cha dango", "茶団子", "Uji dango sweets"]),
    ("f-uji-seikou.jpg", ["mazesoba", "油そば", "abura soba noodles bowl"]),
    ("f-uji-shubaku.jpg", ["zaru soba", "せいろ蕎麦", "soba noodles Japan plate"]),
    ("f-uji-hagata.jpg", ["matcha roll cake", "抹茶ロールケーキ", "matcha cake slice"]),
    ("f-uji-mogumogu.jpg", ["matcha bread", "抹茶パン", "Japanese bakery bread"]),
    ("f-uji-kanbayashi.jpg", ["matcha shaved ice", "宇治金時", "kakigori matcha"]),
    ("f-uji-masuda.jpg", ["matcha soft serve ice cream", "抹茶ソフトクリーム"]),
    ("f-uji-rajinerro.jpg", ["pizza margherita Napoli", "wood fired pizza margherita"]),
    # ---- 串炸 · 新世界 ----
    ("f-daruma.jpg", ["FILE:File:Kushikatsu - Shinsekai (28289215848).jpg", "kushikatsu Shinsekai"]),
    ("f-gifuya.jpg", ["FILE:File:Osaka kushiage kushikatsu (3818694686).jpg", "kushikatsu assorted skewers"]),
    ("f-oyaji.jpg", ["kushikatsu Osaka restaurant", "串かつ 大阪 店内"]),
    ("f-yokozuna.jpg", ["FILE:File:番付メニュー 日本一の串かつ 横綱 法善寺店 2016 (27351279425).jpg", "kushikatsu skewers plate"]),
    ("f-tsurukame.jpg", ["doteyaki Osaka", "土手焼き"]),
    # ---- 大阪烧 ----
    ("f-mizuno.jpg", ["okonomiyaki Osaka Dotonbori", "お好み焼き 大阪"]),
    ("f-chibo.jpg", ["FILE:File:Okonomiyaki Chibo Sennichimae.jpg", "Chibo okonomiyaki"]),
    ("f-bonkura.jpg", ["okonomiyaki teppan grill", "modan yaki okonomiyaki"]),
    # ---- 章鱼烧 ----
    ("f-otako.jpg", ["takoyaki Osaka", "たこ焼き 大阪"]),
    ("f-takohachi.jpg", ["takoyaki Dotonbori", "takoyaki boat Osaka"]),
    # ---- 拉面 ----
    ("f-jojoro.jpg", ["FILE:File:Chuka soba of Bariuma.jpg", "chuka soba ramen bowl"]),
    ("f-kinryu.jpg", ["Kinryu ramen Dotonbori", "ramen Dotonbori Osaka"]),
    ("f-kamikura.jpg", ["FILE:File:Shoyu Ramen.jpg", "shoyu ramen chashu bowl"]),
    ("f-kamukura.jpg", ["FILE:File:どうとんぼり神座中野サンモール店おいしいラーメン20240828-P1056716.jpg", "Kamukura ramen", "ramen with cabbage"]),
    # ---- 咖喱 · 洋食 · 海鲜 ----
    ("f-jiyuuken.jpg", ["curry rice Osaka", "curry and rice Japanese"]),
    ("f-ginpei.jpg", ["taimeshi", "grilled fish Japanese set meal"]),
    # ---- 甜品 ----
    ("f-tamasei.jpg", ["warabimochi", "蕨餅 きな粉"]),
    ("f-rikuro.jpg", ["cheesecake Japanese", "cheesecake whole round"]),
    ("f-alshon.jpg", ["mont blanc cake", "afternoon tea cake set"]),
    # ---- 京都 ----
    ("f-okaru.jpg", ["curry udon Osaka", "oyakodon Japanese"]),
    ("f-matsuba.jpg", ["nishin soba", "soba Kyoto bowl"]),
    # ---- 奈良 · 神户 ----
    ("f-kamabashi.jpg", ["udon Nara", "kake udon bowl"]),
    ("f-ishida.jpg", ["Kobe beef teppanyaki", "Kobe beef steak"]),
    ("f-amona.jpg", ["hamburg steak yoshoku", "yoshoku plate Japanese"]),
]

# ---- 第二批：复查后新增的「高评分」店（2026-09 食べログ 榜单核实） ----
NEW_TARGETS = [
    ("f-mutetteppou.jpg", ["tonkotsu ramen bowl", "豚骨ラーメン"]),
    ("f-chitose-okonomi.jpg", ["FILE:File:Okonomiyaki osaka.jpg", "okonomiyaki"]),
    ("f-tenpumori.jpg", ["kake udon", "かけうどん"]),
    ("f-kankan.jpg", ["takoyaki plate Osaka", "たこ焼き 皿"]),
    ("f-yaei.jpg", ["kushikatsu skewers", "串カツ 盛り合わせ 大阪"]),
    ("f-yako.jpg", ["FILE:File:Kushikatsu (3603151166).jpg", "kushikatsu plate"]),
    ("f-rokkakuto.jpg", ["FILE:File:Kushikatsu.Tengu.JPG", "kushikatsu tray"]),
    ("f-fujii.jpg", ["FILE:File:Ramen and Chahan 003.jpg", "ramen and fried rice"]),
    ("f-ichiran.jpg", ["Ichiran ramen", "一蘭 ラーメン"]),
    ("f-yamamotomenzo.jpg", ["kamaage udon", "釜揚げうどん"]),
    ("f-patisserie-s.jpg", ["macaron assortment", "マカロン"]),
    ("f-kitada.jpg", ["shio ramen bowl", "塩ラーメン"]),
    ("f-manbo.jpg", ["FILE:File:Okonomiyaki Osaka 2.JPG", "okonomiyaki"]),
    ("f-sennariya.jpg", ["kissaten coffee set", "モーニング 喫茶店"]),
    ("f-fukutaro.jpg", ["negiyaki", "ねぎ焼き 大阪"]),
    ("f-chitose-udon.jpg", ["udon set meal", "うどん定食"]),
    ("f-hashimotoya.jpg", ["curry rice Japanese plate", "カレーライス"]),
    ("f-gen-nara.jpg", ["FILE:File:Zaru soba by spinachdip.jpg", "zaru soba"]),
    ("f-menya-k.jpg", ["ramen bowl chashu egg", "ラーメン チャーシュー"]),
    ("f-nakatanido.jpg", ["yomogi mochi", "よもぎ餅 草餅"]),
    ("f-kashiya.jpg", ["wagashi Japanese sweets", "和菓子 上生菓子"]),
    ("f-asahi-yoshoku.jpg", ["FILE:File:Omurice with Demi-glace Sause in Osaka, Japan.jpg", "omurice Osaka"]),
    ("f-plaisir.jpg", ["FILE:File:Beef steak of the set of dinner.jpg", "beef steak plate"]),
    ("f-gyoza-daigaku.jpg", ["gyoza dumplings plate", "餃子 焼き餃子"]),
    ("f-montplus.jpg", ["shortcake strawberry cake", "ショートケーキ"]),
    ("f-camarche.jpg", ["FILE:File:Fresh made bread 05.jpg", "bread loaves"]),
    ("f-551horai.jpg", ["nikuman pork bun", "豚まん 551"]),
]


NEW_TARGETS += [
    ("f-shizuku.jpg", ["FILE:File:Ichigo daifuku 001.jpg", "fruit daifuku"]),
    ("f-lepremier.jpg", ["FILE:File:Manual drip (pour-over) coffee.jpg", "pour over coffee"]),
    ("f-ashishima.jpg", ["FILE:File:Time for coffee (34297193823).jpg", "coffee cup cafe"]),
    ("f-madras.jpg", ["FILE:File:Katsu-curry 003.jpg", "katsu curry"]),
    ("f-nijinohotoke.jpg", ["FILE:File:咖哩飯 (17843819380).jpg", "curry rice plate"]),
    ("f-savoy.jpg", ["FILE:File:Japanese curry rice with shredded beef by Banej in Singapore.jpg", "japanese curry rice"]),
    ("f-temmatsu.jpg", ["FILE:File:Beef Udon - Pompoko.jpg", "beef udon"]),
    ("f-tsukumo.jpg", ["FILE:File:Kitsune Udon in Hiroshima.jpg", "kitsune udon"]),
    ("f-kobayashi.jpg", ["FILE:File:Juwari Soba (8067612263).jpg", "juwari soba"]),
    ("f-biensur.jpg", ["FILE:File:Japanese Milk Bread.jpg", "shokupan milk bread"]),
    ("f-menshiro.jpg", ["FILE:File:Shoyu Ramen.jpg", "shoyu ramen"]),
    ("f-inoichi.jpg", ["FILE:File:Shio ramen from Ryukyu Ramen Tondou, Shin-Yokohama.jpg", "shio ramen"]),
]

# ---- 早餐 · 本地日常 · 非面类特色（2026-09 追加）----
BREAKFAST_TARGETS = [
    ("f-konbini.jpg", ["Japanese convenience store interior", "7-Eleven Japan shop front", "convenience store rice ball shelf"]),
    ("f-onakasuita.jpg", ["onigiri rice ball nori", "Japanese rice ball plate", "omusubi"]),
    ("f-ciaopresso.jpg", ["breakfast set toast coffee Japan", "cafe morning set toast", "toast and coffee cafe"]),
    ("f-daikichi-tenpura.jpg", ["tendon tempura rice bowl", "tempura donburi shrimp", "tenpura bowl"]),
    ("f-okutan.jpg", ["FILE:File:Yudofu of Kyoto.jpg", "yudofu", "tofu hot pot Kyoto restaurant"]),
    ("f-isose.jpg", ["FILE:File:Obanzai by jetalone in Kyoto.jpg", "obanzai", "Japanese home style dishes assortment"]),
    ("f-woodbakers.jpg", ["FILE:File:Donuts of a bakery in Japan.jpg", "donuts Japan bakery", "Japanese bakery bread display"]),
    ("f-tsukihiboshi.jpg", ["FILE:File:Chagayu.jpg", "chagayu", "rice porridge Japanese"]),
    ("f-tanaka-kakinoha.jpg", ["kakinoha sushi persimmon leaf", "saba sushi Nara", "oshizushi wrapped leaf"]),
    ("f-ushisuji-taku.jpg", ["beef tendon stew Japanese", "gyusuji nikomi", "doteyaki beef tendon"]),
]
NEW_TARGETS += BREAKFAST_TARGETS
TARGETS = TARGETS + NEW_TARGETS

BAD_TITLE = re.compile(r"(map|plan|diagram|logo|sign|chart|graph|banknote|stamp|screenshot|pdf|poster|menu|bill)", re.I)


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
            time.sleep(4.5)
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(8.0 * (attempt + 1))
    raise last


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def shrink(path, max_w=900, quality=82):
    """Keep the repo light: covers are only displayed at <=700px wide."""
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001
        return
    try:
        im = Image.open(path).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        im.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    except Exception as e:  # noqa: BLE001
        print(f"WARN  shrink {path}: {e}", file=sys.stderr)


def pick(query):
    data = api({
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6",
        "gsrlimit": "12",
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": "1200",
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
        if w < 900 or h < 600:
            continue
        if h / max(w, 1) > 1.35:
            continue
        cands.append((title, ii))
    return cands


def main():
    os.makedirs(OUT, exist_ok=True)
    cpath = os.path.join(OUT, "credits.json")
    credits = json.load(open(cpath, encoding="utf-8")) if os.path.exists(cpath) else {}
    only = sys.argv[1:] or None
    for fname, queries in TARGETS:
        if only and fname not in only:
            continue
        dest = os.path.join(OUT, fname)
        if os.path.exists(dest) and fname in credits:
            print(f"skip  {fname} (exists)")
            continue
        chosen = None
        for q in queries:
            try:
                if q.startswith("FILE:"):
                    title = q[5:]
                    d = api({"action": "query", "titles": title, "prop": "imageinfo",
                             "iiprop": "url|size|extmetadata", "iiurlwidth": "1200"})
                    pg = list((d.get("query") or {}).get("pages", {}).values())[0]
                    ii = (pg.get("imageinfo") or [{}])[0]
                    cands = [(pg.get("title", title), ii)] if ii.get("thumburl") or ii.get("url") else []
                else:
                    cands = pick(q)
            except Exception as e:  # noqa: BLE001
                print(f"ERR   {fname} query={q}: {e}", file=sys.stderr)
                continue
            if cands:
                chosen = cands[0]
                print(f"cands {fname} <- '{q}': " + " | ".join(c[0] for c in cands[:4]), flush=True)
                break
        if not chosen:
            print(f"MISS  {fname}: no candidate", flush=True)
            continue
        title, ii = chosen
        em = ii.get("extmetadata") or {}
        url = ii.get("thumburl") or ii.get("url")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                f.write(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"ERR   download {fname}: {e}", file=sys.stderr)
            continue
        shrink(dest)
        credits[fname] = {
            "title": title,
            "author": strip_html((em.get("Artist") or {}).get("value", "")),
            "license": strip_html((em.get("LicenseShortName") or {}).get("value", "")),
            "page": ii.get("descriptionurl", ""),
            "bytes": os.path.getsize(dest),
        }
        print(f"OK    {fname} <- {title} [{credits[fname]['license']}] {os.path.getsize(dest)//1024}KB", flush=True)
    json.dump(credits, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", cpath, len(credits), "entries")


if __name__ == "__main__":
    main()
