#!/usr/bin/env python3
"""Assemble 宁德3天2夜攻略.html.

Sources:
  .agents/skills/travel-guide/template.html  — canonical skeleton (大阪攻略的 CSS + 弹窗引擎)
  tools/ningde/sections.html                 — <body> 内容（banner / nav / sections）
  tools/ningde/modals.js                     — `const MODALS = {...};`

Palette: 大阪（朱+蓝）→ 宁德（三都澳深海蓝 + 霞浦滩涂日落赭 + 白茶金）。
Run: python3 tools/ningde/build_ningde.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TPL = os.path.join(ROOT, ".agents", "skills", "travel-guide", "template.html")
NDIR = os.path.join(ROOT, "tools", "ningde")
OUT = os.path.join(ROOT, "宁德3天2夜攻略.html")

TITLE = "宁德 · 3天2夜（杭州高铁往返）· 霞浦滩涂 + 太姥山 + 福鼎"

RECOLOR = {
    "#b4472f": "#b4581f",   # 主强调：霞浦滩涂日落赭
    "#8a3524": "#83390f",   # 强调深
    "#f7e4dd": "#f8e8d9",   # 强调浅
    "#f5e0da": "#f7e5d6",   # badge.r 底
    "#9c3f2b": "#96430f",   # warn 文字
    "#d3836f": "#d39270",   # 进度条渐变末端
    "#3e6f9e": "#2f6f7e",   # 主色：三都澳深海青
    "#26405c": "#143c47",   # 主色深
    "#e3ebf4": "#e1edf0",   # 主色浅
    "#5a4a6f": "#46605f",   # d5 头图（礁石灰青）
    "#3b3049": "#2c3c3b",
}

BADGE_CLASS = '''function badgeClass(t){
  const RED  = ["踩雷","避雷","谨慎","别踩坑","限时","当天往返太赶","不推荐","看时间","人多","已撤下","季节性","天气敏感","要预约","末班早","已售完"];
  const GRN  = ["推荐","必去","必玩","必吃","主力","省钱","已核对","最值得","免费","世界遗产","首选","经典","亲子友好","非遗","主打"];
  const BLU  = ["必打卡","必体验","夜景","出片","顺路","本地","海景","江景","改风景","雨天备选","甜品","早去","散步","CityWalk","citywalk","小众","滩涂","日出"];
  if(RED.indexOf(t)>=0) return "r";
  if(GRN.indexOf(t)>=0) return "g";
  if(BLU.indexOf(t)>=0) return "b";
  return "o";
}'''


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def main():
    tpl = read(TPL)

    m = re.search(r"<style>(.*?)</style>", tpl, re.S)
    if not m:
        sys.exit("CSS block not found in template.html")
    css = m.group(1)
    for a, b in RECOLOR.items():
        css = css.replace(a, b)

    m = re.search(r"(const modal = document\.getElementById\(\"modal\"\);.*?openFromHash\(\);\n)", tpl, re.S)
    if not m:
        sys.exit("engine JS not found in template.html")
    js = m.group(1)
    # 日本口径 → 国内口径（携程 / 大众点评 / UGC）
    js = js.replace('foodTag(d,"食べログ")', 'foodTag(d,"评分")')
    js = js.replace("食べログ 评分<br>（3.5↑ 算好吃）", "平台评分<br>（携程 5 分制）")
    js = js.replace("—— 食べログ 用户评价", "—— 公开评价（携程 / 大众点评 / UGC）")
    js = js.replace("好评率（最新约 20 条）", "好评率（平台口径）")
    js = re.sub(r'function badgeClass\(t\)\{.*?\n\}', BADGE_CLASS, js, count=1, flags=re.S)
    js = re.sub(r"食べログ", "平台", js)

    extra = os.path.join(NDIR, "engine.js")
    engine_extra = read(extra) if os.path.exists(extra) else ""
    modals = read(os.path.join(NDIR, "modals.js")).strip()
    sections = read(os.path.join(NDIR, "sections.html")).strip()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{TITLE}</title>
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
{js}
{engine_extra}
</script>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
