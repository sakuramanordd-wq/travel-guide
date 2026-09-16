#!/usr/bin/env python3
"""Toutiao (头条搜索) text fetch for research discovery.
Usage: python3 t.py "query" [maxchars]
Prints cleaned search-result text (titles + snippets), mobile UA.
"""
import sys, re, gzip, urllib.request, urllib.parse, ssl

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

q = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
url = "https://so.toutiao.com/search?keyword=" + urllib.parse.quote(q)
try:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9", "Accept-Encoding": "gzip"})
    r = urllib.request.urlopen(req, timeout=25, context=CTX)
    raw = r.read()
    if "gzip" in r.headers.get("Content-Encoding", ""):
        raw = gzip.decompress(raw)
    t = raw.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    print(t.strip()[:n])
except Exception as e:
    print("SEARCH_ERROR:", type(e).__name__, e)
