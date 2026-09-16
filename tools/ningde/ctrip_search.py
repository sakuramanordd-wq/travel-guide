#!/usr/bin/env python3
"""Ctrip (携程) globalsearch REST API — find hotels by keyword, dump compact JSON.

Usage:
  python3 tools/ningde/ctrip_search.py "宁德酒店"            # default: type=hotel
  python3 tools/ningde/ctrip_search.py "霞浦 民宿" all
  python3 tools/ningde/ctrip_search.py "福鼎酒店" hotel --raw   # keep raw json

API (mobile H5, no login):
  https://m.ctrip.com/restapi/h5api/globalsearch/search
      ?action=gsonline&source=globalonline&keyword=<kw>&type=all|hotel&t=1

Response items carry: id, word (hotel name), zoneName, locationName, address,
starRating, commentScore (5 分制), commentCount, price ("￥297起" 参考价),
imageUrl, lat/lon. Cache: research/_raw/cache/ctripsearch_<kw>.json
"""
import json, os, re, sys, urllib.parse, subprocess, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(ROOT, "research", "_raw", "cache")
os.makedirs(CACHE, exist_ok=True)

UA_M = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

API = ("https://m.ctrip.com/restapi/h5api/globalsearch/search"
       "?action=gsonline&source=globalonline&keyword={kw}&type={t}&t=1")


def fetch(kw, t="hotel", force=False):
    key = hashlib.md5(f"{kw}|{t}".encode()).hexdigest()[:10]
    cf = os.path.join(CACHE, f"ctripsearch_{key}.json")
    if os.path.exists(cf) and not force and os.path.getsize(cf) > 200:
        return open(cf, encoding="utf-8").read()
    url = API.format(kw=urllib.parse.quote(kw), t=t)
    raw = subprocess.run(["curl", "-sS", "-m", "40", "-L", "-A", UA_M,
                          "-H", "Accept-Language: zh-CN,zh;q=0.9", url],
                         capture_output=True).stdout.decode("utf-8", "ignore")
    open(cf, "w", encoding="utf-8").write(raw)
    with open(os.path.join(CACHE, "ctripsearch_queries.txt"), "a", encoding="utf-8") as f:
        f.write(f"{kw}\t{t}\t{url}\n")
    return raw


def compact(raw):
    try:
        j = json.loads(raw)
    except Exception:
        return {"error": "not json", "head": raw[:200]}
    out = []
    for it in (j.get("data") or []):
        if it.get("type") != "hotel":
            continue
        out.append({
            "id": it.get("id"), "name": it.get("word"),
            "zone": it.get("zoneName"), "area": it.get("locationName"),
            "addr": it.get("address"), "star": it.get("starRating"),
            "score": it.get("commentScore"), "reviews": it.get("commentCount"),
            "price_from": it.get("price"), "img": it.get("imageUrl"),
            "lat": it.get("lat"), "lon": it.get("lon"),
            "city": it.get("cityName"), "cityId": it.get("cityId"),
            "url": (it.get("url") or "").replace("http://", "https://"),
        })
    return {"count": len(out), "hotels": out, "raw_total": len(j.get("data") or [])}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    kw = args[0]
    t = args[1] if len(args) > 1 else "hotel"
    force = "--raw" in sys.argv
    raw = fetch(kw, t, force)
    if "--json" in sys.argv:
        print(raw[:8000])
    else:
        d = compact(raw)
        print(json.dumps(d, ensure_ascii=False, indent=1))
