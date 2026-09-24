#!/usr/bin/env python3
"""First prints for every channel whose real-time record starts before 2000.

WHY THESE. The vintage census over all 5,928 collected channels found that only 22 have vintages
before 1990 and 119 before 2000. Those are the only series on which a leg's historical calls can be
shown as they would have been seen at the older peaks, so they are the ones worth holding in
first-print form. The rest of the pool is screened on revised data and is honest only about what a
channel measures, not about when it could have been read.

`output_type=4` gives ALFRED's initial release, but ONLY with an explicit real-time period: without
`realtime_start`/`realtime_end` the request defaults to today-to-today and ALFRED answers HTTP 400,
"No vintage dates exist for the specified real-time period". The first run of this file lost all 114
series to that, with a status code that looks like a bad series identifier. `1776-07-04` to
`9999-12-31` is ALFRED's own full range.

Read plainly: `output_type=4` gives ALFRED's initial release: one row per observation date, carrying the
`realtime_start` on which that value was first published. That pair -- observation date and
publication date -- is what the tool needs; the full vintage matrix is larger and adds nothing for a
rule that reads the first print.
"""
import os, re, sys, csv, json, time, threading, queue, urllib.request, urllib.error, urllib.parse

ENV = '/mnt/user-data/uploads/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env'
txt = open(ENV).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
P = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in P.group(1).strip().strip('"').strip("'").split(',') if k.strip()] if P else [])))

CENSUS = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/outputs/vintage_census.csv'
CUT = sys.argv[2] if len(sys.argv) > 2 else '2000-01-01'
DEST = sys.argv[3] if len(sys.argv) > 3 else '/mnt/user-data/outputs/fp2'
os.makedirs(DEST, exist_ok=True)

ids = []
for row in csv.DictReader(open(CENSUS)):
    fv = row['first_vintage']
    if re.match(r'\d{4}-\d{2}-\d{2}$', fv or '') and fv < CUT:
        ids.append(row['series'])
ids = sorted(dict.fromkeys(ids))
todo = [s for s in ids if not os.path.exists(os.path.join(DEST, s + '_firstprint.csv'))]
print('pre-%s series %d, to fetch %d, keys %d' % (CUT[:4], len(ids), len(todo), len(KEYS)), flush=True)

q = queue.Queue()
for s in todo: q.put(s)
lock = threading.Lock(); man = []; t0 = time.time()

def worker(key):
    while True:
        try: sid = q.get_nowait()
        except queue.Empty: return
        u = ('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s&file_type=json'
             '&output_type=4&realtime_start=1776-07-04&realtime_end=9999-12-31'
             % (urllib.parse.quote(sid), key))
        st, n = 'error', 0
        for attempt in range(3):
            try:
                with urllib.request.urlopen(u, timeout=180) as r: d = json.load(r)
                obs = [o for o in d.get('observations', []) if o.get('value') not in (None, '.', '')]
                if obs:
                    with open(os.path.join(DEST, sid + '_firstprint.csv'), 'w', newline='') as f:
                        w = csv.writer(f); w.writerow(['date', 'published', 'value'])
                        for o in obs: w.writerow([o['date'], o['realtime_start'], o['value']])
                    st, n = 'ok', len(obs)
                else: st = 'empty'
                break
            except urllib.error.HTTPError as e:
                st = 'http%d' % e.code
                if e.code == 400: break
                time.sleep(2 + 4 * attempt)
            except Exception as e:
                st = type(e).__name__; time.sleep(2 + 4 * attempt)
        with lock:
            man.append((sid, st, n))
            if len(man) % 25 == 0:
                print('  %d/%d, %.1f min' % (len(man), len(todo), (time.time() - t0) / 60), flush=True)

ths = [threading.Thread(target=worker, args=(k,), daemon=True) for k in KEYS]
for t in ths: t.start()
for t in ths: t.join()
with open(os.path.join(DEST, 'MANIFEST_fp2.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'status', 'n'])
    for r in sorted(man): w.writerow(r)
print('done %.1f min, ok %d of %d' % ((time.time() - t0) / 60, sum(1 for r in man if r[1] == 'ok'), len(man)))
