#!/usr/bin/env python3
"""Scrape Ctrip (携程) hotel detail pages for the Ningde guide -> structured JSON.

Usage:
  python3 tools/ningde/ctrip_hotel_detail.py ID [ID ...]
  python3 tools/ningde/ctrip_hotel_detail.py --file research/_raw/ningde/hotel_ids.txt
  python3 tools/ningde/ctrip_hotel_detail.py --dump ID      # raw cleaned text (for debugging)

Output: research/_raw/ningde/hotels_detail.json  + a readable table on stdout.
Region-agnostic version of tools/fetch_ctrip_hotel.py (which hard-codes 南通).
"""
import concurrent.futures as cf
import html
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUTDIR = os.path.join(ROOT, "research", "_raw", "ningde")
CACHE = os.path.join(ROOT, "research", "_raw", "cache")
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUTDIR, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

NEARBY_KIND = ("商业区", "火车站", "汽车站", "机场", "地标", "购物", "景点",
               "地铁站", "休闲娱乐", "医院", "大学")
KEEP_FACILITY = ("停车场", "行李寄存", "接站", "送站", "接送", "洗衣", "健身",
                 "餐厅", "早餐", "行李", "充电", "前台", "茶室", "行李房",
                 "空调", "电梯", "无烟", "叫车", "租车", "儿童", "泳池", "温泉", "厨房")


def clean(t):
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</tr>|</li>|</h\d>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t).replace("\u3000", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def get_text(hid, force=False):
    cf_ = os.path.join(CACHE, f"ctrip_hotel_{hid}.txt")
    if os.path.exists(cf_) and os.path.getsize(cf_) > 5000 and not force:
        return open(cf_, encoding="utf-8").read()
    url = f"https://hotels.ctrip.com/hotels/{hid}.html"
    raw = subprocess.run(["curl", "-sS", "-m", "45", "-L", "-A", UA,
                          "-H", "Accept-Language: zh-CN,zh;q=0.9", url],
                         capture_output=True).stdout
    t = clean(raw.decode("utf-8", "ignore"))
    open(cf_, "w", encoding="utf-8").write(t)
    return t


def _g(t, pat, grp=1, flags=0):
    m = re.search(pat, t, flags)
    return re.sub(r"\s+", " ", m.group(grp)).strip() if m else None


def parse(t, hid):
    d = {"ctrip_id": hid, "url": f"https://hotels.ctrip.com/hotels/{hid}.html"}
    d["name"] = _g(t, r"^\s*(.+?)预订价格")
    d["addr"] = _g(t, r"\n\s*((?:福建|浙江|江苏|广东)?[\u4e00-\u9fa5]{2,12}(?:省|市)?[^\n]{6,90}?)\s*显示地图")
    m = re.search(r"\n\s*(\d)\s*\.\s*(\d)\s*\n\s*(超棒|很好|好|不错|棒|满意|极好|一般|尚可)", t)
    d["score"] = (m.group(1) + "." + m.group(2)) if m else None
    d["score_word"] = m.group(3) if m else None
    d["reviews"] = _g(t, r"显示所有([\d,]+)条点评") or _g(t, r"([\d,]+)\s*条评论")
    d["sub"] = {k: re.sub(r"\s+", "", v) for k, v in re.findall(r"\n(卫生|设施|环境|服务)\s*(\d\s*\.\s*\d)", t)[:4]}
    d["nearby"] = [{"kind": a, "name": b.strip(), "dist": c.strip()}
                   for a, b, c in re.findall(
                       r"(" + "|".join(NEARBY_KIND) + r"):\s*([^\n（(]{2,40}?)\s*[（(]([0-9.]+\s*(?:公里|米))", t)[:14]]
    # 设施块
    fac = []
    m = re.search(r"酒店设施\s*\n(.*?)\n\s*所有设施", t, re.S)
    if m:
        for line in m.group(1).split("\n"):
            line = line.strip()
            if 1 < len(line) < 40 and any(k in line for k in KEEP_FACILITY):
                fac.append(line)
    d["facilities"] = fac[:24]
    d["free_parking"] = any("停车场" in f and "免费" in f for f in fac)
    d["has_parking"] = any("停车场" in f for f in fac)
    d["free_luggage"] = any("行李寄存" in f and "免费" in f for f in fac)
    # 热门提及
    tags = []
    m = re.search(r"热门提及(.*?)(?:\n\s*住客印象|\n\s*附近|\Z)", t, re.S)
    blk = m.group(1) if m else ""
    seen_tag = set()
    for k, n in re.findall(r"([\u4e00-\u9fa5A-Za-z]{2,14})\s*\(([\d,]+)\)", blk):
        if k in ("所有点评",) or k in seen_tag:
            continue
        seen_tag.add(k)
        tags.append([k, int(n.replace(",", ""))])
    d["tags"] = tags[:22]
    d["recommend"] = next((n for k, n in tags if k in ("值得推荐", "推荐")), None)
    d["bad_reviews"] = next((n for k, n in tags if k == "差评"), None)
    # 政策（静态页常只有部分）
    total = int((d["reviews"] or "0").replace(",", "")) or None
    if d.get("recommend") and total:
        d["good_rate"] = round(d["recommend"] / total * 100, 1)
    pol = {}
    for key, pat in (("入住", r"入住时间[：:]\s*([^\n]{1,30})"),
                     ("退房", r"退房时间[：:]\s*([^\n]{1,30})"),
                     ("早餐", r"早餐[：:]\s*([^\n]{1,60})"),
                     ("押金", r"(押金[^\n]{0,80})"),
                     ("儿童", r"(欢迎携带儿童入住|不可携带儿童入住|仅限[^\n]{0,30}儿童入住[^\n]{0,20})"),
                     ("加床", r"(所有房型不可加床[^\n]{0,50}|[^\n]{0,30}可加床[^\n]{0,50})"),
                     ("宠物", r"(允许携带宠物|不可携带宠物)"),
                     ("年龄", r"(不允许18岁以下[^\n]{0,30}|[^\n]{0,20}未成年人[^\n]{0,30})")):
        v = _g(t, pat)
        if v:
            pol[key] = v
    d["policy"] = pol
    d["opened"] = _g(t, r"开业[：:]\s*(\d{4}[^\n]{0,20})")
    d["renovated"] = _g(t, r"装修[：:]\s*(\d{4}[^\n]{0,20})")
    d["rooms"] = _g(t, r"客房数[：:]\s*(\d+)")
    d["phone"] = _g(t, r"电话[：:]\s*([0-9\-+ ]{7,22})")
    # 住客印象里的前几条真实点评（含好评与差评原文）
    quotes = []
    m = re.search(r"住客印象\s*\n(.*?)(?:\n\s*酒店问答|\n\s*附近|\n\s*常见问题|\Z)", t, re.S)
    if m:
        for line in m.group(1).split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            if len(line) >= 60 and not line.startswith(("酒店回复", "展开")):
                quotes.append(line[:420])
            if len(quotes) >= 3:
                break
    d["quotes"] = quotes
    img = re.search(r"(https://dimg\d*\.c-ctrip\.com/images/[^\s\"'\\]+?)_R_", t)
    d["img"] = img.group(0) if img else None
    return d


def run(ids, force=False):
    out = []
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for hid, t in zip(ids, ex.map(lambda h: get_text(h, force), ids)):
            try:
                out.append(parse(t, hid))
            except Exception as e:
                out.append({"ctrip_id": hid, "error": str(e)})
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--dump":
        print(get_text(args[1], force=True)[:6000])
        sys.exit(0)
    if args and args[0] == "--file":
        ids = [l.strip() for l in open(args[1], encoding="utf-8") if l.strip() and not l.startswith("#")]
    else:
        ids = [a for a in args if a.isdigit()]
    res = run(ids)
    json.dump(res, open(os.path.join(OUTDIR, "hotels_detail.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for d in res:
        if d.get("error"):
            print("ERR", d["ctrip_id"], d["error"]); continue
        near = "; ".join(f'{x["kind"]}:{x["name"]}{x["dist"]}' for x in d["nearby"][:5])
        print(f'{d["ctrip_id"]}\t{d["name"]}\t{d["score"]}/{d["reviews"]}\t{d.get("addr")}\t{near}\t'
              f'park={"免费" if d["free_parking"] else ("有" if d["has_parking"] else "-")}\t'
              f'luggage={"免费" if d["free_luggage"] else "-"}\t{",".join(f"{k}({v})" for k, v in d["tags"][:6])}')
    print("wrote research/_raw/ningde/hotels_detail.json", len(res))
