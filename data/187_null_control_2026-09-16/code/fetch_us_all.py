#!/usr/bin/env python3
"""Re-fetch the whole American channel collection into this workspace, straight from FRED.

WHY RE-FETCH RATHER THAN COPY. The collection lives on the user's machine behind a session mount, and
the screen cannot be run there: background work on that machine only advances while a shell call is
open, and an archive of the 262 MB high-frequency folder stalled twice at 71 MB. Pulling the series
again from the source is deterministic, costs one request each against a twelve-key pool, and leaves
the workspace holding the same data the device holds -- which is where the screens actually run.

The list is the device's own inventory of 5,928 identifiers, so this reproduces that collection rather
than inventing a new one. Series that are not FRED series -- the StatCan extracts, the Philadelphia
Fed vintage extracts -- fail with HTTP 400 and are recorded; they are already held in their own
folders and are not lost.
"""
import os, re, csv, sys, json, time, threading, queue, urllib.request, urllib.error, urllib.parse

ENV = '/mnt/user-data/uploads/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env'
txt = open(ENV).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
P = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in P.group(1).strip().strip('"').strip("'").split(',') if k.strip()] if P else [])))

LIST = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/Onset Detector Data/186_realtime_channels_2026-09-15/catalog/all_series_ids.txt'
DEST = sys.argv[2] if len(sys.argv) > 2 else '/mnt/user-data/outputs/us'
os.makedirs(DEST, exist_ok=True)
ids = sorted(dict.fromkeys(l.strip() for l in open(LIST) if l.strip()))
todo = [s for s in ids if not os.path.exists(os.path.join(DEST, s + '.csv'))]
print('series %d, to fetch %d, keys %d' % (len(ids), len(todo), len(KEYS)), flush=True)

q = queue.Queue()
for s in todo: q.put(s)
lock = threading.Lock(); man = []; t0 = time.time()

def worker(key):
    while True:
        try: sid = q.get_nowait()
        except queue.Empty: return
        u = ('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s&file_type=json'
             % (urllib.parse.quote(sid), key))
        st, n = 'error', 0
        for attempt in range(3):
            try:
                with urllib.request.urlopen(u, timeout=180) as r: d = json.load(r)
                obs = [o for o in d.get('observations', []) if o.get('value') not in (None, '.', '')]
                if obs:
                    tmp = os.path.join(DEST, '.' + sid + '.tmp')
                    with open(tmp, 'w', newline='') as f:
                        w = csv.writer(f); w.writerow(['date', 'value'])
                        for o in obs: w.writerow([o['date'], o['value']])
                    os.replace(tmp, os.path.join(DEST, sid + '.csv'))   # never a half-written file
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
            if len(man) % 250 == 0:
                print('  %d/%d ok=%d, %.1f min' % (len(man), len(todo), sum(1 for r in man if r[1] == 'ok'),
                                                   (time.time() - t0) / 60), flush=True)

ths = [threading.Thread(target=worker, args=(k,), daemon=True) for k in KEYS * 2]
for t in ths: t.start()
for t in ths: t.join()
with open(os.path.join(DEST, 'MANIFEST_us.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'status', 'n'])
    for r in sorted(man): w.writerow(r)
print('done %.1f min, ok %d of %d' % ((time.time() - t0) / 60, sum(1 for r in man if r[1] == 'ok'), len(man)))
