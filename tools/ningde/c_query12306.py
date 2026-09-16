#!/usr/bin/env python3
"""c_query12306.py DATE FROM TO [DATE FROM TO ...]  -- curl + queryG with own cookie jar (.ck2.txt).
Auto-refreshes cookie jar on failure. Saves raw JSON to research/_raw/ningde/c-12306-<FROM>-<TO>-<DATE>.json"""
import sys, os, json, subprocess, re

BASE = "/home/hukun02/Project/travel-guide/research/_raw/ningde"
CK = os.path.join(BASE, ".ck2.txt")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def load_stations():
    d = open(os.path.join(BASE, 'station_name.js'), encoding='utf-8', errors='ignore').read()
    m = {}
    for x in re.findall(r'@([^@]+)', d):
        p = x.split('|')
        if len(p) > 6:
            m[p[2]] = p[1]
    return m
NAME = load_stations()

def refresh():
    subprocess.run(['curl', '-s', '-c', CK, '-A', UA,
                    'https://kyfw.12306.cn/otn/leftTicket/init', '-o', '/dev/null'],
                   check=False, timeout=60)

def raw(date, frm, to):
    out = os.path.join(BASE, 'c-12306-%s-%s-%s.json' % (frm, to, date))
    url = ("https://kyfw.12306.cn/otn/leftTicket/queryG?leftTicketDTO.train_date=%s"
           "&leftTicketDTO.from_station=%s&leftTicketDTO.to_station=%s&purpose_codes=ADULT"
           % (date, frm, to))
    for attempt in (1, 2):
        subprocess.run(['curl', '-s', '-b', CK, '-c', CK, '-A', UA, url,
                        '-H', 'Referer: https://kyfw.12306.cn/otn/leftTicket/init',
                        '-H', 'Accept: application/json, text/javascript, */*; q=0.01',
                        '-H', 'X-Requested-With: XMLHttpRequest', '-o', out],
                       check=False, timeout=60)
        try:
            return json.load(open(out, encoding='utf-8'))
        except Exception:
            if attempt == 1:
                refresh()
    return {}

def main():
    args = sys.argv[1:]
    if not os.path.exists(CK):
        refresh()
    for i in range(0, len(args), 3):
        date, frm, to = args[i], args[i+1], args[i+2]
        d = raw(date, frm, to)
        res = (d.get('data') or {}).get('result') or []
        msg = str(d.get('messages') or d.get('c_url') or '')[:120]
        print("### %s -> %s  %s  status=%s n=%d %s" %
              (NAME.get(frm, frm), NAME.get(to, to), date, d.get('status'), len(res), msg))
        rows = []
        for x in res:
            p = x.split('|')
            rows.append((p[8], p[3], NAME.get(p[6], p[6]), NAME.get(p[7], p[7]), p[9], p[10],
                         p[29], p[30], p[31], p[32], p[26], p[28], p[1], p[11]))
        rows.sort()
        for r in rows:
            print("   %s->%s %-7s %s->%s 历时%s 二等[%s] 一等[%s] 商务[%s] 硬座[%s] 硬卧[%s] 无座[%s] note=%s buy=%s"
                  % (r[0], r[4], r[1], r[2], r[3], r[5], r[7], r[8], r[9], r[6], r[11], r[10], r[12], r[13]))
    return 0

sys.exit(main())
