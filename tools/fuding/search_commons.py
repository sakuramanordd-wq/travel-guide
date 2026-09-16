#!/usr/bin/env python3
"""Ad-hoc Commons search helper: print candidate files for each query.

Run: python3 tools/fuding/search_commons.py "query1" "query2" ...
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "travel-guide-builder/1.0 (personal travel guide; contact: local)"


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


def search(query, limit=10):
    data = api({"action": "query", "generator": "search",
                "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": "6",
                "gsrlimit": str(limit), "prop": "imageinfo",
                "iiprop": "url|size|extmetadata"})
    pages = list((data.get("query") or {}).get("pages", {}).values())
    pages.sort(key=lambda p: p.get("index", 99))
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        em = ii.get("extmetadata") or {}
        lic = strip_html((em.get("LicenseShortName") or {}).get("value", "?"))
        w, h = ii.get("width", 0), ii.get("height", 0)
        desc = strip_html((em.get("ImageDescription") or {}).get("value", ""))[:110]
        print(f"  {p.get('title')}  [{w}x{h}] [{lic}]")
        if desc:
            print(f"      desc: {desc}")


if __name__ == "__main__":
    for q in sys.argv[1:]:
        print(f"== {q} ==")
        try:
            search(q)
        except Exception as e:  # noqa: BLE001
            print(f"  ERR {e}")
        print()
