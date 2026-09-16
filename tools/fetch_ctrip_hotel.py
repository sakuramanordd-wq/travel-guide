#!/usr/bin/env python3
"""Fetch Ctrip hotel detail pages -> structured facts JSON.
Usage: fetch_ctrip_hotel.py HOTEL_ID [HOTEL_ID ...]   (prints JSON lines)
"""
import re, html, subprocess, sys, json, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.normpath(os.path.join(HERE, "..", "research", "_raw", "cache"))
os.makedirs(CACHE, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

def get_text(hid, force=False):
    cf = os.path.join(CACHE, f"ctrip_hotel_{hid}.txt")
    if os.path.exists(cf) and os.path.getsize(cf) > 5000 and not force:
        return open(cf, encoding="utf-8").read()
    url = f"https://hotels.ctrip.com/hotels/{hid}.html"
    raw = subprocess.run(["curl","-sS","-m","40","-L","-A",UA,
        "-H","Accept-Language: zh-CN,zh;q=0.9", url], capture_output=True).stdout
    for enc in ("utf-8","gb18030"):
        try: t = raw.decode(enc); break
        except Exception: pass
    else: t = raw.decode("utf-8","ignore")
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>"," ",t)
    t = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</tr>|</li>","\n",t)
    t = re.sub(r"(?s)<[^>]+>"," ",t); t = html.unescape(t)
    t = t.replace("\u3000"," ").replace("\xa0"," ")
    t = re.sub(r"[ \t]+"," ",t); t = re.sub(r"\n\s*\n+","\n",t)
    open(cf,"w",encoding="utf-8").write(t)
    return t

def g(t, pat, grp=1, flags=0):
    m = re.search(pat, t, flags)
    return re.sub(r"\s+"," ",m.group(grp)).strip() if m else None

def parse(t, hid):
    d = {"ctrip_id": hid}
    d["name"] = g(t, r"南通酒店\s*\n\s*(.+?)\n")
    d["rating"] = g(t, r"点评\s*\n\s*([0-9]\s?\.\s?[0-9])\s*\n\s*(?:超棒|很好|好|棒|不错|满意|极好|一般|尚可)")
    d["reviews"] = g(t, r"([0-9][0-9,]*)\s*条评论")
    g2 = re.search(r"([0-9][0-9,]*)\s*条点评", t)
    if not d.get("reviews") and g2: d["reviews"] = g2.group(1)
    d["addr"] = g(t, r"\n\s*((?:江苏)?南通[^\n]{0,10}(?:区|市|县)[^\n]{2,70}?)\s*显示地图")
    d["phone"] = g(t, r"电话：\s*([0-9\- ]{7,20})")
    d["opened"] = g(t, r"开业：\s*([0-9]{4})")
    d["rooms"] = g(t, r"客房数：\s*([0-9]+)")
    d["metro"] = [{"station": a, "dist": b}
                  for a,b in re.findall(r"地铁站[:：]\s*([^\n（(]{1,15}?)\s*[（(]\s*([^)）]{1,12})[)）]", t)[:6]]
    d["landmarks"] = re.findall(r"(?:地标|购物|景点|机场|火车站)[:：]\s*([^\n（(]{2,30}?)\s*[（(]\s*([0-9.]+\s*(?:公里|米))", t)[:12]
    d["free_parking"] = bool(re.search(r"停车场\s*\n?\s*免费|免费\s*\n?\s*停车场|停车[\s\S]{0,12}免费", t))
    d["has_parking"] = bool(re.search(r"停车场", t))
    # breakfast policy block
    bf = re.search(r"早餐\s*\n\s*(类型：[^\n]*)\n\s*(菜品：[^\n]*)?\n?\s*(营业时间：[^\n]*)?\s*\n?(.{0,300}?)总额不包括", t, re.S)
    if bf:
        d["breakfast"] = re.sub(r"\s+"," ", " ".join(x for x in bf.groups() if x)).strip()[:300]
    d["no_breakfast"] = bool(re.search(r"早餐\s*\n\s*酒店不提供早餐", t))
    d["kids_free_bf"] = g(t, r"(1\.?[0-9]米以下儿童\s*\n?\s*免费)")
    d["deposit"] = g(t, r"押金收取方式：([^\n]{0,40})")
    d["kids"] = g(t, r"(欢迎携带儿童入住|仅允许携带[^\n]{0,30}儿童入住|不可携带儿童入住)")
    d["extrabed"] = g(t, r"(所有房型不可加床[^\n]{0,50}|[^\n]{0,40}可加床[^\n]{0,50}|不提供婴儿床[^\n]{0,30})")
    d["sub"] = {k: v.replace(" ","") for k,v in re.findall(r"(卫生|设施|环境|服务)\s+([0-9]\s?\.\s?[0-9])", t)[:4]}
    d["hot_mentions"] = re.findall(r"([\u4e00-\u9fa5]{2,8})\s*\((\d+)\)", t)[:40]
    return d

out = []
for hid in sys.argv[1:]:
    t = get_text(hid)
    if len(t) < 3000:
        out.append({"ctrip_id": hid, "error": "page too short / not found"}); continue
    d = parse(t, hid)
    # trim hot_mentions to plausible amenity tags
    keep = {"免费停车","停车方便","早餐很棒","亲子","儿童","江景","湖景","园景","近地铁站","交通便利","安静","隔音",
            "景观很棒","健身房很棒","泳池","洗衣房","性价比高","商务出行","适合出差","近景区","自助餐棒","前台热情","房间很大","新装修"}
    d["hot_mentions"] = [k for k,_ in d["hot_mentions"] if k in keep][:20]
    if d.get("rating"): d["rating"] = d["rating"].replace(" ","").replace(".",".")
    out.append(d)
    time.sleep(0.8)
print(json.dumps(out, ensure_ascii=False, indent=1))
