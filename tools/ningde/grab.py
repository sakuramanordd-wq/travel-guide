#!/usr/bin/env python3
"""Grab a URL, saving raw HTML + cleaned text into research/_raw/ningde/.

Usage:
  python3 tools/ningde/grab.py <URL> <slug> [--mobile] [--max N]

Writes:
  research/_raw/ningde/<slug>.html   (raw bytes, decoded best-effort)
  research/_raw/ningde/<slug>.txt    (cleaned visible text)
Prints the cleaned text (truncated to --max, default 12000) to stdout.
"""
import sys, os, re, gzip, zlib, ssl, urllib.request

ROOT = "/home/hukun02/Project/travel-guide"
OUT = os.path.join(ROOT, "research/_raw/ningde")

UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, mobile=False, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA_MOBILE if mobile else UA_DESKTOP,
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
            try:
                raw = zlib.decompress(raw)
            except Exception:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        return raw, r.headers.get("Content-Type", "")


def decode(raw, ctype):
    cands = []
    m = re.search(r"charset=([\w\-]+)", ctype or "", re.I)
    if m:
        cands.append(m.group(1))
    m2 = re.search(rb'charset=["\']?([\w\-]+)', raw[:5000], re.I)
    if m2:
        try:
            cands.append(m2.group(1).decode("ascii"))
        except Exception:
            pass
    cands += ["utf-8", "gb18030", "gbk", "big5", "latin-1"]
    for c in cands:
        try:
            return raw.decode(c)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")


def to_text(t):
    t = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    t = re.sub(r"(?is)<(br|/p|/div|/li|/tr|/h[1-6]|/td|/section|/article)[^>]*>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&ensp;", " "), ("&emsp;", " ")):
        t = t.replace(a, b)
    t = re.sub(r"[ \t\r\f\v\u3000]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


if __name__ == "__main__":
    url = sys.argv[1]
    slug = sys.argv[2]
    mobile = "--mobile" in sys.argv
    mx = 12000
    if "--max" in sys.argv:
        mx = int(sys.argv[sys.argv.index("--max") + 1])
    os.makedirs(OUT, exist_ok=True)
    try:
        raw, ct = fetch(url, mobile=mobile)
    except Exception as e:
        msg = "FETCH_ERROR: %s %s\nURL: %s\n" % (type(e).__name__, e, url)
        with open(os.path.join(OUT, slug + ".txt"), "w") as f:
            f.write(msg)
        print(msg)
        sys.exit(2)
    txt = decode(raw, ct)
    with open(os.path.join(OUT, slug + ".html"), "w") as f:
        f.write("<!-- SOURCE: %s\n     QUERY DATE: 2026-09-15 (mobile=%s) -->\n" % (url, mobile))
        f.write(txt)
    body = to_text(txt)
    with open(os.path.join(OUT, slug + ".txt"), "w") as f:
        f.write("SOURCE: %s\nQUERY DATE: 2026-09-15\n%s\n\n" % (url, "-" * 60))
        f.write(body)
    print(body[:mx])
