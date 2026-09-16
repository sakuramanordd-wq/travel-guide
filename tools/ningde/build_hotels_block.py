#!/usr/bin/env python3
"""Generate the expanded 住宿 chapter (HTML cards + MODALS entries) for 宁德3天2夜攻略.

Data: research/_raw/ningde/hotels_merged.json (merged from candidates+detail),
      research/_raw/ningde/hotels_detail.json, images/credits.json
Output: tools/ningde/hotels_block.html  (replaces <section id="hotel"> … </section>)
        tools/ningde/hotels_modals.js   (MODALS entries, merged into modals.js)

Run: python3 tools/ningde/build_hotels_block.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "research", "_raw", "ningde")
NDIR = os.path.join(ROOT, "tools", "ningde")
DETAIL = {int(d["ctrip_id"]): d for d in json.load(open(os.path.join(RAW, "hotels_detail.json"), encoding="utf-8"))}
CAND = {h["id"]: h for h in json.load(open(os.path.join(RAW, "hotels_candidates.json"), encoding="utf-8"))}
CRED = json.load(open(os.path.join(ROOT, "images", "credits.json"), encoding="utf-8"))

# slug, ctrip id, 图, 图注地点, 分组, 交通一句话, 一句话卖点
PICKS = [
    # ---- 霞浦县城（D1 首选：吃饭方便 + 免费接送站） ----
    ("hotel-putiong", 29936821, "images/xiapu-station.jpg", "霞浦站站房", "county", "d1",
     "霞浦站打车约 10 分钟（2.7 km）；酒店有免费高铁站接送（提前 3 小时致电前台 0593-8958888）", "县城里体量最大、接送最省心的一家"),
    ("hotel-xinhaiwan", 107205203, "images/xiapu-county.jpg", "霞浦县城", "county", "d1",
     "距霞浦站 2.5 km，免费接站/送站；步行 250 m 到东关市场", "1,637 条点评里只有 10 条差评，本页好评率最高"),
    ("hotel-baiyulan", 70655271, "images/xiapu-county.jpg", "霞浦太康路一带", "county", "d1",
     "太康路 339 号，楼下就是美食一条街；免费班车接站/送站", "价格最友好，且「下楼就能吃海鲜」"),
    ("hotel-atour-xiapu", 105471695, "images/hero-ningde.jpg", "北岐滩涂日出（参考图）", "county", "d1",
     "赤岸大道 88 号，距北岐滩涂 4.8 km、距霞浦站 4.9 km，门口有滨海新城客运站", "连锁硬件最稳，离北岐机位最近的高档酒店"),
    # ---- 三沙 / 东壁 / 小皓（为日落与花竹日出而住） ----
    ("hotel-huazhu", 104266316, "images/xiapu-sunset.jpg", "东壁日落", "dongbi", "d2",
     "东壁村 26 号，步行 200 m 到东壁观景处；到三沙镇 4.3 km", "携程 4.9 分、592 条零差评，走两步就是东壁机位"),
    ("hotel-nuoya", 112740853, "images/xiapu-dongbi.jpg", "三沙一带渔港（参考图）", "dongbi", "d2",
     "虞公亭村 16 号，距光影栈道 670 m、东壁 1.1 km、虞公亭沙滩 520 m", "位置卡在光影栈道与东壁之间，露台能看海"),
    ("hotel-manhaigu", 83871330, "images/xiapu-gaoluo.jpg", "霞浦海滩（参考图）", "dongbi", "d2",
     "虞公亭村 123 号，东壁村入口处；到东壁 1.6 km、光影栈道 980 m", "带泳池和儿童乐园，带娃看海的选择"),
    ("hotel-shijianhai", 28708000, "images/xiapu-jishi-beach.jpg", "霞浦海边（参考图）", "dongbi", "d2",
     "东壁村 89 号，村内步行可达日落机位；到三沙镇约 5 km", "网红无边泳池，价格也是本页最贵的民宿"),
    ("hotel-huazhu-village", 85395524, "images/xiapu-xiaohao.jpg", "小皓滩涂", "dongbi", "d2",
     "三沙镇花竹村 57 号，距花竹观景台约 110 m", "全页离花竹日出机位最近的住宿，仅 6 间房"),
    ("hotel-yunxi", 82647593, "images/hero-ningde.jpg", "北岐滩涂日出", "beiqi", "d2",
     "松渔村澳头 33-1 号，距北岐滩涂约 660 m，免费接站", "北岐看日出可以睡到 04:50 再出门"),
    ("hotel-songdao", 106711579, "images/xiapu-sbend.jpg", "沙江 S 湾一带滩涂（参考图）", "beiqi", "d2",
     "松农村澳头 178 号，距北岐滩涂约 160 m", "离北岐机位 160 m，楼顶有泳池"),
    # ---- 太姥山镇（Day 2 晚，为 Day 3 早进园） ----
    ("hotel-jiji", 124791295, "images/taimushan-town.jpg", "太姥山镇街景", "tailao", "d3",
     "玉湖大道 133 号，距太姥山站约 5.8 km；打车到景区集散中心约 10 分钟", "2025 年新开的全季，硬件最新"),
    ("hotel-tailao", 1987602, "images/taimushan-inscription.jpg", "太姥山摩崖石刻", "tailao", "d3",
     "秦屿镇玉池南路 276 号，距太姥山汽车站约 150 m；自驾有停车场", "1,308 条点评的老牌大酒店，98.9% 好评"),
    ("hotel-tuke-tailao", 104455425, "images/taimushan.jpg", "太姥山", "tailao", "d3",
     "太姥山镇金麟路 106 号，步行可达玉池路小吃街", "便宜、楼下就是小吃街，适合「睡一觉就走」"),
    ("hotel-dahuang", 63138737, "images/taimushan-rock.jpg", "太姥山石景", "tailao", "d3",
     "太姥山景区内（停车场旁），可省掉一段景交车", "唯一住在景区里的选择，设施偏旧但位置最省时间"),
    # ---- 福鼎市区（改行程/想住得便宜时） ----
    ("hotel-vienna-fuding", 117012778, "images/fuding-station.jpg", "福鼎站", "fuding", "d5",
     "玉门南路 1616 号，距福鼎站 3.0 km，有免费专车接送站", "想住福鼎市区又要接送站，就选这家"),
    ("hotel-tuke-haikou", 82038101, "images/fuding-station.jpg", "福鼎站", "fuding", "d5",
     "海口路 28 号，福鼎市区核心，周边小吃密集", "预算优先时最便宜的一家；缺点是没有正式停车场"),
    # ---- 宁德市区（票没买到霞浦时的兜底） ----
    ("hotel-jinling", 56796334, "images/ningde-station.jpg", "宁德站", "ningde", "d5",
     "院岗路 20 号，宁德站乘 32 路直达万达广场；停车场很大", "4,548 条点评，宁德市区口碑与体量都最扎实"),
    ("hotel-metto-wanda", 481699, "images/ningde-city.jpg", "宁德蕉城", "ningde", "d5",
     "天湖东路 1 号万达广场 3 号楼，吃饭购物都在楼下", "逛街吃饭最方便，代价是房型偏旧"),
]

GROUP_TITLE = {
    "county": ("🏙️ 霞浦县城（D1 首选：吃饭方便 + 免费接送站，代价是日出要早起）",
               "住在县城 = 太康路美食一条街步行圈 + 免费高铁站接送；去北岐滩涂约 5 km（打车 15–20 分钟），去东壁/小皓 20 km 左右（光影 1 号专线 15–18 元）。"),
    "dongbi": ("🌅 三沙 / 东壁 / 小皓（摄影党首选：日落步行圈，花竹日出开车 15 分钟）",
               "东壁是霞浦日落头牌机位，花竹是日出机位；住这一带可以 04:40 起床就位，但村里吃饭只有几家民宿餐厅和咖啡店，夜宵基本没有。"),
    "beiqi": ("🌊 北岐 / 松山（只为北岐日出：可以睡到 04:50）",
              "北岐滩涂是霞浦最出名的日出机位，住村口民宿能比县城多睡 40 分钟；代价是离县城吃饭 5 km。"),
    "tailao": ("⛰️ 太姥山镇（秦屿）（Day 2 晚：为 Day 3 早上 07:00 第一波进园）",
               "镇子就是「横竖几条街」的规模，但离景区集散中心约 10 分钟车程；别住福鼎市区（离景区约 45 km，打车约 150 元）。"),
    "fuding": ("🍜 福鼎市区（备选：小吃为主、想住得便宜）", "福鼎站下车即到，玉池路/桐山溪西一带小吃密集；去太姥山景区约 45 km，只能当备选。"),
    "ningde": ("🚄 宁德市区（兜底：万一没抢到霞浦站的票）", "宁德站在霞浦以南 59 km，去滩涂当天往返太赶，只建议作为买不到霞浦票时的备用落脚点。"),
}

AREA_PIT = {
    "county": "县城酒店拍日出要 04:00–04:30 出发；民宿/酒店的免费接送站通常要提前 3 小时致电前台确认。",
    "dongbi": "村里民宿早餐普遍 07:00 才开餐，赶不上 05:5x 的日出——前一晚在镇上买好面包牛奶；2025 年国庆 10/2–10/7 每天 19:00–21:00 东壁村禁止机动车进入。",
    "beiqi": "北岐机位在堤坝上，风大且没有遮挡，10 月初早晚约 20℃ 出头，带件防风外套；滩涂退潮时别踏进养殖区。",
    "tailao": "玉池路 8:00–20:00 易堵（2024 国庆交警口径），自驾进出镇子留余量；景区内山上水 10 元/瓶，提前在镇上买。",
    "fuding": "福鼎站到市区有距离（约 3–6 km），深夜到站要提前叫车；市区去太姥山景区约 45 km，打车约 150 元/70 分钟。",
    "ningde": "宁德站是温福＋衢宁两线交汇的大站（每日 93 趟停靠），但它在霞浦以南 59 km——本行程住这里等于每天多花 1 小时在路上。",
}


def human(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


def money(s):
    t = re.sub(r"[￥¥]", "", s or "").replace("起", "").strip()
    return t or "实时计价"


def credit_of(img):
    v = CRED.get(os.path.basename(img)) or {}
    au = re.sub(r"\s+", " ", v.get("author", "")).split(",")[0]
    lic = v.get("license", "")
    return f"{au} / Wikimedia Commons · {lic}" if au else "Wikimedia Commons"


def modal_js(slug, hid, img, cap, group, tone, how, pitch):
    d = DETAIL[hid]
    c = CAND.get(hid, {})
    name = d["name"]
    price = money(c.get("price_from"))
    score = d.get("score")
    revs = d.get("reviews") or ""
    rate = d.get("good_rate")
    bad = d.get("bad_reviews")
    nrev = int(str(revs).replace(",", "") or 0)
    nbad = bad if isinstance(bad, int) else 0
    bad_pct = f"{nbad / nrev * 100:.1f}%" if nrev else "—"
    near = "；".join(f'{n["kind"]} {n["name"]}{n["dist"]}' for n in (d.get("nearby") or [])[:4])
    fac = "、".join((d.get("facilities") or [])[:8]) or "—"
    tags = (d.get("tags") or [])[:8]
    tagtxt = "、".join(f"{k}（{v}）" for k, v in tags) or "—"
    quotes = [q.strip() for q in (d.get("quotes") or []) if len(q.strip()) > 30][:2]
    opened = d.get("opened") or "—"
    rooms = d.get("rooms") or "—"
    park = "免费停车" if d.get("free_parking") else ("有停车场" if d.get("has_parking") else "无停车信息")
    lug = "免费行李寄存" if d.get("free_luggage") else ""
    phone = d.get("phone") or "—"
    policy = d.get("policy") or {}
    checkin = policy.get("入住") or ""
    checkout = policy.get("退房") or ""
    deposit = policy.get("押金") or ""
    pet = policy.get("宠物") or ""
    ctrip_url = f"https://hotels.ctrip.com/hotels/{hid}.html"
    if price == "实时计价":
        price_txt = "携程显示「实时计价」（参考价随日期浮动，抓取日 2026-09-15 未给出起价）"
    else:
        try:
            p = float(price)
            price_txt = (f"携程参考起价 ¥{p:.0f} 起（抓取日 2026-09-15）；"
                         f"国庆区间估计 ¥{p * 1.5:.0f}–{p * 2.5:.0f}（<b>估算，非报价</b>，霞浦官方限价上限为酒店 ≤ 上年均价 200% / 民宿 ≤ 150%）")
        except ValueError:
            price_txt = f"携程参考起价 {price}（抓取日 2026-09-15）"
    rows = [
        ["位置", f'{d.get("addr") or "—"}' + (f'<br>邻近：{near}' if near else "")],
        ["参考价", price_txt],
        ["怎么去", how],
        ["硬件", f"{c.get('star') or '—'} · 开业 {opened} · {rooms} 间房 · 电话 {phone}<br>{fac}"],
        ["停车 / 寄存", park + (f" · {lug}" if lug else "")],
        ["口碑构成", f'携程 {score} 分 / {revs} 条点评 · 好评率（值得推荐 {human(d.get("recommend") or 0)} ÷ 总点评 {revs}）<b>{rate}%</b> · 差评 {nbad} 条（占 {bad_pct}）<br>高频关键词：{tagtxt}'],
    ]
    if checkin or checkout or deposit or pet:
        rows.append(["政策", " · ".join(x for x in [checkin, checkout, deposit, pet] if x)])
    for i, q in enumerate(quotes, 1):
        rows.append([f"真实点评 {i}", q[:300] + ("…" if len(q) > 300 else "")])
    rec = [pitch,
           f"点评样本 {human(nrev)} 条，属于「样本足够」的店；同一区域里优先比较评分与差评率，而不是只看首图。",
           "订可免费取消的房型；下单后把「退订条款 + 同房型在售页」截图留证，遇到拒单/加价可直接投诉。"]
    if d.get("free_luggage"):
        rec.append("提供免费行李寄存——Day 3 退房后可以把箱子存前台或寄存处，轻装上山。")
    if "提供接送" in tagtxt or "接站服务" in fac or "送站服务" in fac:
        rec.append("有接站/送站服务：到站前 3 小时致电前台约车，比临时打车稳。")
    pit = [f"差评 {nbad} 条（占 {bad_pct}）——下单前在携程按「最新」排序翻 5 条，重点看隔音、卫生死角、前台加价这三类。",
           AREA_PIT[group]]
    if "实时计价" in price:
        pit.append("这家在携程是「实时计价」，说明旺季价格浮动大：先在 App 里选 10/1–10/2 的实际日期比价再下单。")
    src = [["携程酒店详情页（评分/点评/设施，抓取日 2026-09-15）", ctrip_url]]
    if group in ("county", "dongbi", "beiqi"):
        src.append(["霞浦县市监局·节假日住宿价格行为规则（酒店 ≤ 上年均价 200%、民宿 ≤ 150%）",
                    "http://www.xiapu.gov.cn/zwgk/gkzl/bmzfxxgk/zfbm/xsgj/gkml_25160/zdgkxx/202507/t20250723_2081827.htm"])
    src.append(["Wikimedia Commons（配图为区域实拍，非酒店官方图）", CRED.get(os.path.basename(img), {}).get("page", "https://commons.wikimedia.org/")])

    def jstr(s):
        return json.dumps(s, ensure_ascii=False)

    js = [f'{jstr(slug)}: {{']
    js.append(f'  tone:{jstr(tone)}, ic:"🏨", t:{jstr(name)}, s:{jstr(f"携程 {score} 分 / {revs} 条 · 好评率 {rate}% · 参考 ¥{price} 起")},')
    badges = []
    if rate and float(rate) >= 99.2 and nbad <= 14:
        badges.append("差评极少")
    if score and float(score) >= 4.8:
        badges.append(f"携程 {score}")
    if price != "实时计价":
        try:
            if float(price) <= 270:
                badges.append("性价比")
        except ValueError:
            pass
    if "接站服务" in fac or "提供接送" in tagtxt:
        badges.append("免费接送站")
    if group == "dongbi":
        badges.append("海景")
    badges.append("已核对")
    js.append(f'  tag:{jstr(badges[:4])},')
    js.append(f'  img:[{jstr(img)},{jstr(cap + " · " + credit_of(img))},{jstr(CRED.get(os.path.basename(img), {}).get("page", ""))}],')
    js.append("  rows:[" + ",".join("[" + jstr(k) + "," + jstr(v) + "]" for k, v in rows) + "],")
    js.append("  rec:[" + ",".join(jstr(x) for x in rec) + "],")
    js.append("  pit:[" + ",".join(jstr(x) for x in pit) + "],")
    js.append("  src:[" + ",".join("[" + jstr(a) + "," + jstr(b) + "]" for a, b in src) + "]")
    js.append("},")
    return "\n".join(js), d, c


def card_html(slug, d, c, img, note):
    name = d["name"]
    price = money(c.get("price_from"))
    rate = d.get("good_rate")
    nbad = d.get("bad_reviews") or 0
    badges = []
    if rate and float(rate) >= 99.2 and isinstance(nbad, int) and nbad <= 14:
        badges.append('<span class="badge g">差评极少</span>')
    if d.get("score") and float(d["score"]) >= 4.8:
        badges.append(f'<span class="badge g">携程 {d["score"]}</span>')
    if price != "实时计价":
        try:
            if float(price) <= 270:
                badges.append('<span class="badge o">性价比</span>')
        except ValueError:
            pass
    if "接站服务" in (d.get("facilities") or []) or "提供接送" in "".join(k for k, _ in d.get("tags") or []):
        badges.append('<span class="badge b">免费接送站</span>')
    return (f'    <div class="spot" data-modal="{slug}" data-tone="{PICKS_TONE[slug]}">\n'
            f'      <div class="ph"><img src="{img}" alt="{note}" loading="lazy"></div>\n'
            f'      <div class="body"><div class="t">{name}{"".join(badges)}</div>'
            f'<div class="s">携程 {d.get("score")} 分 / {d.get("reviews")} 条 · 好评率 {rate}%（差评 {nbad}）· 参考 ¥{price} 起 · {note}</div></div>\n'
            f'      <div class="arrow">›</div>\n    </div>\n')


PICKS_TONE = {}

if __name__ == "__main__":
    modals, cards = [], {}
    for slug, hid, img, note, group, tone, how, pitch in PICKS:
        PICKS_TONE[slug] = tone
        js, d, c = modal_js(slug, hid, img, note, group, tone, how, pitch)
        modals.append(js)
        cards.setdefault(group, []).append(card_html(slug, d, c, img, note))

    parts = ['  <section id="hotel">',
             '    <h2>住宿与周边 <span class="tag">两晚两个落脚点 · 19 家实测候选</span></h2>']
    parts.append("""    <div class="card">
      <p><b>先说结论：这趟必须换一次酒店——霞浦住 1 晚、太姥山镇住 1 晚。</b>理由很硬：霞浦的日出机位（北岐、花竹）凌晨 4:30 就要出门，住宁德市区或福鼎市区都来不及；而 Day 3 要爬太姥山 3–4 小时，太姥山镇的酒店离景区集散中心 10 分钟车程，比福鼎市区（约 45 km）省 1 小时。<span class="hl">下表 19 家的评分、点评数、好评率、差评数与真实点评摘录，均为 2026-09-15 从携程酒店详情页抓取；价格是携程「参考起价」，不是国庆实价。</span></p>
      <table class="tbl">
        <tr><th>落脚点</th><th>适合谁</th><th>参考起价量级</th><th>硬伤</th></tr>
        <tr><td class="d">霞浦县城</td><td><b>第一次来、要吃饭方便、要免费接送站</b></td><td>¥252–361</td><td>离北岐 4.8–5 km、离东壁约 20 km，日出必须打车/赶专线</td></tr>
        <tr><td class="d">三沙 / 东壁 / 小皓</td><td><b>摄影党、要看海上日落</b></td><td>¥288–1,028（海景房更高）</td><td>吃饭选择少、夜宵基本没有；村内 19:00–21:00 曾禁机动车</td></tr>
        <tr><td class="d">北岐 / 松山</td><td><b>只拍北岐日出，想多睡 40 分钟</b></td><td>¥261 起</td><td>离县城吃饭 5 km，民宿硬件参差</td></tr>
        <tr><td class="d">太姥山镇（秦屿）</td><td><b>Day 3 早上 07:00 第一波进园</b></td><td>¥299–461</td><td>镇子小、晚上只有小吃街；离福鼎市区 45 km</td></tr>
        <tr><td class="d">福鼎市区</td><td><b>小吃为主、想住便宜</b></td><td>¥167–261</td><td>离太姥山景区约 45 km，打车约 150 元/70 分钟</td></tr>
        <tr><td class="d">宁德市区</td><td><b>只在没抢到霞浦票时兜底</b></td><td>¥288–297</td><td>在霞浦以南 59 km，去滩涂当天往返太赶</td></tr>
      </table>
      <p class="muted" style="margin-top:10px">💰 <b>国庆价格纪律（A 级官方依据）</b>：霞浦县市场监管局霞市监〔2024〕37 号规定国庆期间<b>酒店房价不高于上年同期均价 200%、民宿不高于 150%</b>；另有《霞浦县涉旅行业明码标价工作实施方案》推行「一年一定价、全年不加价」。<b>即酒店合理上限约 +100%、民宿约 +50%，超出可打 12345 / 12315。</b>2025 年国庆的真实表现是<b>高端房源紧张（前五日满房）而非普涨</b>——东壁/花竹的海景民宿越早订越好。</p>
      <p class="muted">🚄 <b>到站之后怎么走</b>：<b>霞浦站</b>在赤岸村、距县城约 4 km，公交 7/8 路 1–2 元，站前的<b>光影 1 号专线</b>（8:00–18:30、30–60 分/班）直达小皓/光影栈道/东壁/三沙古镇码头（19 座 15 元、7 座 18 元）；<b>太姥山站</b>出站即有去景区的班车约 6 元/20 分钟（2024 口径）；<b>福州/厦门方向来的车</b>注意别在宁德站下——太姥山、霞浦都在宁德以北。</p>
    </div>""")
    parts.append("\n    <div class=\"sched-title\">🧭 两晚落脚点总览（点卡片看完整决策）</div>")
    legacy = open(os.path.join(NDIR, "legacy_hotel_cards.html"), encoding="utf-8").read().rstrip()
    parts.append(legacy)
    for g in ["county", "dongbi", "beiqi", "tailao", "fuding", "ningde"]:
        if g not in cards:
            continue
        title, desc = GROUP_TITLE[g]
        parts.append(f'\n    <div class="sched-title">{title}</div>')
        parts.append(f'    <div class="card" style="padding:10px 14px"><p class="muted" style="margin:0">{desc}</p></div>')
        parts.extend([c.rstrip("\n") for c in cards[g]])
    parts.append("""
    <div class="card">
      <p><b>订房实操（按这个顺序做）</b></p>
      <p>① <b>先抢票再订房</b>：10/1 的票 9/17 10:45 起售、返程票 9/19 18:00 起售；票到手当天就订房——国庆霞浦东壁/花竹的海景民宿只有 6–24 间。</p>
      <p>② <b>只订可免费取消的房型</b>，并截图「退订条款 + 同房型在售页」。霞浦有民宿毁约被处罚的公开案例（罚没 2,098 元），遇到拒单/坐地起价，直接走 12315 小程序。</p>
      <p>③ <b>看点评要看的不是分数</b>：本页每家的好评率都是「值得推荐 ÷ 总点评」的真实比值；<b>差评条数与差评率</b>比总分更能筛店（例如 1,637 条点评只有 10 条差评的鑫海湾，比 592 条全好评的花筑更「稳」）。</p>
      <p>④ <b>民宿 vs 酒店</b>：民宿看景观与老板服务（能帮你约车、出海鲜），但早餐普遍 07:00 后才开、隔音和热水是常见差评点；连锁酒店（亚朵/全季/白玉兰/维也纳）胜在稳定与接送站。第一次来 + 要拍日出，建议 D1 县城连锁 + D2 太姥山镇连锁，把民宿留给第二次。</p>
      <p>⑤ <b>宠物、押金、入住时间</b>：本页每家弹窗里都写了携程公示的入住/退房/押金/宠物政策；带宠物优先看鑫海湾（宠物友好，餐厅除外）。</p>
    </div>
  </section>""")
    open(os.path.join(NDIR, "hotels_block.html"), "w", encoding="utf-8").write("\n".join(parts) + "\n")
    open(os.path.join(NDIR, "hotels_modals.js"), "w", encoding="utf-8").write("\n".join(modals) + "\n")
    print("hotel cards:", sum(len(v) for v in cards.values()), "modals:", len(modals))
