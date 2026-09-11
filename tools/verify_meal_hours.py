#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交叉检查：每天的餐次卡片所对应的店，是否在「那一天的星期 + 那个时间点」营业。

数据来源：tools/meal_data.py 的 DAY_PLAN（时段与店铺）+ research/tabelog_shops.json（营业 / 定休）
          页面里老弹窗的「营业 / 定休」行（EXISTING 里的 8 家）
用法: python3 tools/verify_meal_hours.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meal_data import NEW, DAY_PLAN, EXISTING  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "大阪关西5天4夜攻略.html")
SHOPS = os.path.join(ROOT, "research", "tabelog_shops.json")

DAY_WEEK = {"d1": "星期四", "d2": "星期五", "d3": "星期六", "d4": "星期日", "d5": "星期一"}
DAY_DATE = {"d1": "11/05", "d2": "11/06", "d3": "11/07", "d4": "11/08", "d5": "11/09"}


def norm(s):
    s = (s or "").replace("–", "-").replace("—", "-").replace("～", "-").replace("〜", "-")
    s = s.replace("：", ":").replace("・", "·").replace("\u3000", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def parse_hours(s):
    """返回 {星期X: [(open, close), ...]}；某天没有任何时段 = 当天不开。"""
    s = norm(s)
    out = {}
    if re.search(r"24\s*小時|24\s*小时", s):
        for d in "一二三四五六日":
            out["星期" + d] = [(0, 0, 24, 0)]
        return out
    if not re.search(r"星期[一二三四五六日]", s):
        # 页面里的老格式（如「11:00–22:30」「14:00–售完为止」）：适用于所有天，休日看定休字段
        times = [(int(a), int(b), int(c), int(d)) for a, b, c, d in
                 re.findall(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", s)]
        if not times:
            st = re.search(r"(\d{1,2}):(\d{2})", s)
            if st:
                times = [(int(st.group(1)), int(st.group(2)), 24, 0)]
        for d in "一二三四五六日":
            out["星期" + d] = list(times)
        return out
    # 「星期二，星期三 … 11:00-15:00 17:30-22:30」「星期六，星期日，節假日 12:00-23:30」「星期一」（无时段=休）
    pat = re.compile(r"((?:星期[一二三四五六日][，、·]?\s*)+)"
                     r"[^\d星]{0,30}?"
                     r"((?:\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\s*)+)")
    for m in pat.finditer(s):
        days = ["星期" + d for d in re.findall(r"星期([一二三四五六日])", m.group(1))]
        times = [(int(a), int(b), int(c), int(d)) for a, b, c, d in
                 re.findall(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", m.group(2))]
        for d in days:
            out.setdefault(d, [])
            out[d].extend(times)
    for d in set(re.findall(r"星期([一二三四五六日])", s)):
        out.setdefault("星期" + d, [])
    return out


def covers(rng, hh, mm):
    o = rng[0] * 60 + rng[1]
    c = rng[2] * 60 + rng[3]
    t = hh * 60 + mm
    if c <= o:          # 跨夜
        return t >= o or t <= c
    return o <= t <= c


def closed_hit(closed_text, weekday):
    """定休日字段里是否包含该星期（支持「星期一」「周一」「周三・周四」「水・木」）。"""
    c = norm(closed_text)
    if weekday in c:
        return True
    short = weekday[-1]
    if re.search(r"周" + short, c) or re.search(r"[（(]?" + short + r"[）)、・]", c):
        return True
    return False


def main():
    raw = json.load(open(SHOPS, encoding="utf-8"))
    page = open(PAGE, encoding="utf-8").read()
    old_rows = {}
    for m in re.finditer(r'\n"(f-[a-z0-9\-]+)": \{(.*?)\n\}(?=,|\n)', page, re.S):
        sid, body = m.group(1), m.group(2)

        def row(k):
            r = re.search(r'\["%s","(.*?)"\]' % k, body)
            return r.group(1) if r else ""

        old_rows[sid] = (row("营业"), row("定休"))

    info = {}
    for sid, cfg in NEW.items():
        d = raw.get(cfg["tid"], {})
        info[sid] = dict(name=cfg["name"], hours=d.get("hours") or cfg["hours"],
                         closed=d.get("closed") or cfg["closed"])
    for sid in EXISTING:
        if sid in old_rows:
            h, c = old_rows[sid]
            info[sid] = dict(name=sid, hours=h, closed=c)

    problems = 0
    for day, cfg in DAY_PLAN.items():
        wd = DAY_WEEK[day]
        print("=" * 8, day, DAY_DATE[day], wd, cfg["rname"])
        for meal in cfg["meals"]:
            time, mname, ic, where, note, ids = meal[:6]
            hh, mm = int(time[:2]), int(time[3:])
            if not ids:
                print("  %-6s %-14s （无卡片：只有文字说明）" % (time, mname))
                continue
            for sid in ids:
                if sid == "f-konbini":
                    continue
                d = info.get(sid)
                if not d:
                    print("  %-6s %-14s !! %s 没有营业数据" % (time, mname, sid))
                    problems += 1
                    continue
                hrs = parse_hours(d["hours"])
                day_ranges = hrs.get(wd, [])
                if not day_ranges:
                    why = "该日未列在营业时间里"
                    if closed_hit(d["closed"], wd):
                        why = "定休日：%s" % norm(d["closed"])[:22]
                    print("  %-6s %-14s ❌ %-26s %s" % (time, mname, d["name"][:26], why))
                    problems += 1
                    continue
                ok = any(covers(r, hh, mm) for r in day_ranges)
                flag = "✅" if ok else "⚠️"
                if not ok:
                    problems += 1
                rng = " ".join("%02d:%02d-%02d:%02d" % r for r in day_ranges)
                print("  %-6s %-14s %s %-26s %s ｜门休: %s" % (
                    time, mname, flag, d["name"][:26], rng, norm(d["closed"])[:18] or "—"))
        print()
    print("需要人工确认的条数：", problems)


if __name__ == "__main__":
    main()
