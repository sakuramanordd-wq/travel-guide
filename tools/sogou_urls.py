#!/usr/bin/env python3
import sys, ssl, urllib.request, urllib.parse, re, html
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
def C():
    c=ssl.create_default_context(); c.check_hostname=False; c.verify_mode=ssl.CERT_NONE; c.options|=0x4
    try: c.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception: pass
    return c
def run(q):
    u="https://www.sogou.com/web?query="+urllib.parse.quote(q)
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"zh-CN"})
    h=urllib.request.urlopen(req,timeout=30,context=C()).read().decode('utf-8','ignore')
    out=[]
    for m in re.finditer(r'data-url="([^"]+)"data-hint="sugg"[^>]*?data-title="([^"]*)"',h):
        out.append((urllib.parse.unquote(m.group(2))[:70], html.unescape(m.group(1))))
    return out
if __name__=="__main__":
    for q in sys.argv[1:]:
        print("=====",q)
        try:
            for t,u in run(q)[:14]: print("  %s\n     %s" % (t,u[:160]))
        except Exception as e: print("  ERR",repr(e)[:120])
