#!/usr/bin/env python3
"""Fetch a Ctrip (携程) PC hotel-list page and decode the server-rendered hotel cards.

The modern list page (https://hotels.ctrip.com/hotels/list?city=...) ships its first
page of results inside the React-Server-Components payload (self.__next_f.push([1,"..."])).
This script decodes that payload and prints one JSON object per hotel card:
  hotelId, name, enName, star, commentScore, commentDesc, commentNum, positionDesc,
  address, zoneNames, lat/lon, room names + bed + tags(免费取消 etc.), ad flag.
Prices are NOT in the payload (Ctrip hides them behind login on PC); use
tools/trip_price.py (trip.com) for CNY prices, or the globalsearch API for 起价.

Usage:
  python3 tools/ctrip_list.py "https://hotels.ctrip.com/hotels/list?city=20980" [--dump FILE]
  python3 tools/ctrip_list.py --city 20980 --option "北岐滩涂" --in 2026-10-01 --out 2026-10-02
"""
import re, sys, json, os, ssl, gzip, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
HERE = os.path.dirname(os.path.abspath(__file__))
RAWDIR = os.path.normpath(os.path.join(HERE, "..", "research", "_raw", "ningde"))


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
        raw = r.read()
        if "gzip" in r.headers.get("Content-Encoding", ""):
            raw = gzip.decompress(raw)
    return raw.decode("utf-8", "ignore")


def decode_payload(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\]\)', html)
    return "".join(json.loads(c) for c in chunks)


def brace_json(s, start):
    """s[start] must be '[' or '{'; return the balanced JSON substring."""
    op = s[start]; cl = "]" if op == "[" else "}"
    depth = 0; i = start; instr = False; esc = False
    while i < len(s):
        ch = s[i]
        if instr:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': instr = False
        else:
            if ch == '"': instr = True
            elif ch == op: depth += 1
            elif ch == cl:
                depth -= 1
                if depth == 0: return s[start:i+1]
        i += 1
    return None


def cards(payload):
    i = payload.find('"hotelList":[')
    if i < 0: return []
    blob = brace_json(payload, i + len('"hotelList":'))
    if not blob: return []
    try:
        arr = json.loads(blob)
    except Exception:
        return []
    out = []
    for h in arr:
        hi = h.get("hotelInfo", {})
        name = (hi.get("nameInfo") or {}).get("name")
        if not name: continue
        ci = hi.get("commentInfo") or {}
        pos = hi.get("positionInfo") or {}
        mc = (pos.get("mapCoordinate") or [{}])[0]
        rooms = []
        for r in h.get("roomInfo", []) or []:
            s = r.get("summary") or {}
            tags = [t.get("tagTitle") for t in ((r.get("roomTags") or {}).get("advantageTags") or [])]
            bed = "、".join(((r.get("bedInfo") or {}).get("contentList") or [])[:1])
            g = r.get("guestInfo") or {}
            rooms.append({"room": s.get("saleRoomName"), "bed": bed,
                          "adults": g.get("adultCount"), "tags": tags,
                          "qty": s.get("roomQuantity")})
        out.append({
            "hotelId": (hi.get("summary") or {}).get("hotelId"),
            "name": name,
            "enName": (hi.get("nameInfo") or {}).get("enName"),
            "diamond": (hi.get("hotelStar") or {}).get("star"),
            "category": (hi.get("hotelCategory") or {}).get("categoryName"),
            "score": ci.get("commentScore"), "scoreDesc": ci.get("commentDescription"),
            "reviews": ci.get("commenterNumber"),
            "subScore": {x["content"]: x["number"] for x in (ci.get("subScore") or [])},
            "oneLine": [t.get("tagTitle") for t in (ci.get("oneSentenceComment") or [])],
            "positionDesc": pos.get("positionDesc"), "address": pos.get("address"),
            "zone": pos.get("zoneNames"), "lat": mc.get("latitude"), "lon": mc.get("longitude"),
            "isAd": (hi.get("advertiseInfo") or {}).get("isAdHotel"),
            "rooms": rooms,
        })
    return out


def main():
    args = sys.argv[1:]
    dump = None
    if "--dump" in args:
        i = args.index("--dump"); dump = args[i+1]; args = args[:i] + args[i+2:]
    city = option = ci = co = None
    if "--city" in args:
        i = args.index("--city"); city = args[i+1]; args = args[:i] + args[i+2:]
    if "--option" in args:
        i = args.index("--option"); option = args[i+1]; args = args[:i] + args[i+2:]
    if "--in" in args:
        i = args.index("--in"); ci = args[i+1]; args = args[:i] + args[i+2:]
    if "--out" in args:
        i = args.index("--out"); co = args[i+1]; args = args[:i] + args[i+2:]
    if args and args[0].startswith("http"):
        url = args[0]
    else:
        q = {"city": city}
        if option:
            q.update({"optionName": option, "display": option, "directSearch": "1"})
        if ci: q["checkin"] = ci
        if co: q["checkout"] = co
        url = "https://hotels.ctrip.com/hotels/list?" + urllib.parse.urlencode(q)
    html = get(url)
    if dump:
        os.makedirs(os.path.dirname(dump) or ".", exist_ok=True)
        open(dump, "w", encoding="utf-8").write(html)
    payload = decode_payload(html)
    cs = cards(payload)
    m = re.search(r"<title>([^<]*)</title>", html)
    print(json.dumps({"url": url, "title": m.group(1) if m else None,
                      "n_cards": len(cs), "hotels": cs}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
