#!/usr/bin/env python3
"""Build 南通3天2夜攻略.html by reusing the proven Osaka guide's CSS + modal engine.

Sources:
  tools/nantong/sections.html  — the <body> content (banner / nav / sections)
  tools/nantong/modals.js      — `const MODALS = {...};` data for every popup
  tools/nantong/engine.js      — modal render engine (copied from the Osaka guide,
                                 with 食べログ keys swapped for Chinese review keys)

Run:  python3 tools/build_nantong.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "大阪关西5天4夜攻略.html")
NDIR = os.path.join(ROOT, "tools", "nantong")
OUT = os.path.join(ROOT, "南通3天2夜攻略.html")

# 大阪调色板 → 南通调色板（江海青 + 张謇砖红）
RECOLOR = {
    "#3e6f9e": "#3f7f8c",   # 主色：江海青
    "#26405c": "#1e4351",   # 主色深：长江夜色
    "#e3ebf4": "#e2edf0",   # 主色浅
    "#b4472f": "#a8452c",   # 强调：张謇砖红
    "#8a3524": "#7f3320",   # 强调深
    "#f7e4dd": "#f6e5de",   # 强调浅
    "#5a4a6f": "#4a5a63",   # d5 头图（灰青）
    "#3b3049": "#2b373d",
    "#2e7d5b": "#2f7a5f",   # d3
    "#1f5741": "#1f5741",
}

BADGE_CLASS = '''function badgeClass(t){
  const RED  = ["踩雷","避雷","谨慎","别踩坑","限时","当天往返太赶","不推荐","看时间","人多","已撤下","季节性","天气敏感"];
  const GRN  = ["推荐","必去","必玩","必吃","主力","省钱","已核对","最值得","免费","世界遗产","首选","经典","亲子友好"];
  const BLU  = ["必打卡","必体验","夜景","出片","顺路","本地","湖景","江景","改风景","雨天备选","甜品","早去","散步","CityWalk","citywalk","小众"];
  if(RED.indexOf(t)>=0) return "r";
  if(GRN.indexOf(t)>=0) return "g";
  if(BLU.indexOf(t)>=0) return "b";
  return "o";
}'''


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


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
    js = js.replace("食べログ 评分", "本地口碑评分")
    js = js.replace("（3.5↑ 算好吃）", "（评分来源见弹窗底部）")
    js = js.replace("食べログ 用户评价", "本地口碑 / 公开评价")
    js = re.sub(r'function badgeClass\(t\)\{.*?\n\}', BADGE_CLASS, js, count=1, flags=re.S)
    # 南通版把「推荐指数」档位文案保留，但「口碑拆解」改成可选渲染（无数据时不显示）
    js = js.replace('const credit= (d.rows||[]).find(x=>x[0]==="口碑");',
                    'const credit= (d.rows||[]).find(x=>x[0]==="口碑");')

    engine_extra = read(os.path.join(NDIR, "engine.js")) if os.path.exists(os.path.join(NDIR, "engine.js")) else ""

    modals = read(os.path.join(NDIR, "modals.js")).strip()
    sections = read(os.path.join(NDIR, "sections.html")).strip()

    title = "南通 · 3天2夜（杭州高铁往返）· 濱河老城 + 狼山江海"

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
    print("wrote", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
