#!/usr/bin/env python3
"""Fetch a URL and print readable text. Usage: fetch.py URL [--raw] [--max N]"""
import sys, re, html, urllib.request, gzip, io, ssl

def main():
    if len(sys.argv) < 2:
        print("usage: fetch.py URL [--raw] [--max N]"); return 1
    url = sys.argv[1]
    raw = "--raw" in sys.argv
    mx = 20000
    if "--max" in sys.argv:
        mx = int(sys.argv[sys.argv.index("--max")+1])
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        data = r.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    # charset
    cs = None
    m = re.search(rb'charset=["\']?([A-Za-z0-9_-]+)', data[:4000])
    if m: cs = m.group(1).decode("ascii", "ignore")
    for enc in ([cs] if cs else []) + ["utf-8", "gb18030", "gbk", "big5", "latin-1"]:
        try:
            txt = data.decode(enc); break
        except Exception:
            continue
    if raw:
        print(txt[:mx]); return 0
    txt = re.sub(r'(?is)<script.*?</script>', ' ', txt)
    txt = re.sub(r'(?is)<style.*?</style>', ' ', txt)
    txt = re.sub(r'(?is)<!--.*?-->', ' ', txt)
    txt = re.sub(r'(?is)<(br|/p|/div|/li|/tr|/h[1-6]|/table)[^>]*>', '\n', txt)
    txt = re.sub(r'(?s)<[^>]+>', ' ', txt)
    txt = html.unescape(txt)
    txt = txt.replace('\u3000', ' ').replace('\xa0', ' ')
    txt = re.sub(r'[ \t\r\f\v]+', ' ', txt)
    txt = re.sub(r'\n\s*\n\s*\n+', '\n\n', txt)
    lines = [l.strip() for l in txt.split('\n')]
    out = "\n".join(l for l in lines if l)
    print(out[:mx])
    return 0

sys.exit(main())
