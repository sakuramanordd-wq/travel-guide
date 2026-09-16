#!/usr/bin/env python3
import sys, ssl, urllib.request, urllib.parse, re, html
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
def C():
    c=ssl.create_default_context(); c.check_hostname=False; c.verify_mode=ssl.CERT_NONE; c.options|=0x4
    try: c.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception: pass
    return c
def bing(q):
    u="https://cn.bing.com/search?q="+urllib.parse.quote(q)+"&setlang=zh-CN&count=30"
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"zh-CN,zh;q=0.9"})
    h=urllib.request.urlopen(req,timeout=30,context=C()).read().decode('utf-8','ignore')
    res=[]
    for m in re.finditer(r'<h2>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',h,re.S):
        t=html.unescape(re.sub(r'<[^>]+>','',m.group(2))).strip()
        res.append((t[:90],m.group(1)))
    if not res:
        for m in re.finditer(r'<a[^>]+class="[^"]*tilk[^"]*"[^>]+href="([^"]+)"',h):
            res.append(("?",m.group(1)))
    return res
if __name__=="__main__":
    for q in sys.argv[1:]:
        print("=====",q)
        try:
            for t,u in bing(q)[:12]: print("  %s\n     %s" % (t,u[:160]))
        except Exception as e: print("  ERR",repr(e)[:120])
