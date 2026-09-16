#!/usr/bin/env python3
"""c_baidu.py "query" [maxchars] -- Baidu web search; prints titles + RESOLVED real URLs + snippets."""
import sys, re, gzip, ssl, urllib.request, urllib.parse, html

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
TAG = re.compile(r"<[^>]+>")

def txt(s):
    return html.unescape(re.sub(r"\s+", " ", TAG.sub(" ", s))).strip()

def fetch(u, timeout=25):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9",
                                             "Accept-Encoding": "gzip", "Cookie": "BAIDUID=0"})
    r = urllib.request.urlopen(req, timeout=timeout, context=CTX)
    raw = r.read()
    if "gzip" in r.headers.get("Content-Encoding", ""):
        raw = gzip.decompress(raw)
    cs = None
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000])
    if m:
        cs = m.group(1).decode("ascii", "ignore")
    for c in [cs, "utf-8", "gb18030", "latin-1"]:
        if not c:
            continue
        try:
            return raw.decode(c), r.geturl()
        except Exception:
            continue
    return raw.decode("utf-8", "ignore"), r.geturl()

def resolve(u):
    try:
        _, final = fetch(u, timeout=20)
        return final
    except Exception:
        return u

def main():
    q = sys.argv[1]
    mx = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    u = "https://www.baidu.com/s?wd=" + urllib.parse.quote(q) + "&rn=20"
    try:
        t, _ = fetch(u)
    except Exception as e:
        print("ERR", type(e).__name__, e); return
    out = []
    for m in re.finditer(r'<div[^>]+class="result[^"]*"[^>]*>(.*?)(?=<div[^>]+class="result|<div id="page")',
                         t, re.S):
        blk = m.group(1)
        h = re.search(r'<h3[^>]*>(.*?)</h3>', blk, re.S)
        title = txt(h.group(1)) if h else ""
        url = ""
        for pat in (r'mu="([^"]+)"', r'href="(http[^"]*baidu\.com/link\?url=[^"]+)"',
                    r'href="(https?://[^"]+)"'):
            mm = re.search(pat, blk)
            if mm:
                url = html.unescape(mm.group(1)); break
        body = txt(blk)
        if body:
            out.append((title, url, body))
    seen = set(); n = 0
    for title, url, body in out:
        key = body[:120]
        if key in seen or "百度一下" in body[:60] or "热搜榜" in body:
            continue
        seen.add(key)
        real = resolve(url) if "baidu.com/link" in url else url
        print("### %s\n    URL: %s\n    %s\n" % (title, real, body[:mx]))
        n += 1
        if n >= 12:
            break
    if n == 0:
        print(txt(t)[:mx])

main()
