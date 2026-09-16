#!/usr/bin/env python3
"""Sanity-check the generated Zhuji guide.

  * JS syntax check of the inline <script> (node --check)
  * every <img src> / url(images/...) actually exists on disk
  * every data-modal="id" and data-jump target resolves to a MODALS key
  * every MODALS key is referenced from the page (warns about dead data)
  * duplicate MODALS keys
  * rough tag balance for the containers used by the page
"""
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "诸暨3天2夜攻略.html")


def main():
    src = open(HTML, encoding="utf-8").read()
    errors, warns = [], []

    # ---------- script ----------
    m = re.search(r"<script>(.*?)</script>", src, re.S)
    if not m:
        errors.append("no <script> block")
    else:
        js = m.group(1)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(js)
            tmp = f.name
        p = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        if p.returncode != 0:
            errors.append("JS syntax error:\n" + p.stderr.strip()[:4000])
        else:
            print("✓ inline JS parses")

        keys = re.findall(r'^\s*"([a-zA-Z0-9_\-]+)"\s*:\s*\{', js, re.M)
        dup = [k for k, c in Counter(keys).items() if c > 1]
        if dup:
            errors.append(f"duplicate MODALS keys: {dup}")
        print(f"✓ {len(keys)} modal entries")

        # only literal ids: template-literal placeholders like data-modal="${x}" are not real refs
        used = {u for u in re.findall(r'data-modal="([^"$#{]+)"', src)}
        used |= {u for u in re.findall(r'data-jump="([^"$#{]+)"', js)}
        missing = sorted(u for u in used if u not in keys)
        if missing:
            errors.append(f"data-modal targets with no MODALS entry: {missing}")
        else:
            print(f"✓ all {len(used)} referenced modal ids exist")

        dead = sorted(k for k in keys if k not in used and f'"{k}"' not in js.replace(f'"{k}":{{', ""))
        if dead:
            warns.append(f"modal entries never linked (check data-modal): {dead}")

    # ---------- images ----------
    refs = set(re.findall(r'src="(images/[^"]+)"', src))
    refs |= set(re.findall(r'"(images/[^"]+\.jpg)"', src))
    refs |= set(re.findall(r"'(images/[^']+\.jpg)'", src))
    miss = sorted(r for r in refs if not os.path.exists(os.path.join(ROOT, r)))
    if miss:
        errors.append("missing image files: " + ", ".join(miss))
    else:
        print(f"✓ all {len(refs)} referenced images exist")
    unused = []
    for f in sorted(os.listdir(os.path.join(ROOT, "images"))):
        if not f.endswith((".jpg", ".png")):
            continue
        if not re.match(r"(zhuji|hero-zhuji|xishi|wuxie|sizhai|fengqiao|baitalake|zhuji-)", f):
            continue
        rel = "images/" + f
        if rel not in refs:
            unused.append(rel)
    if unused:
        warns.append(f"Zhuji images downloaded but not used: {unused}")

    # ---------- structure ----------
    ids = re.findall(r'<section id="([^"]+)"', src)
    anchors = set(re.findall(r'<a href="#([^"]+)"', src)) | set(re.findall(r"href=\"#([^\"]+)\"", src))
    bad = sorted(a for a in anchors if a not in ids)
    if bad:
        errors.append(f"nav anchors pointing nowhere: {bad}")
    else:
        print(f"✓ nav anchors ok ({len(ids)} sections)")
    if re.search(r"APPEND|TODO|PLACEHOLDER|XXX", src):
        warns.append("placeholder markers left in the output")

    for tag in ("section", "div", "table", "ul"):
        o = len(re.findall(rf"<{tag}[\s>]", src))
        c = len(re.findall(rf"</{tag}>", src))
        if o != c:
            warns.append(f"<{tag}> open {o} vs close {c}")

    print()
    for w in warns:
        print("⚠️ ", w)
    for e in errors:
        print("❌", e)
    if not errors:
        print("\n✅ no blocking problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
