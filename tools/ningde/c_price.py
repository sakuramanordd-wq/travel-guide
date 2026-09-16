#!/usr/bin/env python3
"""c_price.py <routejson>  -- for each train in a saved c-12306 JSON, query 12306 price endpoint.
Writes c-price-<FROM>-<TO>-<DATE>.txt and prints."""
import sys, os, json, subprocess, time

BASE = "/home/hukun02/Project/travel-guide/research/_raw/ningde"
CK = os.path.join(BASE, ".ck2.txt")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def refresh():
    subprocess.run(['curl', '-s', '-c', CK, '-A', UA,
                    'https://kyfw.12306.cn/otn/leftTicket/init', '-o', '/dev/null'],
                   check=False, timeout=60)

def price(train_no, fsn, tsn, seat_types, date):
    url = ("https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no=%s"
           "&from_station_no=%s&to_station_no=%s&seat_types=%s&train_date=%s"
           % (train_no, fsn, tsn, seat_types, date))
    r = subprocess.run(['curl', '-s', '-b', CK, '-c', CK, '-A', UA, url,
                        '-H', 'Referer: https://kyfw.12306.cn/otn/leftTicket/init'],
                       capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}

def main():
    path = sys.argv[1]
    j = json.load(open(path, encoding='utf-8'))
    import re
    m = re.search(r'c-12306-([A-Z]+)-([A-Z]+)-(\d{4}-\d{2}-\d{2})\.json', path)
    frm, to, date = m.group(1), m.group(2), m.group(3)
    rows = j.get('rows')
    if rows is None:
        rows = (j.get('data') or {}).get('result') or []
    print('# route %s -> %s  date %s  n=%d' % (frm, to, date, len(rows)))
    lines = []
    for row in rows:
        p = row.split('|')
        code, tno, fsn, tsn, st, at, lishi, seats = p[3], p[2], p[16], p[17], p[8], p[9], p[10], p[35]
        if st == '24:00':
            continue
        d = price(tno, fsn, tsn, seats, date)
        data = d.get('data') or {}
        # seat code -> name
        nm = {'9': '商务座', 'P': '特等座', 'M': '一等座', 'O': '二等座',
              'S': '商务座', 'A': '高级动卧', 'F': '动卧', 'WZ': '无座', '1': '硬座', '2': '硬座'}
        parts = []
        for k, v in data.items():
            if isinstance(v, str) and v.startswith('¥'):
                parts.append('%s=%s' % (nm.get(k, k), v))
        lines.append('%-7s %s->%s 历时%s | %s | seat_types=%s' %
                     (code, st, at, lishi, '  '.join(parts) if parts else '(无价格返回)', seats))
        print(lines[-1], flush=True)
        time.sleep(1.2)
    out = os.path.join(BASE, 'c-price-%s-%s-%s.txt' % (frm, to, date))
    with open(out, 'w', encoding='utf-8') as f:
        f.write('# 12306 queryTicketPrice, saved 2026-09-15, source https://kyfw.12306.cn/\n')
        f.write('# route %s -> %s  date %s\n\n' % (frm, to, date))
        f.write('\n'.join(lines) + '\n')
    print('SAVED', out)

main()
