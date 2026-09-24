#!/usr/bin/env python3
"""First prints only, taken from FRED's own initial-release view rather than reconstructed.

WHY THIS REPLACES THE RECONSTRUCTION. `fetch_vintages.py` asks for every vintage and takes the
earliest row per observation as the first print. That is correct but expensive, and for a weekly
series revised weekly it is enormous: the NFCI pull hit the API's 100,000-row ceiling having reached
only August 1976, so its first prints beyond that date were silently missing. A truncated vintage file
that LOOKS complete is worse than none, because the reconstruction would quietly stop in 1976 and the
rest would read as absent rather than wrong.

FRED's `output_type=4` returns the initial release of each observation directly — one row per
observation, with the date it first appeared. It is the same figure the reconstruction produces, taken
from the source rather than assembled, and it does not grow with the number of revisions.

Both files are kept. The full vintage files answer "what did this series say on date X", which the
revision objects in collection 180 need. These answer "what was the first thing it said", which is
what a leg reads.
"""
import os, re, csv, json, time, urllib.request, urllib.error
BASE = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(BASE): BASE = os.path.expanduser('~/mnt/Onset Detector Data')
HERE = os.path.join(BASE, '186_realtime_channels_2026-09-15')
VDIR, OUT = os.path.join(HERE, 'vintages'), os.path.join(HERE, 'out')
os.makedirs(VDIR, exist_ok=True)
txt = open(os.path.join(BASE, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
POOL = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in POOL.group(1).strip().strip('"').strip("'").split(',')
                                    if k.strip()] if POOL else [])))
WANT = ['PERMIT', 'HOUST', 'PERMIT1', 'DRALACBS', 'DRSFRMACBS', 'DRCCLACBS', 'DRBLACBS', 'CORCACBS',
        'BBKMCOIX', 'CFNAI', 'BUSINV', 'ISRATIO', 'NEWORDER', 'AMTMNO', 'ACOGNO', 'DGORDER',
        'ICSA', 'IC4WSA', 'CCSA', 'IURSA', 'TEMPHELPS', 'AWHMAN', 'MANEMP', 'TOTALSA',
        'RSAFS', 'INDPRO', 'TCU', 'PAYEMS', 'UNRATE', 'JTSJOL', 'NFCI', 'ANFCI',
        'ADPWNUSNERSA', 'CARTS', 'BUSAPPWNSAUS', 'HBUSAPPWNSAUS', 'GSCPI']

def pull(sid, key, offset=0):
    u = ('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s&file_type=json'
         '&output_type=4&realtime_start=1776-07-04&realtime_end=9999-12-31'
         '&observation_start=1900-01-01&limit=100000&offset=%d' % (sid, key, offset))
    with urllib.request.urlopen(u, timeout=180) as r:
        return json.load(r)

ki, rep = 0, []
for sid in WANT:
    p = os.path.join(VDIR, sid + '_firstprint.csv')
    rows, err, off = [], None, 0
    while True:
        got = None
        for _ in range(len(KEYS) * 3):
            k = KEYS[ki % len(KEYS)]; ki += 1
            try:
                got = pull(sid, k, off); err = None; break
            except urllib.error.HTTPError as e:
                err = 'HTTP %s' % e.code
                if e.code in (429, 403): time.sleep(3); continue
                break
            except Exception as e:
                err = type(e).__name__; time.sleep(2)
        if got is None: break
        obs = [o for o in got.get('observations', []) if o['value'] not in ('.', '')]
        rows += [(o['date'], o['realtime_start'], o['value']) for o in obs]
        n = int(got.get('count', 0)); off += int(got.get('limit', 100000))
        if off >= n or not got.get('observations'): break
        time.sleep(0.2)
    if err or not rows:
        rep.append((sid, err or 'empty', 0, '', '')); continue
    seen, fp = set(), []
    for d, rs, v in sorted(rows):
        if d in seen: continue
        seen.add(d); fp.append((d, rs, v))
    with open(p, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'published', 'value']); w.writerows(fp)
    rep.append((sid, 'ok', len(fp), fp[0][0], fp[-1][0]))
    time.sleep(0.2)
with open(os.path.join(OUT, 'MANIFEST_firstprints.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'status', 'n', 'first_obs', 'last_obs']); w.writerows(rep)
print('first prints: %d of %d' % (sum(1 for r in rep if r[1] == 'ok'), len(WANT)))
for r in rep:
    print(('  ok   %-16s n=%-7d %s .. %s' % (r[0], r[2], r[3], r[4])) if r[1] == 'ok'
          else ('  FAIL %-16s %s' % (r[0], r[1])))
