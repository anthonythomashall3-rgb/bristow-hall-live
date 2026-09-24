#!/usr/bin/env python3
"""Which of the 5,928 collected channels can EVER be read in real time, and from when?

THE QUESTION THIS ANSWERS. A channel that screens well on revised data is not yet a leg: the tool has
to have been able to read it on the day it would have fired. Three legs currently in the amended
system are priced on series whose vintage history begins in 2011 or 2021, so their historical calls
cannot be demonstrated as they would have been seen -- and until this census exists, the same is
unknown for every other channel in the pool.

WHAT IT DOES. One `series/vintagedates` request per series, ascending, limit 1: the count of vintages
and the date of the first. That is enough to sort the whole collection into channels readable in real
time before 1970, before 2000, only recently, and not at all. It is deliberately the cheapest possible
question -- the full vintage matrices are large, and are worth fetching only for the channels that
survive the screen.

Series with no vintages answer HTTP 400; that is recorded as 'none', which is an answer, not a
failure. Series not in FRED at all -- the NBER Macrohistory files, StatCan, the RTDSM extracts -- also
answer 400, and are separated by source afterwards rather than being silently dropped here.
"""
import os, re, sys, json, time, threading, queue, urllib.request, urllib.error

ENV = '/mnt/user-data/uploads/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env'
txt = open(ENV).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
P = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in P.group(1).strip().strip('"').strip("'").split(',') if k.strip()] if P else [])))

LIST = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/Onset Detector Data/186_realtime_channels_2026-09-15/catalog/all_series_ids.txt'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/mnt/user-data/outputs/vintage_census.csv'
ids = [l.strip() for l in open(LIST) if l.strip()]
done = set()
if os.path.exists(OUT):
    for l in open(OUT).read().splitlines()[1:]:
        if l: done.add(l.split(',')[0])
todo = [s for s in ids if s not in done]
print('series %d, already done %d, to do %d, keys %d' % (len(ids), len(done), len(todo), len(KEYS)), flush=True)

q = queue.Queue()
for s in todo: q.put(s)
lock = threading.Lock()
fh = open(OUT, 'a')
if not done: fh.write('series,n_vintages,first_vintage\n'); fh.flush()
n_done = [0]; t0 = time.time()

def worker(key):
    while True:
        try: sid = q.get_nowait()
        except queue.Empty: return
        n, first = -1, 'error'
        for attempt in range(3):
            u = ('https://api.stlouisfed.org/fred/series/vintagedates?series_id=%s&api_key=%s'
                 '&file_type=json&sort_order=asc&limit=1' % (urllib.parse.quote(sid), key))
            try:
                with urllib.request.urlopen(u, timeout=60) as r: d = json.load(r)
                n, first = d.get('count', 0), (d.get('vintage_dates') or ['-'])[0]; break
            except urllib.error.HTTPError as e:
                if e.code == 400: n, first = 0, 'none'; break
                time.sleep(2 + 4 * attempt)
            except Exception:
                time.sleep(2 + 4 * attempt)
        with lock:
            fh.write('%s,%d,%s\n' % (sid, n, first)); n_done[0] += 1
            if n_done[0] % 200 == 0:
                fh.flush()
                print('  %d/%d, %.1f min' % (n_done[0], len(todo), (time.time() - t0) / 60), flush=True)

import urllib.parse
ths = [threading.Thread(target=worker, args=(k,), daemon=True) for k in KEYS * 2]
for t in ths: t.start()
for t in ths: t.join()
fh.flush(); fh.close()
print('census complete in %.1f min' % ((time.time() - t0) / 60))
