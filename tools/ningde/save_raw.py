#!/usr/bin/env python3
"""Fetch URL and save cleaned text into research/_raw/ningde/<name>.txt
Usage: python3 save_raw.py NAME URL [maxchars]
Tries mobile UA first if desktop fails (captcha detection).
"""
import sys, os, re, gzip, zlib, ssl, urllib.request

DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
OUT = "/home/hukun02/Project/travel-guide/research/_raw/ningde"

def fetch(url, ua, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read()
        enc = r.headers.get("Content-Encoding", "")
        if "gzip" in enc:
            raw = gzip.decompress(raw)
        elif "deflate" in enc:
            try: raw = zlib.decompress(raw)
            except Exception: raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        return raw, r.headers.get("Content-Type", "")

def to_text(raw, ctype):
    cands = []
    m = re.search(r"charset=([\w\-]+)", ctype, re.I)
    if m: cands.append(m.group(1))
    m2 = re.search(rb'charset=["\']?([\w\-]+)', raw[:4000], re.I)
    if m2:
        try: cands.append(m2.group(1).decode("ascii"))
        except Exception: pass
    cands += ["utf-8", "gb18030", "gbk", "latin-1"]
    txt = None
    for c in cands:
        try:
            txt = raw.decode(c); break
        except Exception:
            continue
    if txt is None: txt = raw.decode("utf-8", "ignore")
    txt = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", txt)
    txt = re.sub(r"(?is)<!--.*?-->", " ", txt)
    txt = re.sub(r"(?is)<(br|/p|/div|/li|/tr|/h[1-6]|/td)[^>]*>", "\n", txt)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&ensp;", " "), ("&emsp;", " ")):
        txt = txt.replace(a, b)
    txt = txt.replace("\u3000", " ").replace("\xa0", " ")
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt.strip()

def main():
    name, url = sys.argv[1], sys.argv[2]
    maxlen = int(sys.argv[3]) if len(sys.argv) > 3 else 200000
    os.makedirs(OUT, exist_ok=True)
    for ua in (DESKTOP, MOBILE):
        try:
            raw, ct = fetch(url, ua)
            t = to_text(raw, ct)
            if len(t) < 200 and ua is DESKTOP:
                continue
            path = os.path.join(OUT, name + ".txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# URL: %s\n# fetched: 2026-09-15\n# ua: %s\n\n" % (url, "mobile" if ua is MOBILE else "desktop"))
                f.write(t[:maxlen])
            print("SAVED", path, len(t))
            print(t[:4000])
            return 0
        except Exception as e:
            last = e
    print("FETCH_ERROR:", type(last).__name__, last)
    return 1

sys.exit(main())
