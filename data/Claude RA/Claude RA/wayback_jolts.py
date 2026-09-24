#!/usr/bin/env python3
"""JOLTS first prints 2002-2010 via Wayback snapshots of the release page.
For each month, ask the availability API for a snapshot near mid-month and
save the archived release HTML. Gentle pacing (8s) for rate limits.
Output: jolts_wayback/jolts_YYYYMM.html + _done.flag with count."""
import json, os, time, urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jolts_wayback")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
TARGET = "www.bls.gov/news.release/jolts.nr0.htm"

def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()

months = [(y, m) for y in range(2002, 2011) for m in range(1, 13)]
months = [(y, m) for (y, m) in months if (y, m) >= (2002, 7) and (y, m) <= (2010, 9)]
n = 0
for y, m in months:
    dest = os.path.join(OUT, f"jolts_{y}{m:02d}.html")
    if os.path.exists(dest) and os.path.getsize(dest) > 5000:
        n += 1
        continue
    ts = f"{y}{m:02d}20"
    try:
        av = json.loads(get(f"http://archive.org/wayback/available?url={TARGET}&timestamp={ts}", 60))
        snap = av.get("archived_snapshots", {}).get("closest", {})
        if snap.get("available"):
            data = get(snap["url"], 120)
            open(dest, "wb").write(data)
            n += 1
            print(y, m, "ok", snap.get("timestamp"), flush=True)
        else:
            print(y, m, "no snapshot", flush=True)
    except Exception as e:
        print(y, m, "FAIL", e, flush=True)
    time.sleep(8)
print("saved:", n)
open(os.path.join(OUT, "_done.flag"), "w").write(str(n))
