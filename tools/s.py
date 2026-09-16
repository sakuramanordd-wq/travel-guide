#!/usr/bin/env python3
"""Search-engine text fetch for research discovery.
Usage: python3 s.py "query" [engine] [maxchars]
engine: sogou (default) | so360 | bing
Prints cleaned search-result text (titles + snippets).
"""
import sys, re, gzip, urllib.request, urllib.parse, ssl

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9", "Accept-Encoding": "gzip"})
    r = urllib.request.urlopen(req, timeout=timeout, context=CTX)
    raw = r.read()
    if "gzip" in r.headers.get("Content-Encoding", ""):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "ignore")

def clean(t):
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()

if __name__ == "__main__":
    q = sys.argv[1]
    eng = sys.argv[2] if len(sys.argv) > 2 else "sogou"
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 7000
    e = urllib.parse.quote(q)
    urls = {
        "sogou": "https://www.sogou.com/web?query=" + e,
        "so360": "https://www.so.com/s?q=" + e,
        "bing": "https://cn.bing.com/search?q=" + e + "&ensearch=0",
    }
    try:
        t = clean(get(urls[eng]))
        print(t[:n])
    except Exception as ex:
        print("SEARCH_ERROR:", type(ex).__name__, ex)
