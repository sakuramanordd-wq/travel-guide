#!/usr/bin/env bash
# save.sh <outfile> <url> [maxchars]
# Fetches URL via fetch.py (falls back to fetchpage.py), prepends provenance header.
set -u
OUT="research/_raw/ningde/$1"; URL="$2"; MAX="${3:-30000}"
TMP=$(mktemp)
python3 tools/fetch.py "$URL" --max "$MAX" > "$TMP" 2>/dev/null
if [ ! -s "$TMP" ] || [ "$(wc -c < "$TMP")" -lt 400 ]; then
  python3 tools/fetchpage.py "$URL" "$MAX" > "$TMP" 2>/dev/null
fi
if [ ! -s "$TMP" ] || [ "$(wc -c < "$TMP")" -lt 400 ]; then
  M=1 python3 tools/fetchpage.py "$URL" "$MAX" > "$TMP" 2>/dev/null
fi
SZ=$(wc -c < "$TMP")
{
  printf 'URL: %s 抓取日期: 2026-09-15\n' "$URL"
  cat "$TMP"
} > "$OUT"
rm -f "$TMP"
echo "SAVED $OUT bytes=$SZ"
