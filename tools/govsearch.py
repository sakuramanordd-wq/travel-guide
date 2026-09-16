#!/usr/bin/env python3
"""Search nantong.gov.cn CMS and print compact title/url/date results."""
import urllib.parse, urllib.request, ssl, re, sys, html

def search(q, n=8):
    u = ("https://www.nantong.gov.cn/truecms/searchController/getResult.do"
         "?word_correct=&query=" + urllib.parse.quote(q) + "&pageSize=15&page=1")
    req = urllib.request.Request(u, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9"})
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
        t = r.read().decode("utf-8", "ignore")
    t = html.unescape(t)
    # results appear as title then ... then url then date
    urls = re.findall(r'(https?://[a-z0-9.\-]*nantong\.gov\.cn/[^\s"\'<>]+)', t)
    dates = re.findall(r'\b(20\d\d-\d\d-\d\d)\b', t)
    return urls, dates

if __name__ == "__main__":
    for q in sys.argv[1:]:
        print("=" * 12, q)
        try:
            urls, dates = search(q)
            seen = []
            for u in urls:
                if u not in seen:
                    seen.append(u)
            for i, u in enumerate(seen[:8]):
                print("  ", u)
            print("   dates:", dates[:8])
        except Exception as e:
            print("   ERR", e)
