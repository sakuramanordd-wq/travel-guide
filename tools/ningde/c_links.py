#!/usr/bin/env python3
"""c_links.py "query" [engine] -- search and print result titles + URLs.
engine: toutiao | sogou | so360
"""
import sys, re, gzip, ssl, urllib.request, urllib.parse, html

UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
UA_M = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

def get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Language": "zh-CN,zh;q=0.9",
                                              "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        raw = r.read()
        if "gzip" in r.headers.get("Content-Encoding", ""):
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "ignore")

def clean(t):
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return html.unescape(re.sub(r"\s+", " ", t)).strip()

def main():
    q = sys.argv[1]
    eng = sys.argv[2] if len(sys.argv) > 2 else "toutiao"
    e = urllib.parse.quote(q)
    urls = {"toutiao": ("https://so.toutiao.com/search?keyword=" + e, UA_M, "toutiao"),
            "sogou": ("https://www.sogou.com/web?query=" + e, UA_PC, "sogou"),
            "so360": ("https://www.so.com/s?q=" + e, UA_PC, "so360")}
    url, ua, tag = urls[eng]
    try:
        raw = get(url, ua)
    except Exception as ex:
        print("ERR", type(ex).__name__, ex); return
    # find anchors with data-url / href + text
    out = []
    for m in re.finditer(r'<a\b[^>]*?(?:href|data-url)="([^"]+)"[^>]*>(.*?)</a>', raw, re.S | re.I):
        href, inner = m.group(1), clean(m.group(2))
        if not inner or len(inner) < 6:
            continue
        if href.startswith("//"):
            href = "https:" + href
        if not href.startswith("http"):
            continue
        if any(d in href for d in ("toutiao.com/search", "sogou.com/web", "so.com/s?", "javascript")):
            continue
        out.append((inner[:110], href))
    seen = set(); n = 0
    for t, h in out:
        k = h.split("?")[0]
        if k in seen:
            continue
        seen.add(k)
        print("%-110s %s" % (t, h))
        n += 1
        if n > 40:
            break
    if n == 0:
        # fallback: show absolute urls present
        for h in dict.fromkeys(re.findall(r'https?://[^\s"\'<>\\]+', raw)):
            if not any(d in h for d in ("toutiao.com", "sogou.com", "so.com", "bytedns", "byteimg",
                                        "pstatp", "snssdk", "w3.org", "schema.org")):
                print("   RAW:", h[:200])
main()
