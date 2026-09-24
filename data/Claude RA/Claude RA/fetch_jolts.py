#!/usr/bin/env python3
"""Pull archived JOLTS news releases (first prints) from the open blsmon1 mirror.
Target: every release dated 2002-2010 (txt preferred, pdf fallback).
Output: Claude RA/jolts_releases/. Writes _done.flag with a count when finished."""
import re, os, time, urllib.request

BASE = "https://blsmon1.bls.gov"
IDX = BASE + "/bls/news-release/jolts.htm"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jolts_releases")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=60).read()

idx = get(IDX).decode("utf-8", "replace")
links = sorted(set(re.findall(r'href="([^"]*jolts_(\d{8})\.(txt|pdf|htm))"', idx)))
picked = {}
for href, d8, ext in links:
    year = int(d8[4:8])
    if not (2002 <= year <= 2010):
        continue
    # prefer txt over htm over pdf
    rank = {"txt": 0, "htm": 1, "pdf": 2}[ext]
    if d8 not in picked or rank < picked[d8][0]:
        picked[d8] = (rank, href, ext)
n = 0
for d8, (rank, href, ext) in sorted(picked.items()):
    url = href if href.startswith("http") else BASE + ("" if href.startswith("/") else "/") + href
    dest = os.path.join(OUT, f"jolts_{d8}.{ext}")
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        n += 1
        continue
    try:
        data = get(url)
        open(dest, "wb").write(data)
        n += 1
        time.sleep(0.8)
    except Exception as e:
        print(d8, "FAIL", e, flush=True)
print("downloaded/present:", n, "of", len(picked))
open(os.path.join(OUT, "_done.flag"), "w").write(str(n))
