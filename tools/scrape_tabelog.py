#!/usr/bin/env python3
"""Harvest real Tabelog (食べログ 中文站) data for the Osaka-Kansai guide.

Two modes:

  rankings : crawl the area ranking pages (score-sorted + recommend-sorted) of every
             area the itinerary touches, and dump every shop with its score, review
             count, genre and budget → research/tabelog_rankings.json

  search   : keyword-search Tabelog per area (e.g. モーニング / おにぎり / 明石焼き)
             → research/tabelog_search.json    用法: python3 tools/scrape_tabelog.py search

  shops    : crawl the detail page (+ review list page) of the shops listed in
             research/tabelog_targets.txt → research/tabelog_shops.json
             (score, review count, awards like 百名店, budget, hours, closed days,
              seats, payment, access, and up to 6 machine-translated reviews)

Usage:  python3 tools/scrape_tabelog.py rankings
        python3 tools/scrape_tabelog.py shops
"""
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESEARCH = os.path.join(ROOT, "research")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BASE = "https://tabelog.com/tw"

# 行程会经过的区域（食べログ 中文站 区域代码）
AREAS = {
    "新世界・恵美須・今宮": "osaka/A2701/A270206",
    "難波・日本橋・道頓堀": "osaka/A2701/A270202",
    "心齋橋・南船場": "osaka/A2701/A270201",
    "天王寺・阿倍野": "osaka/A2701/A270203",
    "京都車站周邊": "kyoto/A2601/A260101",
    "祇園・清水寺・東山": "kyoto/A2601/A260301",
    "河原町・木屋町・先斗町": "kyoto/A2601/A260201",
    "伏見稻荷・伏見桃山": "kyoto/A2601/A260601",
    "奈良・西大寺周邊": "nara/A2901/A290101",
    "神戸・三宮": "hyogo/A2801/A280101",
    "神戸・元町": "hyogo/A2801/A280102",
}


def fetch(url, tries=4):
    for i in range(tries):
        r = subprocess.run(["curl", "-s", "-A", UA, "-H", "Accept-Language: zh-TW", "-L", url],
                           capture_output=True, text=True, timeout=60)
        if r.stdout and len(r.stdout) > 20000:
            time.sleep(3.5)
            return r.stdout
        time.sleep(6 * (i + 1))
    return r.stdout or ""


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return re.sub(r"\s+", " ", s).strip()


def parse_list(html):
    """把列表页切成一家一家，抓 店名 / 分数 / 评论数 / 类目 / 预算 / 奖项。"""
    items = []
    # 每个店铺卡片以 list-rst__rst-name-target 开始
    chunks = re.split(r'<div class="list-rst__wrap', html)[1:]
    for c in chunks:
        name = re.search(r'list-rst__rst-name-target[^>]*href="([^"]+)"[^>]*>([^<]*)', c)
        if not name:
            continue
        url, nm = name.group(1), clean(name.group(2))
        score = re.search(r'list-rst__rating-val">([0-9.]+)', c)
        rvws = re.search(r'list-rst__rvw-count-num[^>]*>([0-9,]+)', c)
        area = re.search(r'list-rst__area-genre[^>]*>(.*?)</div>', c, re.S)
        bud = re.findall(r'list-rst__budget-val[^>]*>(.*?)</span>', c, re.S)
        awards = re.findall(r'list-rst__award-icon[^>]*>(.*?)</', c, re.S)
        saved = re.search(r'list-rst__save-count-num[^>]*>([0-9,]+)', c)
        items.append({
            "name": nm,
            "url": url,
            "id": url.rstrip("/").split("/")[-1],
            "score": float(score.group(1)) if score else None,
            "reviews": int(rvws.group(1).replace(",", "")) if rvws else None,
            "area_genre": clean(area.group(1)) if area else "",
            "budget": [clean(b) for b in bud],
            "awards": [clean(a) for a in awards if clean(a)],
            "saves": int(saved.group(1).replace(",", "")) if saved else None,
        })
    return items


# 关键词 × 区域（用于找「早餐 / 本地特色」这类榜单抓不到的东西）
SEARCHES = [
    ("モーニング@難波", "osaka/A2701/A270202", "モーニング"),
    ("モーニング@新世界", "osaka/A2701/A270206", "モーニング"),
    ("モーニング@天王寺阿倍野", "osaka/A2701/A270203", "モーニング"),
    ("モーニング@心齋橋", "osaka/A2701/A270201", "モーニング"),
    ("モーニング@京都駅", "kyoto/A2601/A260101", "モーニング"),
    ("モーニング@河原町", "kyoto/A2601/A260201", "モーニング"),
    ("朝食@難波", "osaka/A2701/A270202", "朝食"),
    ("朝食@天王寺阿倍野", "osaka/A2701/A270203", "朝食"),
    ("おにぎり@難波", "osaka/A2701/A270202", "おにぎり"),
    ("おにぎり@天王寺阿倍野", "osaka/A2701/A270203", "おにぎり"),
    ("おにぎり@新世界", "osaka/A2701/A270206", "おにぎり"),
    ("立ち食い@難波", "osaka/A2701/A270202", "立ち食い"),
    ("明石焼き@神戸元町", "hyogo/A2801/A280102", "明石焼き"),
    ("明石焼き@神戸三宮", "hyogo/A2801/A280101", "明石焼き"),
    ("ぼっかけ@神戸", "hyogo/A2801/A280101", "ぼっかけ"),
    ("オムライス@難波", "osaka/A2701/A270202", "オムライス"),
    ("オムライス@心齋橋", "osaka/A2701/A270201", "オムライス"),
    ("天ぷら@難波", "osaka/A2701/A270202", "天ぷら"),
    ("海鮮丼@難波", "osaka/A2701/A270202", "海鮮丼"),
    ("茶粥@奈良", "nara/A2901/A290101", "茶粥"),
    ("柿の葉寿司@奈良", "nara/A2901/A290101", "柿の葉寿司"),
    ("湯豆腐@京都", "kyoto/A2601/A260301", "湯豆腐"),
    ("おばんざい@河原町", "kyoto/A2601/A260201", "おばんざい"),
    ("ホットケーキ@京都", "kyoto/A2601/A260201", "ホットケーキ"),
    ("ホルモン@天王寺阿倍野", "osaka/A2701/A270203", "ホルモン"),
]


def search():
    import urllib.parse
    out = {}
    for label, path, kw in SEARCHES:
        url = "%s/%s/rstLst/?sw=%s" % (BASE, path, urllib.parse.quote(kw))
        html = fetch(url)
        rows = parse_list(html)
        for r in rows:
            r["area_label"] = label
        out[label] = rows
        print("%-26s -> %d 家" % (label, len(rows)), flush=True)
        json.dump(out, open(os.path.join(RESEARCH, "tabelog_search.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print("wrote research/tabelog_search.json", sum(len(v) for v in out.values()), "rows")


def rankings():
    out = {}
    for label, path in AREAS.items():
        got = {}
        for tag, query in [("score", "?SrtT=rt"), ("recommend", "")]:
            for page in (1, 2):
                url = "%s/%s/rstLst/%s%s" % (BASE, path, ("%d/" % page) if page > 1 else "", query)
                html = fetch(url)
                rows = parse_list(html)
                print("%-24s %-9s p%d -> %d 家" % (label, tag, page, len(rows)), flush=True)
                for r in rows:
                    r["area_label"] = label
                    r["sort"] = tag
                    got.setdefault(r["id"], r)
                if len(rows) < 15:
                    break
        out[label] = list(got.values())
    path = os.path.join(RESEARCH, "tabelog_rankings.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", path, sum(len(v) for v in out.values()), "rows")


AWARD_ZH = {
    "ramen_osaka": "拉面 OSAKA 百名店", "ramen_west": "拉面 WEST 百名店", "ramen_kyoto": "拉面 KYOTO 百名店",
    "okonomiyaki": "大阪烧 百名店", "curry_west": "咖喱 WEST 百名店", "bread_west": "面包 WEST 百名店",
    "udon_west": "乌冬 WEST 百名店", "soba_west": "荞麦 WEST 百名店", "sweets_west": "甜点 WEST 百名店",
    "kushiage_osaka": "炸串 OSAKA 百名店", "gyoza": "饺子 百名店", "steak_west": "牛排 WEST 百名店",
    "wagashi_west": "和菓子 WEST 百名店", "kissaten": "喫茶店 百名店", "yoshoku_west": "西式料理 WEST 百名店",
    "yoshoku": "西式料理 百名店", "cafe_west": "咖啡店 WEST 百名店", "bakeries_west": "面包 WEST 百名店",
}


def parse_shop(html):
    d = {}
    m = re.search(r'rdheader-rating__score-val[^>]*>\s*([0-9.]+)', html)
    if not m:
        m = re.search(r'"ratingValue"\s*:\s*"?([0-9.]+)', html)
    d["score"] = float(m.group(1)) if m else None
    d["title"] = clean((re.search(r'<title>(.*?)</title>', html) or [None, ""])[1])
    # 百名店 / BRONZE 等入选记录
    awards = []
    for genre, year in re.findall(r'award\.tabelog\.com/hyakumeiten/([a-z_]+)/(\d{4})/', html):
        label = AWARD_ZH.get(genre, genre)
        txt = "%s %s" % (label, year)
        if txt not in awards:
            awards.append(txt)
    for g, y in re.findall(r'award\.tabelog\.com/(bronze|silver|gold)/([a-z_]+)/(\d{4})', html):
        awards.append("%s %s" % (g.upper(), y))
    d["awards"] = awards[:6]
    head = html[html.find('id="rst-data-head"'):html.find('id="rst-data-head"') + 40000]
    txt = clean(head)
    def field(label, stop=("地址", "交通方式", "營業時間", "公休日", "預算", "付款", "座位", "電話", "首頁", "店名", "預訂", "菜系", "獲獎")):
        i = txt.find(label)
        if i < 0:
            return ""
        rest = txt[i + len(label):]
        for s in stop:
            j = rest.find(s)
            if j > 0:
                rest = rest[:j]
        return rest.strip(" ：:")[:220]
    d["address"] = field("地址")
    d["access"] = field("交通方式")
    d["hours"] = field("營業時間")
    d["closed"] = field("公休日")
    d["budget"] = field("預算")
    b = re.search(r"預算.*?(JPY [0-9,]+～JPY [0-9,]+)", txt)
    d["budget_jpy"] = b.group(1) if b else ""
    d["reserve"] = field("預訂可/不可") or field("預訂")
    d["payment"] = field("付款方式")
    d["seats"] = field("座位數") or field("座位")
    d["tel"] = field("電話")
    d["genre"] = field("類別") or field("類型")
    d["tabelog_url"] = ""
    return d


def parse_reviews(html, limit=20):
    """评论列表页：抓 评分 / 正文 / 日期 / 同行人数 / 午晚餐。"""
    out = []
    blocks = re.split(r'js-rvw-item-clickable-area', html)[1:]
    for b in blocks:
        if len(out) >= limit:
            break
        score = re.search(r'c-rating-v3--val(\d)(\d)', b)
        if not score:
            sc = re.search(r'c-rating-v3__val[^>]*>\s*([0-9.]+)', b)
            score_txt = sc.group(1) if sc else None
        else:
            score_txt = "%s.%s" % (score.group(1), score.group(2))
        body = re.search(r'rvw-item__rvw-comment[^>]*>(.*?)</(?:p|div)>', b, re.S)
        if not body:
            continue
        date = re.search(r'rvw-item__date[^>]*>(.*?)</', b, re.S)
        who = re.search(r'rvw-item__rvwr-name[^>]*>(.*?)</', b, re.S)
        pay = re.search(r'rvw-item__payment-amount[^>]*>(.*?)</', b, re.S)
        meal = re.search(r'c-rating-v3__time--(lunch|dinner)', b)
        out.append({
            "score": float(score_txt) if score_txt else None,
            "text": clean(body.group(1))[:500],
            "date": clean(date.group(1))[:30] if date else "",
            "who": clean(who.group(1))[:24] if who else "",
            "pay": clean(pay.group(1))[:24] if pay else "",
            "meal": meal.group(1) if meal else "",
        })
    return out


RANK_INDEX = {}


def shops():
    for fname in ("tabelog_rankings.json", "tabelog_search.json"):
        rpath = os.path.join(RESEARCH, fname)
        if os.path.exists(rpath):
            for items in json.load(open(rpath, encoding="utf-8")).values():
                for it in items:
                    RANK_INDEX.setdefault(it["id"], it)
    tpath = os.path.join(RESEARCH, "tabelog_targets.txt")
    targets = [l.strip() for l in open(tpath, encoding="utf-8") if l.strip() and not l.startswith("#")]
    out = {}
    opath = os.path.join(RESEARCH, "tabelog_shops.json")
    if os.path.exists(opath):
        out = json.load(open(opath, encoding="utf-8"))
    for t in targets:
        url = t if t.startswith("http") else "%s/%s/" % (BASE, t.lstrip("/"))
        sid = url.rstrip("/").split("/")[-1]
        if sid in out and len(out[sid].get("reviews_list") or []) >= 8:
            print("skip", sid)
            continue
        html = fetch(url)
        d = parse_shop(html)
        d["tabelog_url"] = url
        d["reviews"] = None
        rank = RANK_INDEX.get(sid)
        if rank:
            d["score"] = d.get("score") or rank.get("score")
            d["reviews"] = rank.get("reviews")
            d["area_genre"] = rank.get("area_genre")
            d["budget_list"] = rank.get("budget")
            d["name"] = rank.get("name")
        # 先抓评论列表，再据此算好评率 —— 顺序反了的话新店会拿到 good_rate=None
        rv = fetch(url.rstrip("/") + "/dtlrvwlst/")
        d["reviews_list"] = parse_reviews(rv)
        rated = [r["score"] for r in d["reviews_list"] if r.get("score")]
        if rated:
            d["good_rate"] = round(100 * sum(1 for x in rated if x >= 3.5) / len(rated))
            d["sample_avg"] = round(sum(rated) / len(rated), 2)
            d["sample_n"] = len(rated)
        out[sid] = d
        print("OK %s %s score=%s reviews=%s awards=%s rvws=%d" %
              (sid, d["title"][:40], d["score"], d.get("reviews"), d["awards"][:2], len(d["reviews_list"])), flush=True)
        json.dump(out, open(opath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", opath, len(out), "shops")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "rankings"
    os.makedirs(RESEARCH, exist_ok=True)
    if mode == "rankings":
        rankings()
    elif mode == "search":
        search()
    else:
        shops()
