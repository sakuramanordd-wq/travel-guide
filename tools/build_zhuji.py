#!/usr/bin/env python3
"""Build 诸暨3天2夜攻略.html by reusing the proven Osaka guide's CSS + modal engine.

Sources (all concatenated in filename order, so parts can be authored piecemeal):
  tools/zhuji/sections/*.html — the <body> content (banner / nav / sections)
  tools/zhuji/modals/*.js     — modal data objects (merged into one `const MODALS = {...}`)
  tools/zhuji/engine.js       — optional extra engine JS, appended after MODALS

Run:  python3 tools/build_zhuji.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "大阪关西5天4夜攻略.html")
ZDIR = os.path.join(ROOT, "tools", "zhuji")
OUT = os.path.join(ROOT, "诸暨3天2夜攻略.html")

# 大阪调色板 → 诸暨调色板（浣江青碧 + 苎萝胭脂）
RECOLOR = {
    "#3e6f9e": "#33707f",   # 主色：浣江青
    "#26405c": "#1d4652",   # 主色深：浦阳江夜色
    "#e3ebf4": "#e1edef",   # 主色浅
    "#b4472f": "#a8425a",   # 强调：苎萝胭脂
    "#8a3524": "#7d2e43",   # 强调深
    "#f7e4dd": "#f8e3e9",   # 强调浅
    "#5a4a6f": "#584a66",   # d5 头图（珍珠灰紫）
    "#3b3049": "#332b3d",
    "#2e7d5b": "#2f7a5f",   # d3
    "#1f5741": "#1f5741",
}

BADGE_CLASS = '''function badgeClass(t){
  const RED  = ["踩雷","避雷","谨慎","别踩坑","限时","当天往返太赶","不推荐","看时间","人多","已撤下","季节性","天气敏感","要预约","末班早"];
  const GRN  = ["推荐","必去","必玩","必吃","主力","省钱","已核对","最值得","免费","世界遗产","首选","经典","亲子友好","非遗"];
  const BLU  = ["必打卡","必体验","夜景","出片","顺路","本地","湖景","江景","改风景","雨天备选","甜品","早去","散步","CityWalk","citywalk","小众","山水"];
  if(RED.indexOf(t)>=0) return "r";
  if(GRN.indexOf(t)>=0) return "g";
  if(BLU.indexOf(t)>=0) return "b";
  return "o";
}'''


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def read_parts(subdir, pattern):
    """Concatenate every matching part file in filename order."""
    paths = sorted(glob.glob(os.path.join(ZDIR, subdir, pattern)))
    chunks = []
    for p in paths:
        body = read(p).strip()
        if body:
            chunks.append(f"<!-- ===== {os.path.basename(p)} ===== -->\n{body}")
    return "\n".join(chunks), [os.path.basename(p) for p in paths]


def collect_modals():
    """Merge tools/zhuji/modals/*.js (each a list of `"id": {...},` entries) into one object."""
    paths = sorted(glob.glob(os.path.join(ZDIR, "modals", "*.js")))
    body = []
    for p in paths:
        txt = read(p)
        # permit a whole `const MODALS = { ... };` wrapper — keep only the inner entries
        m = re.search(r"const\s+MODALS\s*=\s*\{(.*)\}\s*;?\s*$", txt, re.S)
        if m:
            txt = m.group(1)
        txt = txt.strip().strip(",")
        if txt:
            body.append(f"/* ===== {os.path.basename(p)} ===== */\n{txt}")
    if not body:
        sys.exit("no tools/zhuji/modals/*.js parts found")
    return "const MODALS = {\n" + ",\n".join(body) + "\n};", [os.path.basename(p) for p in paths]


def main():
    osaka = read(SRC)

    # ---- 1. CSS ----
    m = re.search(r"<style>(.*?)</style>", osaka, re.S)
    if not m:
        sys.exit("CSS block not found in reference file")
    css = m.group(1)
    for a, b in RECOLOR.items():
        css = css.replace(a, b)

    # ---- 2. engine JS ----
    m = re.search(r"(const modal = document\.getElementById\(\"modal\"\);.*?openFromHash\(\);\n)", osaka, re.S)
    if not m:
        sys.exit("engine JS not found in reference file")
    js = m.group(1)
    js = js.replace('foodTag(d,"食べログ")', 'foodTag(d,"评分")')
    js = js.replace("食べログ 评分", "平台评分")
    js = js.replace("（3.5↑ 算好吃）", "（来源见弹窗底部）")
    js = js.replace("—— 食べログ 用户评价", "—— 公开评价")
    js = js.replace("🍽️ 招牌", "🍽️ 招牌")
    js = re.sub(r'function badgeClass\(t\)\{.*?\n\}', BADGE_CLASS, js, count=1, flags=re.S)

    engine_extra = ""
    extra_path = os.path.join(ZDIR, "engine.js")
    if os.path.exists(extra_path):
        engine_extra = read(extra_path)

    modals, modal_parts = collect_modals()
    sections, section_parts = read_parts("sections", "*.html")
    if not sections:
        sys.exit("no tools/zhuji/sections/*.html parts found")

    title = "诸暨 · 3天2夜（杭州高铁往返）· 西施故里 + 五泄 + 斯宅千柱屋"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{sections}

<!-- ================= MODAL ================= -->
<div class="modal" id="modal">
  <div class="modal-card">
    <div class="modal-head" id="mh">
      <div class="ic" id="mh-ic">📍</div>
      <div class="ht"><div class="t" id="mh-t">标题</div><div class="s" id="mh-s">副标题</div></div>
      <button class="modal-close" id="mh-x">×</button>
    </div>
    <div class="modal-body" id="mh-body"></div>
  </div>
</div>

<script>
{modals}
{engine_extra}
{js}
</script>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("sections:", ", ".join(section_parts))
    print("modals:  ", ", ".join(modal_parts))
    print("wrote", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
