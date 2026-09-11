#!/usr/bin/env python3
"""[已废弃 2026-09] 旧版：按「品种」分组生成每天的吃什么。
改成「按餐次（早/午/下午/晚/夜宵）」后请用 tools/build_meal_page.py + tools/meal_data.py。
保留此文件只为对照历史逻辑，不要再运行（会覆盖新的餐次版块）。

原说明：Generate the "吃什么" blocks of every Day section (and the cover images of the
24-shop 美食 list) from the single source of truth: the MODALS data of the page.

Run from the repo root:  python3 tools/build_food_sections.py

Idempotent: it re-reads its own output, so it can be re-run after editing the
MODALS entries (评分 / 好评率 / 招牌 / 缺点 all stay in sync everywhere).
"""
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "大阪关西5天4夜攻略.html")
CREDITS = os.path.join(ROOT, "images", "food", "credits.json")

# ---------------------------------------------------------------- 每家店的品类（弹窗里「同品类其他选择」按它分组）
CAT = {
    "f-daruma": "串炸", "f-gifuya": "串炸", "f-oyaji": "串炸", "f-yokozuna": "串炸", "f-tsurukame": "串炸",
    "f-mizuno": "大阪烧", "f-chibo": "大阪烧", "f-bonkura": "大阪烧",
    "f-otako": "章鱼烧", "f-takohachi": "章鱼烧",
    "f-jojoro": "拉面", "f-kinryu": "拉面", "f-kamukura": "拉面", "f-kamikura": "拉面",
    "f-jiyuuken": "咖喱洋食", "f-ginpei": "海鲜",
    "f-tamasei": "甜品", "f-rikuro": "甜品", "f-alshon": "甜品",
    "f-okaru": "乌冬荞麦", "f-matsuba": "乌冬荞麦", "f-kamabashi": "乌冬荞麦",
    "f-ishida": "神户牛", "f-amona": "神户牛",
}

# 图片说明里用的菜品名（封面图多为同类菜品参考图，不是本店实拍）
DISH = {
    "f-daruma": "大阪新世界的串炸", "f-gifuya": "大阪的串炸（串揚げ）", "f-oyaji": "串炸店门面（同类店铺）",
    "f-yokozuna": "横綱 的菜单看板（同一品牌 法善寺店实拍）", "f-tsurukame": "土手焼き（味噌炖牛筋串）",
    "f-mizuno": "大阪烧", "f-chibo": "千房 门面（同品牌 千日前店实拍）", "f-bonkura": "モダン焼き（大阪烧 + 炒面）",
    "f-otako": "本家 大たこ 门前排队（本店实拍）", "f-takohachi": "道顿堀的章鱼烧摊",
    "f-jojoro": "中华荞麦（酱油拉面）", "f-kinryu": "金龍ラーメン 的拉面（本店实拍）", "f-kamukura": "どうとんぼり神座 的拉面（本店实拍）",
    "f-kamikura": "酱油拉面（叉烧面）",
    "f-jiyuuken": "自由軒 的名物咖喱（本店实拍）", "f-ginpei": "鯛めし（鲷鱼饭）",
    "f-tamasei": "わらび餅（蕨饼）", "f-rikuro": "舒芙蕾式烤芝士蛋糕", "f-alshon": "蛋糕卷（下午茶）",
    "f-okaru": "咖喱乌冬（大阪）", "f-matsuba": "にしんそば（鲱鱼荞麦）", "f-kamabashi": "乌冬定食（奈良）",
    "f-ishida": "铁板烧神户牛", "f-amona": "洋食（汉堡排定食）",
}

# ---------------------------------------------------------------- 每一天展示哪些店、怎么分组
DAYS = {
    "d1": {
        "title": "🍽️ Day 1 吃什么",
        "rname": "（酒店周边，最省力）",
        "note": "🧭 <b>落地日就吃家门口。</b>新世界 / 日本桥 / 道顿堀全在步行 6–20 分钟圈内：13:45 把行李寄存在酒店后就能开吃。下面<b>按品种分组</b>，每张卡片上是<b>封面图 + 推荐指数 + 好评率 + 人均</b>，<b>点一下</b>看这家店的<b>好评原文 / 差评原文、招牌菜、排队情况、营业时间、怎么去</b>。",
        "spots": [("food-kuromon", "🏮", "黑门市场", "步行 10 分 · 17:00 前后收摊，想吃要趁早", "顺路")],
        "groups": [
            ("🍢 串炸 · 新世界（酒店步行 8–12 分）", "薄衣现炸 · 酱汁禁止二次蘸 · 落地第一晚最顺",
             ["f-daruma", "f-gifuya", "f-oyaji", "f-yokozuna", "f-tsurukame"]),
            ("🐙 章鱼烧 · 边走边吃（难波 / 法善寺 步行 15–20 分）", "¥500–900 一份 6–8 个，刚出锅极烫",
             ["f-otako", "f-takohachi"]),
            ("🥘 大阪烧 · 粉类（道顿堀 步行 15 分）", "份量大：两人点一份主食 + 一份豚平烧刚好",
             ["f-mizuno", "f-chibo", "f-bonkura"]),
            ("🍜 深夜一碗（道顿堀 · 24 小时 / 到早上 8 点）", "飞机早起 + 夜景收尾后，10 分钟就能坐进去",
             ["f-kinryu", "f-kamukura"]),
            ("🍛 中午简餐 & 🍡 下午甜品（日本桥 / 难波）", "日本桥站 B28 出口即到 · 难波站 3 分",
             ["f-jiyuuken", "f-tamasei", "f-alshon"]),
        ],
        "foot": "📷 卡片封面为公开授权的菜品 / 店铺参考图（Wikimedia Commons），<b>多数不是本店实拍</b>，点开后每张图都标明作者与授权；评分、好评率、排队与人均均来自 食べログ 逐店核对。",
    },
    "d2": {
        "title": "🍽️ Day 2 吃什么",
        "rname": "（京都为主 / 回大阪也行）",
        "note": "🧭 <b>京都吃饭两条原则：</b>① <b>11:00 开门就进</b>——13:00 之后祇园一片全在排队；② <b>别把午餐钉死在网红店</b>，巷子里的小店更快更好吃。下面 3 家都在祇园四条 / 京都站步行 1–5 分钟，午市比晚市便宜。",
        "spots": [("food-kyoto", "🍡", "锦市场 / 祇园怎么吃", "玉子烧、豆乳甜甜圈、海鲜串 · 16:00 后陆续收摊", "早去")],
        "groups": [
            ("🍜 京都站 · 出发前的一碗（06:00 开门）", "回程前也顺路 · 酱油系 · 排队约 20 分",
             ["f-kamikura"]),
            ("🍲 祇园 · 四条 午市（步行 1–3 分）", "乌冬 / 亲子丼 / 鲱鱼荞麦 · 11:00 开门即满",
             ["f-okaru", "f-matsuba"]),
        ],
        "foot": "📷 与 Day 1 相同：封面为公开授权的参考图，点开后可见作者与授权；价格与排队时间以 食べログ 2026 年 9 月核对值为准。",
    },
    "d3": {
        "title": "🍽️ Day 3 吃什么",
        "rname": "（大阪粉类 + 市场 + 串炸）",
        "note": "🧭 <b>今天一路从大阪城吃到新世界：</b>中午在道顿堀吃粉类或一碗拉面，下午在难波吃章鱼烧，晚上回酒店旁的新世界吃串炸收尾（吃完 6 分钟回房）。<b>不想排队就看卡片右下角的排队时间</b>，或者点开任意一家，用弹窗底部的「同品类其他选择」当场换店。",
        "spots": [("food-kuromon", "🏮", "黑门市场", "午餐主战场：现烤海鲜、河豚汤、和牛串 · 周六 11:30 前最舒服", "必吃"),
                  ("pit-crowd", "⚠️", "道顿堀河岸第一排", "排队久、价格高；同一家店在巷子里的分店常常更快", "避坑")],
        "groups": [
            ("🥘 大阪烧 · 粉类（道顿堀 / 难波）", "面糊 + 酱汁 + 美乃滋 · 排队 20–60 分要算进时间",
             ["f-mizuno", "f-chibo", "f-bonkura"]),
            ("🍜 拉面（本趟最推荐的一碗在这里）", "丈六 3.73 分 / 好评率 95% · 只收现金、7 席",
             ["f-jojoro", "f-kinryu", "f-kamukura"]),
            ("🐙 章鱼烧 · 边走边吃（道顿堀 / 法善寺）", "一份 6–8 个 · 下午逛心斋桥时顺手",
             ["f-otako", "f-takohachi"]),
            ("🍢 串炸 · 新世界（晚上回家门口吃）", "吃完步行 6 分钟回酒店 · 酱汁禁止二次蘸",
             ["f-daruma", "f-gifuya", "f-oyaji", "f-yokozuna", "f-tsurukame"]),
            ("🍛 想换口味：咖喱 / 海鲜 / 洋食（难波 · 道顿堀）", "一份百年咖喱，或一顿正经鱼料理",
             ["f-jiyuuken", "f-ginpei"]),
            ("🍡 甜品 · 下午茶（日本桥 · 难波 · 天王寺）", "玉製家 14:00 开卖 · りくろー 去阿倍野顺路",
             ["f-tamasei", "f-rikuro", "f-alshon"]),
        ],
        "foot": "📷 封面图为公开授权的菜品 / 店铺参考图（Wikimedia Commons，CC 授权），非本店实拍；好评率 = 该店最新约 20 条评价里 ≥3.5 分的比例。",
    },
    "d4": {
        "title": "🍽️ Day 4 吃什么",
        "rname": "（跟着目的地走）",
        "note": "🧭 <b>跟着今天去的地方吃：</b>去<b>奈良</b>就在近铁奈良站前拱廊街吃乌冬（去奈良公园的路上）；去<b>神户</b>就把预算花在午餐上——<b>神户牛午市 ¥1,000–1,999 就能吃到 A5</b>，晚餐同样的东西要贵一大截。",
        "spots": [("food-kyoto", "🍵", "宇治 / 伏见怎么吃", "中村藤吉本店抹茶甜品、宇治茶、伏见酒藏试饮", "甜品")],
        "groups": [
            ("🦌 奈良（近铁奈良站前拱廊街）", "去奈良公园的路上 · 饭点满座 · 只收现金 / PayPay",
             ["f-kamabashi"]),
            ("🥩 神户（三宫 · 花钟前）", "午市比晚市便宜一大截 · Ishida 必须预约",
             ["f-ishida", "f-amona"]),
        ],
        "foot": "📷 封面图为公开授权的菜品参考图，点开后可见作者与授权；神户牛价格请以店家当日菜单为准。",
    },
}

DAY5 = {
    "title": "🍽️ Day 5 吃什么",
    "rname": "（12:15 起飞，只有便利店时间）",
    "note": "🧭 <b>最后一天没有吃饭时间。</b>黑门市场 9:00 之后才开、你们 07:50 就要出发，所以早餐只有三个选项：<b>① 便利商店</b>（7-11 / LAWSON 的饭团 + 三明治 + 咖啡，最稳）；<b>② 酒店自助早餐</b>（约 ¥1,000 ≈44 元/人，06:30 前后开）；<b>③ 06:45 去通天阁拍清晨空景</b>（来回 15 分钟，回来再吃）。机场内的店贵 10–20%，只适合补漏。",
    "spots": [("pit-lastday", "🎁", "最后一天必做清单", "伴手礼必须在前一晚买完 · 07:30 退房 · 别排临空城", "别踩坑"),
              ("spot-kix", "✈️", "关西机场（KIX）", "T1 / T2 接驳 · 09:15 前到机场 · 退税柜台可能排队", "必看")],
    "groups": [],
    "foot": "",
}

# ---------------------------------------------------------------- 解析页面里的 MODALS 数据


def parse_shops(html):
    shops = {}
    for m in re.finditer(r'\n"(f-[a-z0-9\-]+)": \{(.*?)\n\}(?=,|\n)', html, re.S):
        sid, body = m.group(1), m.group(2)

        def field(name):
            r = re.search(r'\b%s:"([^"]*)"' % name, body)
            return r.group(1) if r else ""

        def row(key):
            r = re.search(r'\["%s","(.*?)"\]' % key, body)
            return r.group(1) if r else ""

        tag = re.search(r'\btag:\[(.*?)\]', body)
        tags = re.findall(r'"([^"]*)"', tag.group(1)) if tag else []
        pit = re.search(r'\bpit:\["(.*?)"', body, re.S)
        shops[sid] = {
            "id": sid,
            "name": field("t"),
            "s": field("s"),
            "tags": tags,
            "score": next((t.replace("食べログ ", "") for t in tags if t.startswith("食べログ")), ""),
            "good": next((t.replace("好评率 ", "") for t in tags if t.startswith("好评率")), ""),
            "stars": next((t.replace("推荐 ", "") for t in tags if t.startswith("推荐")), ""),
            "price": row("人均").split(" · ")[0],
            "queue": row("推荐指数").split("·")[-1].strip() if "·" in row("推荐指数") else "",
            "sig": row("招牌"),
            "pit": strip_tags(pit.group(1)).split("；")[0] if pit else "",
            "cat": CAT.get(sid, ""),
            "img": "images/food/%s.jpg" % sid,
        }
    return shops


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "").replace("&nbsp;", " ").strip()


def short(s, n=26):
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def good_num(pct):
    try:
        return int(pct.replace("%", ""))
    except ValueError:
        return 0


def rate_cls(pct):
    n = good_num(pct)
    return "" if n >= 75 else ("mid" if n >= 55 else "low")


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def credit_short(credits, sid):
    c = credits.get(sid + ".jpg")
    if not c:
        return ""
    author = c["author"] or "Wikimedia Commons"
    author = re.sub(r"\s+", " ", author)[:34]
    return "© %s · %s" % (author, c["license"] or "CC")


NON_DISH = re.compile(r"(营业|预约|席位|支持|禁止|收费|加收|必须|免费|无休|不定休)")


def card(shop, credits):
    head = shop["sig"].split("；")[0]
    dishes = [x.strip() for x in re.split(r"[、，]", head) if x.strip()]
    dishes = [d for d in dishes if d and len(d) <= 16 and "。" not in d]
    only = [d for d in dishes if not NON_DISH.search(d)]
    dishes = only or dishes
    sig_txt = "、".join(dishes[:2]) if dishes else short(shop["sig"], 22)
    cat_line = shop["s"].split(" · 人均")[0]
    cr = credit_short(credits, shop["id"])
    L = []
    L.append('              <div class="scard" data-modal="%s">' % shop["id"])
    L.append('                <div class="cover">')
    L.append('                  <img src="%s" alt="%s 参考图" loading="lazy">' % (shop["img"], esc(shop["cat"] or shop["name"])))
    L.append('                  <span class="lv">%s</span>' % shop["stars"])
    L.append('                  <span class="rt %s">好评率 %s</span>' % (rate_cls(shop["good"]), shop["good"]))
    if cr:
        L.append('                  <span class="cr">%s</span>' % esc(cr))
    L.append('                </div>')
    L.append('                <div class="cb">')
    L.append('                  <div class="cname">%s</div>' % esc(shop["name"]))
    L.append('                  <div class="cmeta"><span class="sc">食べログ %s</span><span>·</span><span>%s</span></div>' % (shop["score"], esc(cat_line)))
    L.append('                  <div class="cline"><span class="k">人均</span> %s</div>' % esc(shop["price"]))
    L.append('                  <div class="cline"><span class="k">招牌</span> %s</div>' % esc(sig_txt))
    if shop["pit"]:
        L.append('                  <div class="cline warn"><span class="k">注意</span> %s</div>' % esc(short(shop["pit"], 30)))
    L.append('                  <div class="cmore"><span class="cta">点开看好评 / 差评 →</span><span>%s</span></div>' % esc(short(shop["queue"], 16)))
    L.append('                </div>')
    L.append('              </div>')
    return "\n".join(L)


def spot(item):
    mid, ic, title, sub, badge = item
    bcls = {"必吃": "g", "顺路": "b", "早去": "o", "避坑": "r", "别踩坑": "r",
            "必看": "g", "甜品": "b", "推荐": "g"}.get(badge, "o")
    return ('          <div class="spot" data-modal="%s">\n'
            '            <div class="ic">%s</div>\n'
            '            <div class="body"><div class="t">%s<span class="badge %s">%s</span></div><div class="s">%s</div></div>\n'
            '            <div class="arrow">›</div>\n'
            '          </div>') % (mid, ic, title, bcls, badge, sub)


def day_block(cfg, shops, credits):
    L = ['        <div class="rest">']
    L.append('          <h4>%s <span class="rname">%s</span> <span class="muted" style="font-size:12px">点任意一家店 → 好评 / 差评 + 招牌 + 人均</span></h4>' % (cfg["title"], cfg["rname"]))
    L.append('          <p class="restnote">%s</p>' % cfg["note"])
    for sp in cfg.get("spots", []):
        L.append(spot(sp))
    for gtitle, gnote, ids in cfg["groups"]:
        L.append('          <div class="foodgroup">')
        L.append('            <h5>%s <span>%s</span></h5>' % (gtitle, gnote))
        L.append('            <div class="sgrid">')
        for sid in ids:
            L.append(card(shops[sid], credits))
        L.append('            </div>')
        L.append('          </div>')
    if cfg.get("foot"):
        L.append('          <p class="restfoot">%s</p>' % cfg["foot"])
    L.append('        </div>')
    return "\n".join(L)


def main():
    html = open(PAGE, encoding="utf-8").read()
    credits = json.load(open(CREDITS, encoding="utf-8")) if os.path.exists(CREDITS) else {}
    shops = parse_shops(html)
    missing = [s for s in shops if not os.path.exists(os.path.join(ROOT, shops[s]["img"]))]
    if missing:
        print("!! 缺少封面图：", ", ".join(missing))

    # 1) 给每个 f-* 弹窗补上封面图 + 品类
    def inject(m):
        sid, body = m.group(1), m.group(2)
        if "\n  img:" in body or "\n  cat:" in body:
            return m.group(0)
        c = credits.get(sid + ".jpg")
        if not c:
            return m.group(0)
        author = re.sub(r"\s+", " ", c["author"] or "Wikimedia Commons")[:60]
        dish = DISH.get(sid, shops.get(sid, {}).get("cat", ""))
        cap = "%s（参考图，非本店实拍）· %s / Wikimedia Commons · %s" % (dish, author, c["license"] or "CC")
        cap = cap.replace('"', "”")
        add = '\n  img:["images/food/%s.jpg","%s","%s"],\n  cat:"%s",' % (sid, cap, c["page"], CAT.get(sid, ""))
        # 插在 tag:[...] 之后
        m2 = re.search(r'\n(\s*)tag:\[.*?\],', body, re.S)
        if m2:
            body = body[: m2.end()] + add + body[m2.end():]
        else:
            body = body + add
        return '\n"%s": {%s\n}' % (sid, body)

    html = re.sub(r'\n"(f-[a-z0-9\-]+)": \{(.*?)\n\}(?=,|\n)', inject, html, flags=re.S)

    # 2) 美食清单大卡：加封面图（幂等：已有封面图就跳过）
    src = html

    def fcover(m):
        sid = m.group(1)
        if src[m.end():m.end() + 80].lstrip().startswith('<div class="fcover"'):
            return m.group(0)
        c = credits.get(sid + ".jpg")
        if not c:
            return m.group(0)
        s = shops.get(sid, {})
        return (m.group(0) + '\n      <div class="fcover">'
                '<img src="images/food/%s.jpg" alt="%s 参考图" loading="lazy">'
                '<span class="lv">%s</span><span class="rt %s">好评率 %s</span>'
                '<span class="cr">%s</span></div>'
                % (sid, esc(s.get("cat", "")), s.get("stars", ""), rate_cls(s.get("good", "")),
                   s.get("good", ""), esc(credit_short(credits, sid))))

    html = re.sub(r'<div class="fcard" data-modal="(f-[a-z0-9\-]+)">', fcover, src)

    # 3) 每个 Day 的「吃什么」整块重写
    for day, cfg in DAYS.items():
        block = day_block(cfg, shops, credits)
        pat = re.compile(r'(<section id="%s">.*?)        <div class="rest">.*?\n        </div>' % day, re.S)
        html, n = pat.subn(lambda m: m.group(1) + block, html, count=1)
        print("day %s: replaced %d block" % (day, n))

    # 4) Day 5 插入（原本没有「吃什么」块）
    if 'Day 5 吃什么' not in html:
        block = day_block(DAY5, shops, credits)
        pat = re.compile(r'(<section id="d5">.*?)      </div>\n    </div>\n  </section>', re.S)
        html, n = pat.subn(lambda m: m.group(1) + block + "\n      </div>\n    </div>\n  </section>", html, count=1)
        print("day d5: inserted %d block" % n)

    open(PAGE, "w", encoding="utf-8").write(html)
    print("cards per day:", {d: sum(len(g[2]) for g in c["groups"]) for d, c in DAYS.items()}, "| d5 0")
    print("wrote", PAGE)


if __name__ == "__main__":
    main()
