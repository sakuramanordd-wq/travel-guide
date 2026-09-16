#!/usr/bin/env python3
"""Save a Bing/Baidu-mobile/Toutiao search result page as raw evidence.

Usage:
  python3 tools/ningde/srch.py baidu  "query" <slug> [maxchars]
  python3 tools/ningde/srch.py toutiao "query" <slug> [maxchars]

Writes research/_raw/ningde/<slug>.txt and prints the cleaned text.
"""
import sys, os, re, gzip, ssl, urllib.request, urllib.parse

ROOT = "/home/hukun02/Project/travel-guide"
OUT = os.path.join(ROOT, "research/_raw/ningde")

UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

TEMPLATES = {
    "baidu": "https://m.baidu.com/s?word=",
    "toutiao": "https://so.toutiao.com/search?keyword=",
}


def clean(t):
    t = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&ensp;", " "), ("&emsp;", " ")):
        t = t.replace(a, b)
    t = re.sub(r"[ \t\r\f\v\u3000]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


if __name__ == "__main__":
    engine, q, slug = sys.argv[1], sys.argv[2], sys.argv[3]
    mx = int(sys.argv[4]) if len(sys.argv) > 4 else 4000
    url = TEMPLATES[engine] + urllib.parse.quote(q)
    os.makedirs(OUT, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA_MOBILE, "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            raw = r.read()
            if "gzip" in r.headers.get("Content-Encoding", ""):
                raw = gzip.decompress(raw)
        body = clean(raw.decode("utf-8", "ignore"))
        with open(os.path.join(OUT, slug + ".txt"), "w") as f:
            f.write("SEARCH(%s): %s\nURL: %s\nQUERY DATE: 2026-09-15\n%s\n\n"
                    % (engine, q, url, "-" * 60))
            f.write(body)
        print(body[:mx])
    except Exception as e:
        print("SEARCH_ERROR:", type(e).__name__, e)
        sys.exit(2)
