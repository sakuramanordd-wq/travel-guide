#!/usr/bin/env python3
"""Enumerate Ctrip hotels for the Ningde trip by running many keyword searches.

Usage: python3 tools/ningde/hotel_hunt.py [--detail]
Writes research/_raw/ningde/hotels_candidates.json and prints a ranked table.
"""
import json, os, sys, concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctrip_search as cs  # noqa: E402

ROOT = cs.ROOT
OUTDIR = os.path.join(ROOT, "research", "_raw", "ningde")
os.makedirs(OUTDIR, exist_ok=True)

KEYWORDS = [
    "宁德酒店", "宁德万达广场酒店", "宁德高铁站酒店", "宁德汽车南站酒店",
    "宁德东侨酒店", "宁德蕉城酒店", "宁德三都澳酒店", "宁德霍童古镇酒店",
    "霞浦酒店", "霞浦高铁站酒店", "霞浦县城酒店", "霞浦民宿", "霞浦摄影民宿",
    "霞浦北岐民宿", "霞浦东壁民宿", "霞浦小皓民宿", "霞浦花竹民宿",
    "霞浦三沙镇民宿", "霞浦三沙酒店", "霞浦海景民宿", "霞浦下尾岛民宿",
    "福鼎酒店", "福鼎高铁站酒店", "福鼎市区酒店", "福鼎民宿",
    "太姥山酒店", "太姥山民宿", "太姥山景区酒店", "秦屿镇酒店",
    "嵛山岛民宿", "嵛山岛酒店",
    "屏南酒店", "白水洋酒店", "白水洋民宿", "周宁酒店", "鲤鱼溪民宿",
    "杨家溪民宿", "霞浦东安岛民宿",
]

BRANDS = ["亚朵", "全季", "汉庭", "锦江之星", "如家", "维也纳", "希尔顿",
          "开元", "温德姆", "桔子", "美仑", "格林豪泰", "7天", "喆啡",
          "城市便捷", "泊寓", "璞隐", "丽枫", "途客", "海友"]


def collect():
    hotels = {}
    kws = list(KEYWORDS) + [f"宁德{b}" for b in BRANDS] + [f"霞浦{b}" for b in BRANDS] + [f"福鼎{b}" for b in BRANDS]
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for kw, raw in zip(kws, ex.map(lambda k: cs.fetch(k, "hotel"), kws)):
            d = cs.compact(raw)
            for h in d.get("hotels", []):
                if not h.get("id"):
                    continue
                h["kw"] = kw
                hotels.setdefault(h["id"], h)
    return list(hotels.values())


def rank(hs):
    def key(h):
        return (-(h.get("reviews") or 0), -(h.get("score") or 0))
    return sorted(hs, key=key)


if __name__ == "__main__":
    hs = rank(collect())
    json.dump(hs, open(os.path.join(OUTDIR, "hotels_candidates.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{len(hs)} hotels")
    for h in hs:
        print(f'{h["id"]}\t{h.get("city")}\t{h["name"]}\t{h.get("star")}\t{h.get("score")}\t'
              f'{h.get("reviews")}\t{h.get("price_from")}\t{h.get("zone")}\t{h.get("addr")}')
