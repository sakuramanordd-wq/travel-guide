#!/usr/bin/env python3
"""Fetch a URL (tolerant SSL) and save body text to research/_raw/... with a source header.
Usage: python3 tools/research_fetch.py URL OUTFILE GRADE [NOTE]
Grade: A=official/bank, B=mainstream media, C=UGC
"""
import sys, os, re, ssl, gzip, zlib, urllib.request, datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
UA_M = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

def ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    try:
        c.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception:
        pass
    c.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    return c

def body_text(h):
    h = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', ' ', h, flags=re.S | re.I)
    h = re.sub(r'<br\s*/?>|</(p|div|li|tr|h\d)>', '\n', h, flags=re.I)
    h = re.sub(r'</t[dh]>', '\t', h, flags=re.I)
    h = re.sub(r'<[^>]+>', '', h)
    import html as _h
    h = _h.unescape(h)
    h = re.sub(r'[ \t\u00a0]+', ' ', h)
    h = re.sub(r'\n\s*\n+', '\n', h)
    return h.strip()

def main():
    url, out, grade = sys.argv[1], sys.argv[2], sys.argv[3]
    note = sys.argv[4] if len(sys.argv) > 4 else ""
    mobile = os.environ.get("M", "").strip() in ("1", "mobile", "true")
    ua = UA_M if mobile else UA
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": ua,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        })
        r = urllib.request.urlopen(req, timeout=35, context=ctx())
        raw = r.read()
        enc = r.headers.get("Content-Encoding", "")
        if "gzip" in enc:
            raw = gzip.decompress(raw)
        elif "deflate" in enc:
            try: raw = zlib.decompress(raw)
            except Exception: raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        txt = raw.decode("utf-8", "ignore")
        if '<' in txt[:2000]:
            txt = body_text(txt)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write("SOURCE URL: %s\n" % url)
            f.write("FETCHED: %s (local date)\n" % datetime.date.today().isoformat())
            f.write("SOURCE GRADE: %s\n" % grade)
            if note:
                f.write("NOTE: %s\n" % note)
            f.write("STATUS: OK (http %s, %d chars raw)\n" % (getattr(r, "status", "?"), len(raw)))
            f.write("=" * 70 + "\n")
            f.write(txt + "\n")
        print("OK %s -> %s (%d chars)" % (url, out, len(txt)))
    except Exception as e:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write("SOURCE URL: %s\n" % url)
            f.write("FETCHED: %s\n" % datetime.date.today().isoformat())
            f.write("SOURCE GRADE: %s\n" % grade)
            f.write("STATUS: FETCH_FAILED: %r\n" % (e,))
            f.write("NOTE: %s\n" % note)
        print("FAIL %s : %r" % (url, e))

main()
