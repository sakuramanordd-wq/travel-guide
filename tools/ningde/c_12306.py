#!/usr/bin/env python3
"""c_12306.py FROM TO DATE  -> save research/_raw/ningde/c-12306-<FROM>-<TO>-<DATE>.json
Uses cookie file research/_raw/ningde/.ck.txt """
import sys, os, json, ssl, urllib.request, urllib.parse, http.cookiejar

BASE = "/home/hukun02/Project/travel-guide/research/_raw/ningde"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

def load_cookie():
    p = os.path.join(BASE, ".ck.txt")
    jar = http.cookiejar.MozillaCookieJar(p)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as e:
        print("cookie load warn", e)
    return jar

def get(url, jar):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar),
                                    urllib.request.HTTPSHandler(context=CTX))
    with op.open(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

IDX = ["secretStr","备注","备注2","train_no","车次","始发站码","终到站码","出发站码","到达站码",
       "出发时刻","到达时刻","历时","可购","出发日期","","","","","","","","","","","","",
       "","","","","","","","", "软卧","软座","特等座","无座","硬卧","硬座","二等座","一等座",
       "商务座","动卧","","","","","","","","","","","席别","可改签","可候补"]

def parse(row):
    p = row.split("|")
    d = {}
    for i, name in enumerate(IDX):
        if name and i < len(p):
            d[name] = p[i]
    # 33.. : index 32 是软卧
    d["软卧"] = p[32] if len(p) > 32 else ""
    d["软座"] = p[33] if len(p) > 33 else ""
    d["特等座"] = p[34] if len(p) > 34 else ""
    d["无座"] = p[35] if len(p) > 35 else ""
    d["硬卧"] = p[36] if len(p) > 36 else ""
    d["硬座"] = p[37] if len(p) > 37 else ""
    d["二等座"] = p[30] if len(p) > 30 else ""
    d["一等座"] = p[31] if len(p) > 31 else ""
    d["商务座"] = p[32] if len(p) > 32 else ""
    return d

def main():
    frm, to, date = sys.argv[1], sys.argv[2], sys.argv[3]
    jar = load_cookie()
    url = ("https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date=%s"
           "&leftTicketDTO.from_station=%s&leftTicketDTO.to_station=%s&purpose_codes=ADULT"
           % (date, frm, to))
    try:
        txt = get(url, jar)
    except Exception as e:
        print("ERR", type(e).__name__, e); return 1
    try:
        j = json.loads(txt)
    except Exception:
        print("NONJSON:", txt[:500]); return 1
    if not j.get("data"):
        print("NODATA:", json.dumps(j, ensure_ascii=False)[:500]); return 1
    res = j["data"].get("result") or []
    rows = [parse(r) for r in res]
    out = {"http": 200, "date": date, "from": frm, "to": to, "count": len(rows), "rows": rows,
           "map": j["data"].get("map", {})}
    p = os.path.join(BASE, "c-12306-%s-%s-%s.json" % (frm, to, date))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("SAVED", p, len(rows), "trains")
    for r in rows:
        print(r.get("车次"), r.get("出发时刻"), "->", r.get("到达时刻"), r.get("历时"),
              "| 出发站", r.get("出发站码"), "到达站", r.get("到达站码"),
              "| 二等", r.get("二等座"), "一等", r.get("一等座"), "无座", r.get("无座"))
    return 0

sys.exit(main())
