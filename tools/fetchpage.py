#!/usr/bin/env python3
import sys, re, gzip, io, os, urllib.request, urllib.parse, ssl, zlib

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
# Usage:  M=1 python3 fetchpage.py <URL>   -> fetch with a mobile UA.
# Some CN sites (e.g. bendibao) return a puzzle-captcha page to a desktop UA but serve content to mobile UA.
if os.environ.get("M", "").strip() in ("1", "mobile", "true"):
    UA = UA_MOBILE

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        raw = r.read()
        enc = r.headers.get("Content-Encoding", "")
        if "gzip" in enc:
            raw = gzip.decompress(raw)
        elif "deflate" in enc:
            try:
                raw = zlib.decompress(raw)
            except Exception:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        return raw, r.headers.get("Content-Type", "")

def to_text(raw, ctype):
    txt = None
    m = re.search(r"charset=([\w\-]+)", ctype, re.I)
    cands = []
    if m: cands.append(m.group(1))
    m2 = re.search(rb'charset=["\']?([\w\-]+)', raw[:4000], re.I)
    if m2:
        try: cands.append(m2.group(1).decode("ascii"))
        except Exception: pass
    cands += ["utf-8", "gb18030", "gbk", "latin-1"]
    for c in cands:
        try:
            txt = raw.decode(c)
            break
        except Exception:
            continue
    if txt is None:
        txt = raw.decode("utf-8", "ignore")
    txt = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", txt)
    txt = re.sub(r"(?is)<!--.*?-->", " ", txt)
    txt = re.sub(r"(?is)<(br|/p|/div|/li|/tr|/h[1-6]|/td)[^>]*>", "\n", txt)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt.strip()

if __name__ == "__main__":
    url = sys.argv[1]
    maxlen = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    try:
        raw, ct = fetch(url)
        t = to_text(raw, ct)
        print(t[:maxlen])
    except Exception as e:
        print("FETCH_ERROR:", type(e).__name__, e)
