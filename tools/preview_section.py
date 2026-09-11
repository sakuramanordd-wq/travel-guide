#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把页面里某个 section 抽成独立预览文件（方便无头浏览器截图核对版式）。

用法:  python3 tools/preview_section.py d1 _pv_d1.html
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "大阪关西5天4夜攻略.html")


def main():
    sec_id, out = sys.argv[1], sys.argv[2]
    html = open(PAGE, encoding="utf-8").read()
    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    m = re.search(r'<section id="%s">(.*?)</section>' % re.escape(sec_id), html, re.S)
    if not m:
        print("找不到 section", sec_id)
        return
    body = m.group(0)
    doc = ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
           "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           "<title>preview %s</title><style>%s</style></head><body><div class=\"wrap\">%s</div></body></html>"
           % (sec_id, css, body))
    open(os.path.join(ROOT, out), "w", encoding="utf-8").write(doc)
    print("wrote", out, len(doc), "bytes")


if __name__ == "__main__":
    main()
