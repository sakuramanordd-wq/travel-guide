#!/usr/bin/env python3
"""Stop-aware analysis: which 杭州->宁德 trains actually stop at 霞浦/太姥山/福鼎,
and via which route (coastal 杭甬+甬台温 vs inland 金温线)."""
import json, os, sys

RAW = os.path.join(os.path.dirname(__file__), "..", "research", "_raw", "ningde")
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-09-29"
KEY = ["福鼎", "太姥山", "霞浦", "宁德"]
COASTAL = {"绍兴北", "余姚北", "宁波", "宁海", "三门县", "临海", "台州西", "温岭", "雁荡山"}
INLAND = {"诸暨", "义乌", "永康南", "缙云西", "丽水", "青田"}


def rows(od):
    p = os.path.join(RAW, f"12306_{od}_{DATE}.json")
    return json.load(open(p, encoding="utf-8"))["rows"] if os.path.exists(p) else []


stops = json.load(open(os.path.join(RAW, f"stops_{DATE}.json"), encoding="utf-8"))


def route(code):
    names = {s["station"] for s in stops.get(code, [])}
    r = []
    if names & COASTAL:
        r.append("沿海(杭甬+甬台温)")
    if names & INLAND:
        r.append("金温线")
    return "+".join(r) or "?"


def keytimes(code):
    d = {}
    for s in stops.get(code, []):
        if s["station"] in KEY:
            d[s["station"]] = (s["arr"], s["dep"])
    return d


def main():
    print(f"===== A. 杭州→宁德 各车次经停 福鼎/太姥山/霞浦（{DATE}）=====")
    print(f"{'车次':<7}{'出发站':<7}{'发车':<6}{'到宁德':<7}{'历时':<7}{'路线':<20}"
          f"{'福鼎':<14}{'太姥山':<14}{'霞浦':<14}二等座")
    for r in sorted(rows("HGH-NES"), key=lambda x: x["dep"]):
        if r["dep"] == "24:00":
            continue
        k = keytimes(r["code"])
        f = lambda n: (f"{k[n][0]}/{k[n][1]}" if n in k else "—")
        print(f"{r['code']:<7}{r['from_name']:<7}{r['dep']:<6}{r['arr']:<7}{r['dur']:<7}"
              f"{route(r['code']):<20}{f('福鼎'):<14}{f('太姥山'):<14}{f('霞浦'):<14}"
              f"{r['price'].get('O')}")

    for od, lbl in [("HGH-XOS", "B. 杭州→霞浦 直达"), ("HGH-TLS", "C. 杭州→太姥山/福鼎 直达"),
                    ("XOS-HGH", "D. 霞浦→杭州 返程"), ("TLS-HGH", "E. 太姥山/福鼎→杭州 返程"),
                    ("NES-HGH", "F. 宁德→杭州 返程")]:
        print(f"\n===== {lbl}（{DATE}）=====")
        for r in sorted(rows(od), key=lambda x: x["dep"]):
            print(f"{r['code']:<7}{r['from_name']:<7}{r['dep']:<6}-> {r['arr']:<6}{r['to_name']:<7}"
                  f"{r['dur']:<7}二等座 {str(r['price'].get('O')):<9}一等座 {str(r['price'].get('M')):<9}"
                  f"{(r['start']+'→'+r['end']):<16}{r['sale_hint']}")


if __name__ == "__main__":
    main()
