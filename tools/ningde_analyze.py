#!/usr/bin/env python3
"""Analyze collected 12306 JSON -> printable tables for the Ningde report."""
import json, os, collections, sys

RAW = os.path.join(os.path.dirname(__file__), "..", "research", "_raw", "ningde")
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-09-29"


def load(od):
    p = os.path.join(RAW, f"12306_{od}_{DATE}.json")
    if not os.path.exists(p):
        return []
    return json.load(open(p, encoding="utf-8"))["rows"]


def seat(pr):
    """O=二等座, M=一等座, A9/9=商务座, A1/1=硬座, A3/3=硬卧, A4/4=软卧."""
    m = {"二等座": pr.get("O"), "一等座": pr.get("M"), "商务座": pr.get("A9") or pr.get("9"),
         "硬座": pr.get("A1"), "硬卧": pr.get("A3"), "软卧": pr.get("A4"), "无座": pr.get("WZ")}
    return m


def show(od, label):
    rows = load(od)
    print(f"\n########## {label}  [{od}]  n={len(rows)}  ({DATE})")
    print(f"{'车次':<8}{'出发站':<7}{'发车':<7}{'到达':<7}{'到达站':<7}{'历时':<7}{'二等座':<9}{'一等座':<9}{'商务座':<9}{'始发→终到':<16}起售")
    for r in rows:
        s = seat(r["price"])
        print(f"{r['code']:<8}{r['from_name']:<7}{r['dep']:<7}{r['arr']:<7}{r['to_name']:<7}"
              f"{r['dur']:<7}{str(s['二等座']):<9}{str(s['一等座']):<9}{str(s['商务座']):<9}"
              f"{(r['start']+'→'+r['end']):<16}{r['sale_hint']}")


def crossings():
    """Which trains to 宁德 also stop at 霞浦/太姥山/福鼎 (by set membership)."""
    nes = {r["code"]: r for r in load("HGH-NES")}
    xos = {r["code"] for r in load("HGH-XOS")}
    tls = {r["code"] for r in load("HGH-TLS")}
    fes = {r["code"] for r in load("HGH-FES")}
    print("\n########## 杭州→宁德 各车次是否经停 霞浦/太姥山/福鼎")
    print(f"{'车次':<8}{'出发站':<7}{'发车':<7}{'到宁德':<8}{'历时':<7}{'霞浦':<6}{'太姥山':<7}{'福鼎':<6}二等座")
    for c, r in sorted(nes.items(), key=lambda kv: kv[1]["dep"]):
        print(f"{c:<8}{r['from_name']:<7}{r['dep']:<7}{r['arr']:<8}{r['dur']:<7}"
              f"{'✓' if c in xos else '—':<6}{'✓' if c in tls else '—':<7}{'✓' if c in fes else '—':<6}"
              f"{seat(r['price'])['二等座']}")


if __name__ == "__main__":
    for od, label in [("HGH-NES", "杭州 → 宁德"), ("HGH-XOS", "杭州 → 霞浦"),
                      ("HGH-TLS", "杭州 → 太姥山"), ("HGH-FES", "杭州 → 福鼎"),
                      ("NES-HGH", "宁德 → 杭州"), ("XOS-HGH", "霞浦 → 杭州"),
                      ("TLS-HGH", "太姥山 → 杭州"), ("FES-HGH", "福鼎 → 杭州")]:
        show(od, label)
    crossings()
