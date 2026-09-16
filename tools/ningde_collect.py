#!/usr/bin/env python3
"""Collect 12306 schedules+prices+stops for all Ningde-corridor ODs.
Writes one JSON per OD into research/_raw/ningde/.
"""
import subprocess, json, urllib.parse, os, time, re, sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"
ROOT = os.path.join(os.path.dirname(__file__), "..")
CK = os.path.join(ROOT, "research", "_raw", "ningde", ".ck.txt")
OUT = os.path.join(ROOT, "research", "_raw", "ningde")
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-09-29"


def get(u, ref="https://kyfw.12306.cn/otn/leftTicket/init"):
    p = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, "-b", CK, "-c", CK,
                        "-H", "Referer: " + ref, "-H", "X-Requested-With: XMLHttpRequest",
                        "--compressed", u], capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except Exception:
        return None


def left(frm, to, date):
    u = ("https://kyfw.12306.cn/otn/leftTicket/queryG"
         f"?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={frm}"
         f"&leftTicketDTO.to_station={to}&purpose_codes=ADULT")
    j = get(u)
    if not j or not j.get("data"):
        return None
    smap = j["data"].get("map", {})
    rows = []
    for enc in j["data"].get("result", []):
        f = urllib.parse.unquote(enc).split("|")
        if len(f) < 40:
            continue
        rows.append(dict(code=f[3], sale_hint=f[1], train_no=f[2],
                         from_code=f[6], to_code=f[7], dep=f[8], arr=f[9], dur=f[10],
                         buy=f[11], date=f[13], from_no=f[16], to_no=f[17],
                         seat_types=f[35], from_name=smap.get(f[6], f[6]), to_name=smap.get(f[7], f[7]),
                         start=smap.get(f[4], f[4]), end=smap.get(f[5], f[5])))
    return rows


def price(train_no, fno, tno, seat_types, date):
    u = ("https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice"
         f"?train_no={train_no}&from_station_no={fno}&to_station_no={tno}"
         f"&seat_types={seat_types}&train_date={date}")
    j = get(u)
    if not j or not j.get("data"):
        return {}
    d = j["data"]
    return {k: v for k, v in d.items() if k not in ("OT", "train_no")}


def stops(train_no, frm, to, date):
    u = ("https://kyfw.12306.cn/otn/czxx/queryByTrainNo"
         f"?train_no={train_no}&from_station_telecode={frm}"
         f"&to_station_telecode={to}&depart_date={date}")
    j = get(u)
    if not j or not j.get("data"):
        return []
    return [{"station": s.get("station_name"), "arr": s.get("arrive_time"),
             "dep": s.get("start_time"), "no": s.get("station_no")}
            for s in j["data"].get("data", [])]


ODS = [
    ("HGH", "NES"), ("HVU", "NES"), ("XHH", "NES"),
    ("HGH", "XOS"), ("HVU", "XOS"),
    ("HGH", "TLS"), ("HVU", "TLS"), ("XHH", "TLS"),
    ("HGH", "FES"), ("HVU", "FES"),
    ("NES", "HGH"), ("NES", "HVU"),
    ("XOS", "HGH"), ("XOS", "HVU"),
    ("TLS", "HGH"), ("TLS", "HVU"),
    ("FES", "HGH"), ("FES", "HVU"),
    ("NES", "XOS"), ("NES", "TLS"), ("NES", "FES"),
    ("XOS", "TLS"), ("TLS", "FES"),
]

summary = {}
for frm, to in ODS:
    fn = os.path.join(OUT, f"12306_{frm}-{to}_{DATE}.json")
    rows = left(frm, to, DATE)
    if rows is None:
        print(f"{frm}->{to}: NO DATA"); summary.setdefault("nodata", []).append(f"{frm}->{to}")
        continue
    for r in rows:
        r["price"] = price(r["train_no"], r["from_no"], r["to_no"], r["seat_types"], DATE)
        time.sleep(0.25)
    json.dump({"date": DATE, "from": frm, "to": to, "rows": rows},
              open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    summary[f"{frm}->{to}"] = len(rows)
    print(f"{frm}->{to}: {len(rows)} trains", flush=True)

# stop lists for every unique train seen (full runs)
seen = {}
for frm, to in ODS:
    fn = os.path.join(OUT, f"12306_{frm}-{to}_{DATE}.json")
    if not os.path.exists(fn):
        continue
    for r in json.load(open(fn, encoding="utf-8"))["rows"]:
        seen.setdefault(r["train_no"], r["code"])
allstops = {}
for tn, code in seen.items():
    st = stops(tn, "HGH", "NES", DATE)
    if not st:
        st = stops(tn, "NES", "HGH", DATE)
    allstops[code] = st
    time.sleep(0.25)
json.dump(allstops, open(os.path.join(OUT, f"stops_{DATE}.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("stops for", len(allstops), "trains")
json.dump(summary, open(os.path.join(OUT, f"summary_{DATE}.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
