#!/usr/bin/env python3
"""12306 leftTicket query + parser, for Ningde research.

Usage:
  python3 tools/ningde_trains.py OD HGH NES 2026-09-29 [outfile.json]
  python3 tools/ningde_trains.py stops 240000G12340 HGH NES 2026-09-29
  python3 tools/ningde_trains.py query HGH NES 2026-09-29      # print table
"""
import sys, os, re, json, time, gzip, ssl, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
COOKIE_FILE = os.path.join(os.path.dirname(__file__), "..", "research", "_raw", "ningde", ".ck.txt")


def _jar():
    ck = {}
    try:
        for line in open(COOKIE_FILE, encoding="utf-8"):
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) >= 7:
                ck[p[5]] = p[6]
    except FileNotFoundError:
        pass
    return ck


def get(url, referer="https://kyfw.12306.cn/otn/leftTicket/init"):
    """Use curl: kyfw rejects the urllib request shape."""
    import subprocess
    cmd = ["curl", "-s", "-m", "30", "-A", UA, "-b", COOKIE_FILE, "-c", COOKIE_FILE,
           "-H", "Referer: " + referer,
           "-H", "X-Requested-With: XMLHttpRequest",
           "-H", "Accept: application/json, text/javascript, */*; q=0.01",
           "--compressed", "-w", "\n@@HTTP:%{http_code}", url]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    except Exception as e:
        return 0, ""
    body = p.stdout
    code = 0
    m = re.search(r"\n@@HTTP:(\d+)$", body)
    if m:
        code = int(m.group(1)); body = body[:m.start()]
    return code, body


# field index -> label (12306 leftTicket result pipe format)
F = {
    0: "secretStr", 2: "train_no", 3: "车次", 4: "始发站码", 5: "终到站码",
    6: "出发站码", 7: "到达站码", 8: "出发时刻", 9: "到达时刻", 10: "历时",
    11: "可购", 13: "出发日期", 23: "软卧", 24: "软座", 25: "特等座",
    26: "无座", 28: "硬卧", 29: "硬座", 30: "二等座", 31: "一等座", 32: "商务座",
    33: "动卧", 35: "席别", 36: "可改签", 37: "可候补",
}


def query(frm, to, date):
    url = ("https://kyfw.12306.cn/otn/leftTicket/queryG"
           f"?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={frm}"
           f"&leftTicketDTO.to_station={to}&purpose_codes=ADULT")
    st, body = get(url)
    if st != 200 or not body.strip():
        return {"http": st, "error": "empty/redirect", "rows": []}
    try:
        j = json.loads(body)
    except Exception:
        return {"http": st, "error": "not json", "raw": body[:500], "rows": []}
    if not j.get("data"):
        return {"http": st, "error": "no data", "raw": body[:500], "rows": []}
    smap = j["data"].get("map", {})
    rows = []
    for enc in j["data"].get("result", []):
        f = urllib.parse.unquote(enc).split("|")
        if len(f) < 36:
            continue
        r = {}
        for i, lbl in F.items():
            r[lbl] = f[i] if i < len(f) else ""
        r["出发站"] = smap.get(r["出发站码"], r["出发站码"])
        r["到达站"] = smap.get(r["到达站码"], r["到达站码"])
        r["始发站"] = smap.get(r["始发站码"], r["始发站码"])
        r["终到站"] = smap.get(r["终到站码"], r["终到站码"])
        rows.append(r)
    return {"http": st, "date": date, "from": frm, "to": to, "count": len(rows), "rows": rows}


def stops(train_no, frm, to, date):
    url = ("https://kyfw.12306.cn/otn/czxx/queryByTrainNo"
           f"?train_no={train_no}&from_station_telecode={frm}"
           f"&to_station_telecode={to}&depart_date={date}")
    st, body = get(url, referer="https://kyfw.12306.cn/otn/leftTicket/init")
    try:
        j = json.loads(body)
        return j.get("data", {}).get("data", [])
    except Exception:
        return []


def table(res, show_seats=True):
    out = []
    hdr = ("车次", "出发站", "出发", "到达", "到达站", "历时", "二等座", "一等座", "商务座", "无座", "train_no")
    out.append(" | ".join(hdr))
    for r in res["rows"]:
        out.append(" | ".join(str(x) for x in (
            r["车次"], r["出发站"], r["出发时刻"], r["到达时刻"], r["到达站"], r["历时"],
            r["二等座"], r["一等座"], r["商务座"], r["无座"], r["train_no"])))
    return "\n".join(out)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "query":
        frm, to, date = sys.argv[2], sys.argv[3], sys.argv[4]
        res = query(frm, to, date)
        print(json.dumps({k: v for k, v in res.items() if k != "rows"}, ensure_ascii=False))
        print(table(res))
        if len(sys.argv) > 5:
            open(sys.argv[5], "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    elif mode == "stops":
        tn, frm, to, date = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        for s in stops(tn, frm, to, date):
            print(" | ".join(str(s.get(k, "")) for k in
                             ("station_name", "arrive_time", "start_time", "stopover_time", "station_no")))
    elif mode == "json":
        frm, to, date = sys.argv[2], sys.argv[3], sys.argv[4]
        res = query(frm, to, date)
        res["_stops"] = {}
        for r in res["rows"]:
            res["_stops"][r["车次"]] = stops(r["train_no"], r["出发站码"], r["到达站码"], date)
            time.sleep(0.4)
        open(sys.argv[5], "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
        print("wrote", sys.argv[5], res.get("count"))
