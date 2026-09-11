#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「吃什么」重建成按餐次（早饭 / 午饭 / 下午 / 晚饭 / 夜宵）推荐，数据只用真实评分。

做四件事：
  1. 给 tools/meal_data.py 里 NEW 的每家店生成弹窗（评分 / 评论数 / 好评率 / 招牌 /
     好评原文 / 差评原文 / 营业 / 定休 / 座位 / 预约 / 付款 / 怎么去 / 顺路）
  2. 给复查后撤下的店（DEMOTED）打上「已撤下推荐」标记
  3. 每个 Day 的「吃什么」整块换成按餐次的时间轴
  4. 美食清单区按品类重排，并附「复查后撤下」名单

用法： python3 tools/build_meal_page.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meal_data import NEW, DEMOTED, DAY_PLAN, EXISTING, AREA_FIX  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "大阪关西5天4夜攻略.html")
SHOPS = os.path.join(ROOT, "research", "tabelog_shops.json")
CREDITS = os.path.join(ROOT, "images", "food", "credits.json")

TIER_LABEL = {"S": "🏆 本次最高分", "A": "★ 值得专程", "B": "顺路吃", "C": "🕐 方便兜底"}

DISH = {
    "f-mutetteppou": "豚骨拉面（猪背脂浓汤）", "f-menshiro": "贝类高汤拉面", "f-fujii": "中华荞麦 + 炒饭",
    "f-kitada": "贝汤拉面", "f-inoichi": "白酱油 / 和牛拉面", "f-tenpumori": "冷乌冬",
    "f-chitose-udon": "名物「肉吸」+ 乌冬", "f-temmatsu": "肉乌冬 + 杂烩饭", "f-tsukumo": "鸡蛋乌冬",
    "f-kobayashi": "手打十成荞麦", "f-gen-nara": "手打荞麦（只配盐）", "f-fukutaro": "葱烧 + 大阪烧",
    "f-chitose-okonomi": "大阪烧（松软料多）", "f-manbo": "まんぼ焼（京风大阪烧）", "f-rokkakuto": "创做串扬套餐",
    "f-yaei": "串炸 + どて焼き", "f-yako": "现炸串炸（一串 ¥150 起）", "f-kankan": "新世界章鱼烧",
    "f-hashimotoya": "香料咖喱（每日限量）", "f-madras": "大阪甘辛咖喱（份量极大）", "f-nijinohotoke": "香料咖喱 + 配菜",
    "f-savoy": "牛肉咖喱（菜单只有这一道）", "f-plaisir": "神户牛铁板烧", "f-gyoza-daigaku": "饺子（味噌蘸酱）",
    "f-asahi-yoshoku": "炸牛排 + 德米格拉斯酱", "f-patisserie-s": "招牌蛋糕「エス」", "f-ashishima": "葦島特调咖啡",
    "f-sennariya": "混合果汁 + 复古布丁", "f-shizuku": "水果大福", "f-lepremier": "手冲咖啡 + 起司蛋糕",
    "f-biensur": "食パン / 三明治", "f-nakatanido": "艾草饼（よもぎ餅）", "f-kashiya": "季节冰品 + 上生菓子",
    "f-montplus": "焦糖蛋糕", "f-camarche": "硬式面包 / 可颂", "f-ichiran": "天然豚骨拉面", "f-551horai": "猪肉包（豚まん）",
    "f-yamamotomenzo": "咖喱乌冬 + 冷乌冬", "f-menya-k": "鸡白汤拉面",
}

# 美食清单区的分组：(标题, 副标题, [店铺 id])
CAT_GROUPS = [
    ("🍜 拉面（每天都吃得到）", "大阪清汤 / 贝汤 / 京都酱油各有代表；多数只收现金",
     ["f-jojoro", "f-mutetteppou", "f-menshiro", "f-kamikura", "f-kitada", "f-inoichi", "f-menya-k", "f-ichiran"]),
    ("🍲 乌冬 · 荞麦（本趟评分最高的一档）", "京都 3.98 / 奈良 4.04 都在这里；多数只做午市",
     ["f-yamamotomenzo", "f-gen-nara", "f-chitose-udon", "f-tenpumori", "f-temmatsu", "f-kobayashi", "f-tsukumo", "f-okaru"]),
    ("🍢 串炸 · 新世界 / 日本桥", "薄衣现炸、酱汁禁止二次蘸；周四 八重勝 休，去前看营业日",
     ["f-rokkakuto", "f-yako", "f-yaei", "f-daruma", "f-gifuya"]),
    ("🥘 大阪烧 · 粉类", "份量大：两人点一份主食 + 一份豚平烧刚好；平日多数只做晚市",
     ["f-fukutaro", "f-manbo", "f-chitose-okonomi"]),
    ("🐙 章鱼烧（站着吃完继续走）", "一份 6–8 个，刚出锅极烫",
     ["f-kankan"]),
    ("🍛 咖喱 · 洋食 · 神户牛", "本次最高分 4.03 的咖喱就在这里；神户牛午市比晚市便宜一大截",
     ["f-hashimotoya", "f-savoy", "f-asahi-yoshoku", "f-nijinohotoke", "f-gyoza-daigaku", "f-madras", "f-plaisir", "f-ishida", "f-551horai"]),
    ("🍡 甜品 · 下午茶", "玉製家 14:00 开卖、中谷堂现捣麻糬 · 注意定休日",
     ["f-kashiya", "f-patisserie-s", "f-tamasei", "f-montplus", "f-shizuku", "f-nakatanido", "f-alshon"]),
    ("☕ 咖啡 · 面包（早饭 / 歇脚）", "千成屋咖啡 周末 09:00 开、Bien Sur 08:00 开",
     ["f-camarche", "f-ashishima", "f-biensur", "f-lepremier", "f-sennariya"]),
]

CSS = """
  /* ==MEALS-CSS-START== */
  /* ---- 按餐次的「吃什么」时间轴 ---- */
  .meals{margin-top:6px}
  .meal{position:relative;border-left:2px solid var(--line);padding:0 0 14px 18px;margin-left:5px}
  .meal:last-child{border-left-color:transparent;padding-bottom:2px}
  .meal:before{content:"";position:absolute;left:-7px;top:5px;width:12px;height:12px;border-radius:50%;background:var(--shu);box-shadow:0 0 0 3px #fff,0 0 0 4px var(--shu-l)}
  .mhead{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;margin-bottom:3px}
  .mtime{font-size:12.5px;font-weight:700;color:#fff;background:var(--shu-d);border-radius:7px;padding:2px 8px;letter-spacing:.4px}
  .mname{font-size:15.5px;font-weight:700;color:var(--ai-d)}
  .mwhere{font-size:12px;color:var(--muted);background:var(--cream);border:1px solid var(--line);border-radius:999px;padding:1px 9px}
  .mnote{font-size:13px;color:#4a4640;line-height:1.72;margin:3px 0 9px}
  .mnote b{color:var(--shu-d)}
  /* 封面上的档位徽章：必须限定在 .scard .cover 内，否则会覆盖 #precheck
     的 .tier 网格行（曾导致「行前必查清单」整块塌陷到首屏底部） */
  .scard .cover .tier{position:absolute;left:8px;bottom:8px;background:rgba(201,154,63,.94);color:#fff;font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:999px}
  .scard .cover .tier.s{background:rgba(180,71,47,.94)}
  .scard .cover .tier.c{background:rgba(90,96,105,.9)}
  .mlinks{font-size:12.5px;color:var(--muted);margin:2px 0 0;line-height:1.9}
  .mlinks .lab{cursor:pointer;color:var(--ai-d);font-weight:600;border-bottom:1px dotted var(--gold);padding-bottom:1px}
  .mlinks .lab:hover{background:var(--gold-l);border-radius:4px}
  /* ---- 餐次内的「品类」分组小标题 ---- */
  .mcats{display:grid;gap:12px;margin-top:2px}
  .mcat-row{border-top:1px dashed var(--line);padding-top:9px}
  .mcat-row:first-child{border-top:none;padding-top:0}
  .mcat{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:7px}
  .mcat .cn{font-size:13.5px;font-weight:700;color:var(--shu-d)}
  .mcat .cn:before{content:"◆";font-size:9px;color:var(--gold);margin-right:5px;vertical-align:1px}
  .mcat .ch{font-size:12px;color:var(--muted);line-height:1.6}
  .mcat .cnt{font-size:11.5px;color:var(--muted);background:var(--cream);border:1px solid var(--line);border-radius:999px;padding:1px 8px;margin-left:auto}
  .mcat-row .sgrid{margin-top:0}
  .demote{display:grid;gap:9px;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));margin-top:10px}
  .dcard{background:#fff;border:1px solid var(--line);border-left:4px solid #b4472f;border-radius:12px;padding:11px 13px;cursor:pointer;transition:.18s}
  .dcard:hover{box-shadow:0 6px 16px rgba(0,0,0,.09)}
  .dcard .dn{font-size:14px;font-weight:700;color:var(--ai-d)}
  .dcard .ds{font-size:12px;color:var(--muted);margin-top:3px;display:flex;gap:8px;flex-wrap:wrap}
  .dcard .ds b{color:#b4472f}
  .dcard .dr{font-size:12.4px;color:#5a5650;line-height:1.6;margin-top:6px}
  /* ==MEALS-CSS-END== */
"""


def clean(s, n=None):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("\u3000", " ").replace("&nbsp;", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if n and len(s) > n:
        s = s[: n - 1] + "…"
    return s


def js(s):
    """安全地放进 JS 双引号字符串。"""
    return (s or "").replace("\\", "\\\\").replace('"', "”").replace("\n", " ")


def html_esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def stars_for(tier, score):
    if tier == "S":
        return "★★★★★"
    if tier == "C":
        return "★★☆☆☆"
    if tier == "A":
        return "★★★★★" if (score or 0) >= 3.7 else "★★★★☆"
    return "★★★★☆" if (score or 0) >= 3.6 else "★★★☆☆"


def rate_cls(pct):
    try:
        n = int(str(pct).replace("%", ""))
    except ValueError:
        return ""
    return "" if n >= 85 else ("mid" if n >= 70 else "low")


def load_shops():
    raw = json.load(open(SHOPS, encoding="utf-8"))
    out = {}
    for sid, cfg in NEW.items():
        d = raw.get(cfg["tid"], {})
        rv = d.get("reviews_list") or []
        good = [r for r in rv if (r.get("score") or 0) >= 4 and len(clean(r.get("text"))) >= 50]
        good.sort(key=lambda r: (-(r["score"]), -len(clean(r.get("text")))))
        bad = [r for r in rv if r.get("score") is not None and r["score"] <= 3.2
               and len(clean(r.get("text"))) >= 50]
        bad.sort(key=lambda r: (r["score"], -len(clean(r.get("text")))))
        g1 = good[0] if good else None
        g2 = good[1] if len(good) > 1 else None
        b1 = bad[0] if bad else None
        out[sid] = dict(
            id=sid, cfg=cfg, score=d.get("score"), reviews=d.get("reviews"),
            good_rate=d.get("good_rate"), avg=d.get("sample_avg"), n=d.get("sample_n"),
            url=d.get("tabelog_url", ""), awards=d.get("awards") or [],
            good=g1, good2=g2, bad=b1, genre=d.get("area_genre", ""),
        )
    return out


def review_line(r, label):
    if not r:
        return None
    txt = clean(r.get("text"), 190)
    date = (r.get("date") or "").replace(" 訪問", "").strip()
    return ["真实评价 · %s" % label, "“%s” —— 食べログ 用户（%s 分 · %s）" % (txt, r.get("score"), date)]


def modal_entry(sh):
    cfg = sh["cfg"]
    sid = sh["id"]
    cred = CREDITS_JSON.get(sid + ".jpg", {})
    cap = "%s（参考图，非本店实拍）" % DISH.get(sid, cfg["cat"])
    img = ['images/food/%s.jpg' % sid, cap + ("" if not cred else " · %s / Wikimedia Commons · %s" % (
        clean(cred.get("author") or "Wikimedia Commons", 40), cred.get("license") or "CC")), cred.get("page", "")]
    tags = ["食べログ %s" % sh["score"]]
    if sh["reviews"]:
        tags.append("%s 条评价" % format(sh["reviews"], ","))
    if sh["good_rate"] is not None:
        tags.append("好评率 %s%%" % sh["good_rate"])
    if sh["awards"]:
        tags.append(sh["awards"][0])
    tags.append("推荐 %s" % stars_for(cfg["tier"], sh["score"]))
    rows = [
        ["人均", cfg["price"]],
        ["口碑", "食べログ %s 分（%s 条评价） · 好评率 %s%%（抽样 %s 条中 ≥3.5 分的比例，抽样均分 %s）" % (
            sh["score"], format(sh["reviews"] or 0, ","), sh["good_rate"], sh["n"], sh["avg"])],
        ["推荐指数", "%s · %s" % (stars_for(cfg["tier"], sh["score"]), TIER_LABEL[cfg["tier"]])],
        ["招牌 / 点单", cfg["dishes"]],
        ["营业", cfg["hours"]],
        ["定休", cfg["closed"]],
        ["座位", cfg["seats"]],
        ["预约", cfg["reserve"]],
        ["付款", cfg["pay"]],
        ["怎么去", cfg["access"]],
        ["顺路", cfg["route"]],
    ]
    if sh["awards"]:
        rows.insert(4, ["获奖 / 入选", " / ".join(sh["awards"][:4])])
    shop = [x for x in [review_line(sh["good"], "正面"), review_line(sh["good2"], "正面（第二条）"),
                        review_line(sh["bad"], "吐槽 / 注意")] if x]
    rec = ["顺路安排：%s" % cfg["route"], cfg["why"]]
    if not sh["awards"]:
        rec.append("本次复查评分 %s 分（%s 条评价），已进入推荐名单——但没进百名店，属于「顺路吃很好」的一档。" % (sh["score"], format(sh["reviews"] or 0, ",")))
    pit = [cfg["pit"]]

    def arr(items):
        return "[" + ",".join('"%s"' % js(x) for x in items) + "]"

    L = ['"%s": {' % sid]
    L.append('  tone:"d3", ic:"%s", t:"%s", s:"%s · 人均 %s",' % (cfg["ic"], js(cfg["name"]), js(cfg["s"]), js(cfg["price"])))
    L.append('  tag:[%s],' % ",".join('"%s"' % js(t) for t in tags))
    L.append('  img:[%s],' % ",".join('"%s"' % js(x) for x in img))
    L.append('  cat:"%s",' % js(cfg["cat"]))
    L.append('  rows:[%s],' % ",".join("[%s]" % ",".join('"%s"' % js(c) for c in r) for r in rows))
    L.append('  shop:[%s],' % ",".join("[%s]" % ",".join('"%s"' % js(c) for c in r) for r in shop))
    L.append('  rec:[%s],' % ",".join('"%s"' % js(r) for r in rec))
    L.append('  pit:[%s],' % ",".join('"%s"' % js(p) for p in pit))
    L.append('  src:[["食べログ（中文站）","%s"]]' % sh["url"])
    L.append('}')
    return "\n".join(L)


def load_existing(html):
    """解析页面里已有的 f-* 弹窗（老弹窗保留的店），生成餐次卡片需要的信息。"""
    out = {}
    for m in re.finditer(r'\n"(f-[a-z0-9\-]+)": \{(.*?)\n\}(?=,|\n)', html, re.S):
        sid, body = m.group(1), m.group(2)
        if sid in NEW or sid not in EXISTING:
            continue

        def fld(name):
            r = re.search(r'\b%s:"([^"]*)"' % name, body)
            return r.group(1) if r else ""

        def row(key):
            r = re.search(r'\["%s","(.*?)"\]' % key, body)
            return r.group(1) if r else ""

        tag = re.search(r'\btag:\[(.*?)\]', body)
        tags = re.findall(r'"([^"]*)"', tag.group(1)) if tag else []
        meta = EXISTING[sid]
        cred = CREDITS_JSON.get(sid + ".jpg", {})
        out[sid] = dict(
            id=sid, name=fld("t"), cat=meta["cat"], tier=meta["tier"],
            score=next((t.replace("食べログ ", "") for t in tags if t.startswith("食べログ")), ""),
            good=next((t.replace("好评率 ", "") for t in tags if t.startswith("好评率")), ""),
            price=clean(row("人均").split(" · ")[0]),
            sig=clean(row("招牌") or row("招牌 / 点单")),
            hours=clean(row("营业")),
            route=clean(fld("s")), pit=meta["pit"],
            credit="" if not cred else "© %s · %s" % (clean(cred.get("author") or "Wikimedia Commons", 30), cred.get("license") or "CC"),
        )
    return out


def scard_existing(sh):
    return "\n".join([
        '                <div class="scard" data-modal="%s">' % sh["id"],
        '                  <div class="cover">',
        '                    <img src="images/food/%s.jpg" alt="%s 参考图" loading="lazy">' % (sh["id"], html_esc(sh["cat"])),
        '                    <span class="lv">%s</span>' % ({"S": "★★★★★", "A": "★★★★★", "B": "★★★★☆", "C": "★★☆☆☆"}[sh["tier"]]),
        '                    <span class="rt %s">好评率 %s</span>' % (rate_cls(sh["good"]), sh["good"]),
        '                    <span class="tier %s">%s</span>' % (sh["tier"].lower(), TIER_LABEL[sh["tier"]]),
        ('                    <span class="cr">%s</span>' % html_esc(sh["credit"])) if sh["credit"] else '',
        '                  </div>',
        '                  <div class="cb">',
        '                    <div class="cname">%s</div>' % html_esc(sh["name"]),
        '                    <div class="cmeta"><span class="sc">食べログ %s</span><span>·</span><span>%s</span></div>' % (sh["score"], html_esc(sh["cat"])),
        '                    <div class="cline"><span class="k">人均</span> %s</div>' % html_esc(sh["price"]),
        '                    <div class="cline"><span class="k">招牌</span> %s</div>' % html_esc(clean(sh["sig"], 40)),
        '                    <div class="cline"><span class="k">营业</span> %s</div>' % html_esc(clean(sh["hours"], 40)),
        '                    <div class="cline warn"><span class="k">注意</span> %s</div>' % html_esc(clean(sh["pit"], 46)),
        '                    <div class="cmore"><span class="cta">点开看好评 / 差评 →</span><span>%s</span></div>' % html_esc(clean(sh["cat"], 16)),
        '                  </div>',
        '                </div>',
    ])


def scard(sh):
    cfg = sh["cfg"]
    sid = sh["id"]
    cred = CREDITS_JSON.get(sid + ".jpg", {})
    cr = "" if not cred else "© %s · %s" % (clean(cred.get("author") or "Wikimedia Commons", 30), cred.get("license") or "CC")
    return "\n".join([
        '                <div class="scard" data-modal="%s">' % sid,
        '                  <div class="cover">',
        '                    <img src="images/food/%s.jpg" alt="%s 参考图" loading="lazy">' % (sid, html_esc(cfg["cat"])),
        '                    <span class="lv">%s</span>' % stars_for(cfg["tier"], sh["score"]),
        '                    <span class="rt %s">好评率 %s%%</span>' % (rate_cls(sh["good_rate"]), sh["good_rate"]),
        ('                    <span class="tier %s">%s</span>' % (cfg["tier"].lower(), TIER_LABEL[cfg["tier"]])),
        ('                    <span class="cr">%s</span>' % html_esc(cr)) if cr else '',
        '                  </div>',
        '                  <div class="cb">',
        '                    <div class="cname">%s</div>' % html_esc(cfg["name"]),
        '                    <div class="cmeta"><span class="sc">食べログ %s</span><span>·</span><span>%s</span></div>' % (sh["score"], html_esc(clean(cfg["s"], 46))),
        '                    <div class="cline"><span class="k">人均</span> %s</div>' % html_esc(cfg["price"]),
        '                    <div class="cline"><span class="k">招牌</span> %s</div>' % html_esc(clean(cfg["dishes"], 40)),
        '                    <div class="cline"><span class="k">营业</span> %s</div>' % html_esc(clean(cfg["hours"], 40)),
        '                    <div class="cline warn"><span class="k">注意</span> %s</div>' % html_esc(clean(cfg["pit"], 46)),
        '                    <div class="cmore"><span class="cta">点开看好评 / 差评 →</span><span>%s</span></div>' % html_esc(clean(cfg["route"], 20)),
        '                  </div>',
        '                </div>',
    ])


def links(items):
    """把「区域攻略 / 避坑」做成一行内联链接（不再重复整天的大卡片）。"""
    parts = ['<span class="lab" data-modal="%s">%s %s</span>' % (mid, ic, title) for mid, ic, title, _sub, _badge in items]
    return '          <p class="mlinks">📖 顺路攻略：%s</p>' % " · ".join(parts)



# ---------- 便利店早餐（没有 食べログ 评分，也不该有：这是「本地日常」）----------
KONBINI_CARD = {
    "name": "便利店早餐（Konbini）",
    "s": "7-11 / LAWSON / FamilyMart · 24 小时",
    "price": "¥300–800（≈13–35 元）",
    "sig": "饭团（鮭・ツナマヨ・明太子）+ 玉子三明治 + 现磨咖啡；炸鸡（からあげくん / FAMICHIKI）",
    "hours": "24 小时（多数店）",
    "pit": "饭团当天吃（海苔会软）；晚上 20:00–23:00 熟食便当常打折；热食在收银台旁保温箱",
    "route": "Day 2 / Day 4 / Day 5 早饭",
}


def konbini_entry():
    cred = CREDITS_JSON.get("f-konbini.jpg", {})
    cap = "便利店（参考图，非本店实拍）" + ("" if not cred else " · %s / Wikimedia Commons · %s" % (
        clean(cred.get("author") or "Wikimedia Commons", 40), cred.get("license") or "CC"))
    rows = [
        ["人均", "¥300–800（≈13–35 元）"],
        ["口碑", "便利店没有 食べログ 评分——它是<b>「本地日常」而不是「必吃」</b>：上班族、学生早上都在这里解决。下面写清买什么、怎么买、什么时候买。"],
        ["推荐指数", "🛒 本地日常 · 最稳的一顿早饭（不算「必吃」）"],
        ["招牌", "饭团、玉子三明治、现磨咖啡、炸鸡（からあげくん / FAMICHIKI）、咖喱面包"],
        ["营业", "24 小时（多数店；酒店旁与地铁站内都有）"],
        ["付款", "现金 / 交通 IC 卡（ICOCA・Suica）/ PayPay、信用卡（多数店）"],
        ["怎么去", "酒店旁的 7-11 / LAWSON；难波・恵美須町・天王寺站内也有"],
        ["顺路", "Day 2 / Day 4 / Day 5 早饭（出发前 5 分钟解决）"],
    ]
    shop = [
        ["推荐组合 · 正面", "饭团（鮭・ツナマヨ・明太子）+ 玉子三明治 + 一杯现磨咖啡 —— 一顿约 ¥400–700，这就是日本上班族的早上"],
        ["热食柜 · 正面", "LAWSON 的 からあげくん、FamilyMart 的 FAMICHIKI、7-11 的 アメリカンドッグ —— 现买现吃最香，别放凉"],
        ["怎么买 · 正面", "饭团在冷藏柜 / 收银台旁；热食在收银台边的保温箱直接点；咖啡是<b>自助机</b>：先拿杯子 → 机器上按确认 → 拿到收银台结账 —— 不会日语也能买"],
        ["吐槽 / 注意", "没有「好吃到惊艳」这回事；饭团是冷饭、偏咸，跟国内不一样；海苔放久会软 —— 想吃坐着吃热的，请看同一天的其他卡片"],
    ]
    rec = [
        "顺路安排：出发前 5 分钟解决，或买饭团 + 味噌汤带上车（近铁特急・新快速车厢内可以吃，普通地铁里别吃）。",
        "省钱：晚上 20:00–23:00 便当 / 熟食常贴 20%・30% 折扣贴纸，当夜宵买最划算。",
        "顺便：便利店的季节限定甜点（栗子 / 抹茶 / 布丁）和 100% 果汁也值得拿一个，比机场便宜一半。",
    ]
    pit = ["便利店不需要 食べログ 评分；想吃真正坐下来吃的早饭，看同一天卡片里的 天政・飯糰店 Onakasuita・CAFFE CIAO PRESSO。"]
    L = ['"f-konbini": {']
    L.append('  tone:"d3", ic:"🛒", t:"便利店早餐（7-11 / LAWSON / FamilyMart）", s:"酒店旁 / 车站内 · 24 小时 · 人均 ¥300–800",')
    L.append('  tag:["食べログ 无评分（便利店）","好评率 无（不看评分）","推荐 🛒 本地日常","24 小时"],')
    L.append('  img:["images/food/f-konbini.jpg","%s","%s"],' % (js(cap), js(cred.get("page", ""))))
    L.append('  cat:"便利店",')
    L.append('  rows:[%s],' % ",".join("[%s]" % ",".join('"%s"' % js(c) for c in r) for r in rows))
    L.append('  shop:[%s],' % ",".join("[%s]" % ",".join('"%s"' % js(c) for c in r) for r in shop))
    L.append('  rec:[%s],' % ",".join('"%s"' % js(r) for r in rec))
    L.append('  pit:[%s],' % ",".join('"%s"' % js(x) for x in pit))
    L.append('  src:[["食べログ（中文站）· 便利店不是餐厅，没有评分","https://tabelog.com/tw/"]]')
    L.append('}')
    return "\n".join(L)


def scard_konbini():
    c = KONBINI_CARD
    cred = CREDITS_JSON.get("f-konbini.jpg", {})
    cr = "" if not cred else "© %s · %s" % (clean(cred.get("author") or "Wikimedia Commons", 30), cred.get("license") or "CC")
    return "\n".join([
        '                <div class="scard" data-modal="f-konbini">',
        '                  <div class="cover">',
        '                    <img src="images/food/f-konbini.jpg" alt="便利店 参考图" loading="lazy">',
        '                    <span class="lv">🛒 本地日常</span>',
        '                    <span class="rt ok">24 小时</span>',
        '                    <span class="tier c">不用排队</span>',
        ('                    <span class="cr">%s</span>' % html_esc(cr)) if cr else '',
        '                  </div>',
        '                  <div class="cb">',
        '                    <div class="cname">%s</div>' % html_esc(c["name"]),
        '                    <div class="cmeta"><span class="sc">🛒 便利店</span><span>·</span><span>%s</span></div>' % html_esc(c["s"]),
        '                    <div class="cline"><span class="k">人均</span> %s</div>' % html_esc(c["price"]),
        '                    <div class="cline"><span class="k">招牌</span> %s</div>' % html_esc(c["sig"]),
        '                    <div class="cline"><span class="k">营业</span> %s</div>' % html_esc(c["hours"]),
        '                    <div class="cline warn"><span class="k">注意</span> %s</div>' % html_esc(c["pit"]),
        '                    <div class="cmore"><span class="cta">点开看怎么买 →</span><span>%s</span></div>' % html_esc(c["route"]),
        '                  </div>',
        '                </div>',
    ])



def day_block(day, cfg, newshops, oldshops):
    L = ['        <div class="rest">']
    L.append('          <h4>%s <span class="rname">%s</span> <span class="muted" style="font-size:12px">点任意一家店 → 好评 / 差评 + 招牌 + 人均</span></h4>' % (cfg["title"], cfg["rname"]))
    L.append('          <p class="restnote">%s</p>' % cfg["note"])
    L.append('          <div class="meals">')
    for meal in cfg["meals"]:
        time, mname, ic, where, note, ids = meal[:6]
        mlinks = meal[6] if len(meal) > 6 else []
        L.append('            <div class="meal">')
        L.append('              <div class="mhead"><span class="mtime">%s</span><span class="mname">%s %s</span><span class="mwhere">%s</span></div>' % (time, ic, mname, where))
        L.append('              <p class="mnote">%s</p>' % note)
        if mlinks:
            L.append('              <p class="mlinks">📖 %s</p>' % " · ".join(
                '<span class="lab" data-modal="%s">%s</span>' % (mid, label) for mid, label in mlinks))

        # ids 支持两种写法：
        #   1) 平铺 ["f-a", "f-b"]                        → 一个 .sgrid
        #   2) 按品类分组 [("拉面", ["f-a"], "说明"), …]   → 每品类一个小标题 + 一个 .sgrid
        groups = None
        if ids and isinstance(ids[0], (tuple, list)):
            groups = [(g[0], list(g[1]), (g[2] if len(g) > 2 else "")) for g in ids]

        def cards_for(sub):
            out = [scard(newshops[i]) for i in sub if i in newshops]
            out += [scard_existing(oldshops[i]) for i in sub if i in oldshops]
            if "f-konbini" in sub:
                out.append(scard_konbini())
            return out

        if groups:
            L.append('              <div class="mcats">')
            for gname, sub, ghint in groups:
                cs = cards_for(sub)
                if not cs:
                    continue
                L.append('                <div class="mcat-row">')
                L.append('                  <div class="mcat"><span class="cn">%s</span>%s<span class="cnt">%d 家</span></div>'
                         % (gname, ('<span class="ch">%s</span>' % ghint) if ghint else "", len(cs)))
                L.append('                  <div class="sgrid">')
                L.extend(cs)
                L.append('                  </div>')
                L.append('                </div>')
            L.append('              </div>')
        else:
            cs = cards_for(ids)
            if cs:
                L.append('              <div class="sgrid">')
                L.extend(cs)
                L.append('              </div>')
        L.append('            </div>')
    L.append('          </div>')
    if cfg.get("alts"):
        L.append('          <p class="mlinks">🔗 备选（要改路线 / 换时段才吃得到）：%s</p>' % " · ".join(
            '<span class="lab" data-modal="%s">%s</span>' % (mid, label) for mid, label in cfg["alts"]))
    if cfg.get("spots"):
        L.append(links(cfg["spots"]))
    if cfg.get("foot"):
        L.append('          <p class="restfoot">%s</p>' % cfg["foot"])
    L.append('        </div>')
    return "\n".join(L)


def fcard_existing(sid, info):
    """老弹窗（保留的店）在美食清单里的卡片。"""
    cr = info.get("credit", "")
    return "\n".join([
        '    <div class="fcard" data-modal="%s">' % sid,
        '      <div class="fcover"><img src="images/food/%s.jpg" alt="%s 参考图" loading="lazy">'
        '<span class="lv">%s</span><span class="rt %s">好评率 %s</span><span class="cr">%s</span></div>'
        % (sid, html_esc(info.get("cat", "")), info.get("stars", ""), rate_cls(info.get("good")),
           info.get("good", ""), html_esc(cr)),
        '      <div class="fn"><b>%s</b><span class="fc">%s</span></div>' % (html_esc(info.get("name", "")), html_esc(info.get("cat", ""))),
        '      <div class="fl"><span class="k">人均</span> <b>%s</b> · <span class="k">食べログ</span> <b>%s</b> · <span class="fgood">好评率 %s</span></div>'
        % (html_esc(info.get("price", "")), info.get("score", ""), info.get("good", "")),
        '      <div class="fl"><span class="k">招牌</span> %s</div>' % html_esc(clean(info.get("sig", ""), 46)),
        '    </div>',
    ])


def fcard_new(sh):
    cfg = sh["cfg"]
    sid = sh["id"]
    cred = CREDITS_JSON.get(sid + ".jpg", {})
    cr = "" if not cred else "© %s · %s" % (clean(cred.get("author") or "Wikimedia Commons", 30), cred.get("license") or "CC")
    return "\n".join([
        '    <div class="fcard" data-modal="%s">' % sid,
        '      <div class="fcover"><img src="images/food/%s.jpg" alt="%s 参考图" loading="lazy">'
        '<span class="lv">%s</span><span class="rt %s">好评率 %s%%</span><span class="cr">%s</span></div>'
        % (sid, html_esc(cfg["cat"]), stars_for(cfg["tier"], sh["score"]), rate_cls(sh["good_rate"]), sh["good_rate"], cr),
        '      <div class="fn"><b>%s</b><span class="fc">%s · %s</span></div>' % (html_esc(cfg["name"]), html_esc(cfg["cat"]), html_esc(TIER_LABEL[cfg["tier"]])),
        '      <div class="fl"><span class="k">人均</span> <b>%s</b> · <span class="k">食べログ</span> <b>%s</b><span class="k">／%s 条</span> · <span class="fgood">好评率 %s%%</span><span class="k">（抽样 %s 条，均分 %s）</span></div>'
        % (html_esc(cfg["price"]), sh["score"], format(sh["reviews"] or 0, ","), sh["good_rate"], sh["n"], sh["avg"]),
        '      <div class="fl"><span class="k">成绩</span> %s</div>' % (html_esc(" / ".join(sh["awards"][:3])) if sh["awards"] else "—"),
        '      <div class="fl"><span class="k">招牌</span> %s</div>' % html_esc(clean(cfg["dishes"], 52)),
        '      <div class="fl"><span class="k">营业</span> %s</div>' % html_esc(clean(cfg["hours"], 46)),
        '      <div class="fl warn"><span class="k">注意</span> %s</div>' % html_esc(clean(cfg["pit"], 60)),
        '    </div>',
    ])


def main():
    global CREDITS_JSON
    CREDITS_JSON = json.load(open(CREDITS, encoding="utf-8"))
    html = open(PAGE, encoding="utf-8").read()
    newshops = load_shops()

    # ---------- 1) 新店弹窗 ----------
    entries = []
    for sid, sh in newshops.items():
        if not os.path.exists(os.path.join(ROOT, "images/food", sid + ".jpg")):
            print("!! 缺封面", sid)
        if re.search(r'\n"%s": \{' % re.escape(sid), html):
            html = re.sub(r'\n"%s": \{.*?\n\}(?=,|\n)' % re.escape(sid),
                          lambda m: "\n" + modal_entry(sh), html, count=1, flags=re.S)
        else:
            entries.append(modal_entry(sh))
    if re.search(r'\n"f-konbini": \{', html):
        html = re.sub(r'\n"f-konbini": \{.*?\n\}(?=,|\n)', lambda m: "\n" + konbini_entry(), html, count=1, flags=re.S)
    else:
        entries.append(konbini_entry())
    if entries:
        anchor = '\n"f-alshon": {'
        assert anchor in html, "找不到插入点 f-alshon"
        html = html.replace(anchor, "\n" + ",\n".join(entries) + ",\n" + anchor.lstrip("\n"), 1)
    print("新店弹窗：", len(newshops))

    # ---------- 2) 撤下推荐的标记 ----------
    for sid, name, cat, score, rv, good, reason in DEMOTED:
        m = re.search(r'\n"%s": \{(.*?)\n\}(?=,|\n)' % re.escape(sid), html, re.S)
        if not m:
            print("!! 找不到撤下的弹窗", sid)
            continue
        body = m.group(1)
        if "已撤下推荐" in body:
            continue
        body = re.sub(r'"推荐 ★+☆*"', '"已撤下推荐 · ' + score + ' 分"', body)
        body = re.sub(r'"推荐指数","(?:[^"]*)"', '"推荐指数","<b>已撤下推荐</b>（2026-09 复查后不再推荐，原因见下方）"', body)
        rec = re.search(r'\n  rec:\[', body)
        warn = '<b>⚠️ 已撤下推荐：</b>本次复查后不再推荐这家 —— %s' % js(reason)
        if rec:
            body = body[: rec.end()] + '"%s",' % warn + body[rec.end():]
        html = html[: m.start()] + '\n"%s": {%s\n}' % (sid, body) + html[m.end():]
    print("标记撤下：", len(DEMOTED))

    # ---------- 2.5) 区域攻略弹窗（大阪烧 / 拉面 / 甜点）改成真实评分版 ----------
    for sid, text in AREA_FIX.items():
        m = re.search(r'\n"%s": \{.*?\n\}(?=,|\n)' % re.escape(sid), html, re.S)
        if not m:
            print("!! 找不到区域弹窗", sid)
            continue
        html = html[: m.start()] + "\n" + text + html[m.end():]
    print("区域弹窗复查改写：", len(AREA_FIX))

    # ---------- 3) 每天按餐次重写 ----------
    oldshops = load_existing(html)
    print("老店餐次卡片：", len(oldshops), sorted(oldshops))
    for day, cfg in DAY_PLAN.items():
        block = day_block(day, cfg, newshops, oldshops)
        pat = re.compile(r'(<section id="%s">.*?)\n        <div class="rest">.*?\n        </div>' % day, re.S)
        html, n = pat.subn(lambda m: m.group(1) + "\n" + block, html, count=1)
        if n == 0 and day == "d5":
            pat5 = re.compile(r'(<section id="%s">.*?)      </div>\n    </div>\n  </section>' % day, re.S)
            html, n = pat5.subn(lambda m: m.group(1) + block + "\n      </div>\n    </div>\n  </section>", html, count=1)
        print("day %s: %d" % (day, n))

    # ---------- 4) 美食清单区 ----------
    existing = {}
    for m in re.finditer(r'\n"(f-[a-z0-9\-]+)": \{(.*?)\n\}(?=,|\n)', html, re.S):
        sid, body = m.group(1), m.group(2)

        def f(name):
            r = re.search(r'\b%s:"([^"]*)"' % name, body)
            return r.group(1) if r else ""

        def row(key):
            r = re.search(r'\["%s","(.*?)"\]' % key, body)
            return r.group(1) if r else ""

        tag = re.search(r'\btag:\[(.*?)\]', body)
        tags = re.findall(r'"([^"]*)"', tag.group(1)) if tag else []
        cat = re.search(r'\n  cat:"([^"]*)"', body)
        cred = CREDITS_JSON.get(sid + ".jpg", {})
        existing[sid] = dict(
            id=sid, name=f("t"), cat=(cat.group(1) if cat else ""),
            score=next((t.replace("食べログ ", "") for t in tags if t.startswith("食べログ")), ""),
            good=next((t.replace("好评率 ", "") for t in tags if t.startswith("好评率")), ""),
            stars=next((t.replace("推荐 ", "") for t in tags if t.startswith("推荐")), ""),
            price=row("人均").split(" · ")[0], sig=row("招牌") or row("招牌 / 点单"),
            credit="" if not cred else "© %s · %s" % (clean(cred.get("author") or "Wikimedia Commons", 30), cred.get("license") or "CC"),
        )

    groups_html = []
    for title, sub, ids in CAT_GROUPS:
        cards = []
        for sid in ids:
            if sid in newshops:
                cards.append(fcard_new(newshops[sid]))
            elif sid in existing:
                cards.append(fcard_existing(sid, existing[sid]))
            else:
                print("!! 清单里找不到", sid)
        groups_html.append('\n    <div class="fgroup">\n      <h3>%s <span>%s</span></h3>\n      <div class="fgrid">\n%s\n      </div>\n    </div>'
                           % (title, sub, "\n".join(cards)))

    demote_html = ['\n    <div class="fgroup" id="demoted">\n      <h3>🚫 复查后撤下推荐（附真实评分，别专程去） <span>2026-09 复查：同一街区 / 同一品类都有更好的选择；点开仍可看原始数据</span></h3>\n      <div class="demote">']
    for sid, name, cat, score, rv, good, reason in DEMOTED:
        demote_html.append('        <div class="dcard" data-modal="%s">\n          <div class="dn">%s</div>\n'
                           '          <div class="ds"><span>%s</span> · <span>食べログ <b>%s</b></span><span>好评率 <b>%s</b></span></div>\n'
                           '          <div class="dr">%s</div>\n        </div>'
                           % (sid, html_esc(name), html_esc(cat), score, good, html_esc(reason)))
    demote_html.append('      </div>\n    </div>')
    # 按用户要求：文末只留「撤下名单」，按品类的 46 张卡片与 10 秒决策不再重复生成
    food_section = "\n".join(demote_html)

    start = html.index('    <div class="fgroup"')
    end = html.index('  </section>', start)
    html = html[:start] + food_section.lstrip("\n") + "\n" + html[end:]
    print("美食清单区重写完成")

    # ---------- 5) CSS ----------
    if "/* ==MEALS-CSS-START== */" in html:
        html = re.sub(r"  /\* ==MEALS-CSS-START==.*?==MEALS-CSS-END== \*/\n",
                      CSS.strip("\n") + "\n", html, count=1, flags=re.S)
    elif "/* ---- 按餐次的「吃什么」时间轴 ---- */" in html:
        # 旧版 CSS（无标记）：整段换成带标记的新版
        html = re.sub(r"  /\* ---- 按餐次的「吃什么」时间轴 ---- \*/.*?(\.dcard \.dr\{[^}]*\}\n)",
                      CSS.strip("\n") + "\n", html, count=1, flags=re.S)
    elif ".meals{" not in html:
        html = html.replace("</style>", CSS + "</style>", 1)

    # ---------- 6) 标题 / 说明文案 ----------
    # 文末只保留「数据怎么念 + 撤下名单」：10 秒决策与按品类的卡片不再重复出现
    html = re.sub(r'\s*<p class="foodlegend" style="margin-top:8px">👇.*?\n      </div>\n',
                  "\n", html, count=1, flags=re.S)
    html = html.replace('每个 Day 模块里的「吃什么」用的就是这同一套卡片，已按品种分组，随手点开即可（Day 2 京都 / Day 4 奈良·神户 的店也在下面）。',
                        '每个 Day 模块里都按「早饭 / 午饭 / 下午 / 晚饭 / 夜宵」排好，并写清「这时候你人在哪」；下面是评分口径说明，以及<b>复查后撤下推荐</b>的店。')
    for _h in ['吃什么 · 按「早 / 午 / 下午 / 晚 / 夜宵」排 <span class="tag">真实评分 · 好评率 · 撤下名单</span>',
               '吃什么 · 24 家实测清单 <span class="tag">人均 · 好评率 · 缺点</span>']:
        html = html.replace('<h2>' + _h + '</h2>',
                            '<h2>评分数据 & 复查后撤下的店 <span class="tag">数据怎么念 · 撤下名单</span></h2>')
    html = html.replace('<a href="#food">美食按餐次</a>', '<a href="#food">数据 · 撤下名单</a>')
    html = html.replace('<a href="#food">美食24家</a>', '<a href="#food">数据 · 撤下名单</a>')
    html = re.sub(r'<p class="foodlegend">📊.*?</p>',
                  '<p class="foodlegend">📊 <b>这张表怎么念：</b>数据来自 <b>食べログ（日本最大美食评分站）中文站</b>，2026 年 9 月逐店抓取。<b>评分</b>＝食べログ 5 分制（<b>3.5 以上算「好吃」、3.7 以上是难波一带的顶尖水平</b>；日本人给分很吝啬，别拿大众点评的 4.8 来比）；<b>评论数</b>＝该店累计评价条数（几百条以上才有参考价值）；<b>好评率</b>＝最新约 20 条评价里「≥3.5 分」占的比例（同时给抽样均分，避免只看一个数字）；<b>荣誉</b>＝食べログ「百名店」入选年份，是判断「值不值得专程」最硬的信号。<b>每家店都按真实评分重新筛过一遍</b>：分数和口碑不够的已经从推荐里撤下（见文末「复查后撤下」），页面里写的好评 / 差评都是食べログ 用户的原文（中文站机器翻译，我们只做断句整理）。</p>',
                  html, count=1)
    open(PAGE, "w", encoding="utf-8").write(html)
    print("wrote", PAGE, len(html), "bytes")


if __name__ == "__main__":
    main()
