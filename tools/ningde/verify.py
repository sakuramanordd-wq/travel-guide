#!/usr/bin/env python3
"""QA checks for 宁德3天2夜攻略.html / .md / index.html.

Run: python3 tools/ningde/verify.py
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML = os.path.join(ROOT, "宁德3天2夜攻略.html")
MD = os.path.join(ROOT, "宁德3天2夜攻略.md")
IDX = os.path.join(ROOT, "index.html")

ok, warn, bad = [], [], []


def chk(cond, msg):
    (ok if cond else bad).append(msg)


def main():
    t = open(HTML, encoding="utf-8").read()
    # 1. JS syntax
    js = re.search(r"<script>([\s\S]*)</script>\s*</body>", t)
    chk(bool(js), "找到 <script> 区块")
    if js:
        tmp = "/tmp/ningde_check.js"
        open(tmp, "w", encoding="utf-8").write(js.group(1))
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        chk(r.returncode == 0, "内联 JS 语法通过 node --check" + ("" if r.returncode == 0 else f" :: {r.stderr[:300]}"))
        keys = set(re.findall(r'^\s*"([a-z0-9-]+)":\s*\{', js.group(1), re.M))
    else:
        keys = set()
    # 2. modal ids vs data-modal
    used = set(re.findall(r'data-modal="([^"]+)"', t))
    missing = sorted(used - keys)
    unused = sorted(keys - used)
    chk(not missing, f"所有 data-modal 都有对应弹窗（缺失 {len(missing)}）" + (f" :: {missing[:8]}" if missing else ""))
    if unused:
        warn.append(f"定义了但页面未引用（{len(unused)}）: {unused[:8]}")
    print(f"弹窗：定义 {len(keys)} / 引用 {len(used)}")
    # 3. 图片存在
    imgs = sorted(set(re.findall(r'images/[A-Za-z0-9._/-]+', t)))
    miss_img = [i for i in imgs if not os.path.exists(os.path.join(ROOT, i))]
    chk(not miss_img, f"所有图片文件存在（引用 {len(imgs)} 张，缺失 {len(miss_img)}）" + (f" :: {miss_img[:6]}" if miss_img else ""))
    # 4. 来源链接
    nsrc = len(re.findall(r'https?://', t))
    chk(nsrc > 40, f"页面含 {nsrc} 个来源链接")
    # 5. 日本/大阪残留
    for w in ["食べログ", "tabelog", "日元", "円", "大阪", "关西", "南通"]:
        c = t.count(w)
        if c:
            bad.append(f"出现残留词「{w}」×{c}")
    # 6. 必要结构
    for sec in ["plan", "hotel", "d1", "d2", "d3", "pass", "food", "tips", "precheck", "gallery"]:
        chk(f'id="{sec}"' in t, f"包含 section #{sec}")
    chk("撤下" in t, "含「撤下名单」可信度机制")
    chk(re.search(r"(来源|分级)[^<]{0,20}(A|甲)", t) is not None, "含来源分级说明")
    chk("2026" in t and "10.01" in t, "含日期")
    # 7. md / index
    chk(os.path.exists(MD), "存在 .md 版本")
    if os.path.exists(MD):
        m = open(MD, encoding="utf-8").read()
        chk(len(m) > 8000, f".md 篇幅 {len(m)} 字符")
        chk("宁德" in m, ".md 含目的地")
    if os.path.exists(IDX):
        idx = open(IDX, encoding="utf-8").read()
        chk("宁德3天2夜攻略.html" in idx, "index.html 已登记本攻略")
        chk("images/ningde" in idx or "hero-ningde" in idx, "index.html 卡片图存在")
    # 8. 计数信息
    mh = re.findall(r'<div class="mcat">([^<]+)', t)
    print("餐次分组:", mh)
    print("弹窗类型:", {k.split("-")[0] for k in keys})
    print(f"\n通过 {len(ok)} 项；警告 {len(warn)}；失败 {len(bad)}")
    for w in warn:
        print("  WARN", w)
    for b in bad:
        print("  FAIL", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
