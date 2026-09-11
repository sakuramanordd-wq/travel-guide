#!/usr/bin/env python3
"""Fetch freely-licensed photos from Wikimedia Commons for the Osaka/Kansai guide.

Writes images/*.jpg plus images/credits.json (title, author, license, source page).
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
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")

# target filename -> list of Commons search queries (first hit wins)
TARGETS = [
    ("hero-osaka.jpg", ["Osaka Castle keep autumn", "Osaka Castle Tenshu"]),
    ("osaka-castle.jpg", ["Osaka Castle park moat", "Osaka castle main tower"]),
    ("dotonbori.jpg", ["Dotonbori at night Osaka", "Dotonbori Ebisubashi night"]),
    ("tsutenkaku.jpg", ["Tsutenkaku Shinsekai", "Shinsekai Osaka Tsutenkaku"]),
    ("umeda-sky.jpg", ["Umeda Sky Building", "Umeda Sky Building night"]),
    ("kuromon.jpg", ["FILE:File:黒門市場 2024(1).jpg", "黒門市場"]),
    ("tenjinbashisuji.jpg", ["Tenjinbashisuji shopping street", "Tenjimbashisuji shotengai"]),
    ("osaka-tenmangu.jpg", ["Osaka Tenmangu shrine", "Osaka Tenmangu"]),
    ("nakanoshima.jpg", ["Osaka City Central Public Hall", "Nakanoshima Osaka city hall"]),
    ("kaiyukan.jpg", ["FILE:File:Osaka Aquarium Kaiyukan 2022-04-24.jpg"]),
    ("kiyomizu.jpg", ["Kiyomizu-dera autumn", "Kiyomizu temple Kyoto"]),
    ("fushimi-inari.jpg", ["Fushimi Inari senbon torii", "Fushimi Inari Taisha torii"]),
    ("arashiyama.jpg", ["Arashiyama bamboo grove", "Sagano bamboo forest"]),
    ("nara-deer.jpg", ["Nara deer Todai-ji", "Sika deer Nara Park"]),
    ("himeji.jpg", ["Himeji Castle", "Himeji castle keep"]),
    ("kobe.jpg", ["Kobe Port Tower night", "Kobe harborland night"]),
    ("uji.jpg", ["Byodo-in Uji Phoenix Hall", "Byodoin temple Uji"]),
    ("minoo.jpg", ["Minoo Falls Osaka", "Mino waterfall Osaka"]),
    ("koyasan.jpg", ["FILE:File:Okuno-in - Okonuin572.jpg"]),
    ("usj.jpg", ["FILE:File:Universal Studios Japan parade 2.jpg"]),
]

BAD_TITLE = re.compile(r"(map|plan|diagram|logo|sign|chart|graph|banknote|stamp|screenshot)", re.I)


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
            time.sleep(3.0)
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(6.0 * (attempt + 1))
    raise last


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def pick(query):
    data = api({
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6",
        "gsrlimit": "12",
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
        if w < 1200 or h < 700:
            continue
        if h / max(w, 1) > 1.25:
            continue
        cands.append((title, ii))
    return cands


def main():
    os.makedirs(OUT, exist_ok=True)
    credits = {}
    cpath = os.path.join(OUT, "credits.json")
    if os.path.exists(cpath):
        credits = json.load(open(cpath, encoding="utf-8"))
    for fname, queries in TARGETS:
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
                             "iiprop": "url|size|extmetadata", "iiurlwidth": "1400"})
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
                print(f"cands {fname} <- '{q}': " + " | ".join(c[0] for c in cands[:4]))
                break
        if not chosen:
            print(f"MISS  {fname}: no candidate")
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
        credits[fname] = {
            "title": title,
            "author": strip_html((em.get("Artist") or {}).get("value", "")),
            "license": strip_html((em.get("LicenseShortName") or {}).get("value", "")),
            "page": ii.get("descriptionurl", ""),
            "bytes": os.path.getsize(dest),
        }
        print(f"OK    {fname} <- {title} [{credits[fname]['license']}] {os.path.getsize(dest)//1024}KB")
    json.dump(credits, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", cpath, len(credits), "entries")


if __name__ == "__main__":
    main()
