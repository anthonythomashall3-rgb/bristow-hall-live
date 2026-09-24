#!/usr/bin/env python3
"""The FRED fetcher, parallelised across the key pool. Same data, same files, a fraction of the time.

WHY THIS IS EXACTLY AS ACCURATE AS THE SERIAL VERSION. Each series is an independent request whose
result is written to its own file. Nothing is shared, nothing is aggregated, no ordering matters. Two
series fetched at the same moment produce byte-identical files to the same two fetched a minute apart.
The only thing parallelism can break is the rate limit, and that is handled by construction rather
than by hoping.

FRED'S LIMIT IS PER KEY, NOT PER ADDRESS -- collection 110 established this the hard way: two
processes against one key at 110 requests a minute each went over the 120-per-minute cap and FRED
returned 403 to everything, including the live site's own refresh. So this runs **one worker per key**
and paces each worker below the cap independently. More keys is the lever; more threads on one key is
not.

A worker that meets a 429 or a 403 backs off and retries on its own key rather than moving to another,
because moving would put a second worker's traffic on that key and cause exactly the failure the
per-key design avoids.
"""
import os, re, csv, sys, json, time, threading, queue, urllib.request, urllib.error
BASE = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(BASE): BASE = os.path.expanduser('~/mnt/Onset Detector Data')
HERE = os.path.join(BASE, '186_realtime_channels_2026-09-15')
CAT, OUT = os.path.join(HERE, 'catalog'), os.path.join(HERE, 'out')
txt = open(os.path.join(BASE, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
POOL = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in POOL.group(1).strip().strip('"').strip("'").split(',')
                                    if k.strip()] if POOL else [])))
LIST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(CAT, 'fred_highfreq_new2.csv')
DEST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'data_highfreq')
TAG = sys.argv[3] if len(sys.argv) > 3 else 'highfreq2'
os.makedirs(DEST, exist_ok=True)
# MEASURED, AND CORRECTED. The first run used one worker per key at 100 requests a minute each: twelve
# keys, 1,200 requests a minute from a single address. Failures went from 6 in the first 600 to 150 in
# the next 200 and then the run stalled entirely with every worker blocked. FRED's documented 120 a
# minute is PER KEY, but there is evidently an address-level limit as well, and the per-key design does
# not protect against that. Four workers at 60 a minute is 240 a minute from this address -- still four
# times the serial rate, and demonstrably under whatever the address limit is.
# MEASURED AGAIN, AND THE FIRST DIAGNOSIS WAS WRONG. Cutting to four workers did not help, so the
# stall was not the rate limit. A direct probe of six keys returned 200 OK on every one, with latencies
# of 2.8 to 16.4 seconds. FRED is simply slow at the moment, and at eight seconds a request four
# workers give thirty a minute no matter what the pacing says. This work is LATENCY-bound, not
# rate-bound, so concurrency is the lever and the pacing gap is nearly irrelevant.
# The 150 failures in the first run are therefore most likely invalid identifiers -- the catalogue
# includes discontinued series that return HTTP 400 -- not throttling. The failure file now records the
# reason for each so a permanent 400 can be told from a retryable 429, and the retryable ones re-run.
PER_MIN = 45
GAP = 60.0 / PER_MIN
MAX_WORKERS = 12

want = []
with open(LIST) as f:
    for r in csv.DictReader(f):
        sid = r.get('id') or r.get('series')
        if sid: want.append((sid, r.get('title', '')))
todo = [(s, t) for s, t in want
        if not (os.path.exists(os.path.join(DEST, s + '.csv')) and os.path.getsize(os.path.join(DEST, s + '.csv')) > 80)]
print('listed %d, already held %d, to fetch %d, workers %d'
      % (len(want), len(want) - len(todo), len(todo), min(len(KEYS), MAX_WORKERS)), flush=True)

q = queue.Queue()
for item in todo: q.put(item)
lock = threading.Lock()
ok, bad, done = [], [], [0]

def worker(key):
    last = 0.0
    while True:
        try: sid, title = q.get_nowait()
        except queue.Empty: return
        wait = GAP - (time.time() - last)
        if wait > 0: time.sleep(wait)
        last = time.time()
        err = None
        for attempt in range(4):
            try:
                u = ('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s'
                     '&file_type=json&observation_start=1900-01-01' % (sid, key))
                with urllib.request.urlopen(u, timeout=60) as r:
                    d = json.load(r)
                rows = [(o['date'], o['value']) for o in d.get('observations', []) if o['value'] not in ('.', '')]
                if not rows: err = 'empty'; break
                with open(os.path.join(DEST, sid + '.csv'), 'w', newline='') as f:
                    w = csv.writer(f); w.writerow(['date', 'value']); w.writerows(rows)
                with lock: ok.append((sid, rows[0][0], rows[-1][0], len(rows), title))
                err = None; break
            except urllib.error.HTTPError as e:
                err = 'HTTP %s' % e.code
                # back off on THIS key rather than moving to another: moving would double a second
                # worker's traffic on that key, which is the failure this design avoids
                if e.code in (429, 403): time.sleep(5 * (attempt + 1)); continue
                break
            except Exception as e:
                err = type(e).__name__; time.sleep(2)
        if err:
            with lock: bad.append((sid, err, title))
        with lock:
            done[0] += 1
            if done[0] % 100 == 0:
                print('  %d/%d  ok=%d fail=%d' % (done[0], len(todo), len(ok), len(bad)), flush=True)

t0 = time.time()
ts = [threading.Thread(target=worker, args=(k,), daemon=True) for k in KEYS[:MAX_WORKERS]]
for t in ts: t.start()
for t in ts: t.join()
with open(os.path.join(OUT, 'MANIFEST_%s.csv' % TAG), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'first', 'last', 'n', 'title']); w.writerows(ok)
with open(os.path.join(OUT, 'FAILED_%s.csv' % TAG), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'reason', 'title']); w.writerows(bad)
print('fetched %d, failed %d, in %.1f minutes (%.1f series/minute)'
      % (len(ok), len(bad), (time.time() - t0) / 60, len(ok) / max((time.time() - t0) / 60, 1e-9)))
