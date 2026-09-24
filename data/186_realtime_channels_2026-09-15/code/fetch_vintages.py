#!/usr/bin/env python3
"""Fetch every vintage of the revised series that priced admissibly, so they can be read causally.

WHY. `price_realtime.py` found six objects that fire three to eight times in sixty-odd years with no
false alarm and put two or three calls inside one day to three months early. Every one of them is
built on a series that is revised after first publication. Read from today's file they measure what
the number BECAME, not what it said at the time, and a walk that used them would be reading the
future. They are upper bounds until their vintages are read, and this is what reads them.

WHAT A VINTAGE IS HERE. ALFRED holds, for each observation date, every value that observation has ever
had and the range of real-world dates over which each value stood. Asking for `realtime_start=1776-07-04`
and `realtime_end=9999-12-31` returns one row per observation-vintage pair. The FIRST PRINT of an
observation is the row whose `realtime_start` is earliest, and the day it became public is that
`realtime_start`. That is the only figure a rule standing on that day could have read.

The CSV endpoint fails on wide pulls -- HTTP/2 INTERNAL_ERROR and HTTP/1.1 empty replies, on both
machines -- so this uses the JSON API, which does not. Requests are spread across the key pool
because FRED's limit is per key, and a single key at two processes went over the cap and returned 403
to everything including the live site's own refresh.
"""
import os, re, csv, json, time, urllib.request, urllib.error
BASE = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(BASE): BASE = os.path.expanduser('~/mnt/Onset Detector Data')
HERE = os.path.join(BASE, '186_realtime_channels_2026-09-15')
VDIR, OUT = os.path.join(HERE, 'vintages'), os.path.join(HERE, 'out')
os.makedirs(VDIR, exist_ok=True); os.makedirs(OUT, exist_ok=True)
CFG = os.path.join(BASE, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
txt = open(CFG).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
POOL = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in POOL.group(1).strip().strip('"').strip("'").split(',')
                                    if k.strip()] if POOL else [])))

# Declared in advance. Every revised series that priced admissibly, plus the ones the existing legs
# already stand on, so the whole set can be re-priced on first prints in one pass.
WANT = ['PERMIT', 'HOUST', 'PERMIT1', 'DRALACBS', 'DRSFRMACBS', 'DRCCLACBS', 'DRBLACBS', 'CORCACBS',
        'BBKMCOIX', 'CFNAI', 'BUSINV', 'ISRATIO', 'NEWORDER', 'AMTMNO', 'ACOGNO', 'DGORDER',
        'ICSA', 'IC4WSA', 'CCSA', 'IURSA', 'TEMPHELPS', 'AWHMAN', 'MANEMP', 'TOTALSA',
        'RSAFS', 'INDPRO', 'TCU', 'PAYEMS', 'UNRATE', 'JTSJOL', 'NFCI', 'ANFCI']

def pull(sid, key):
    u = ('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s&file_type=json'
         '&realtime_start=1776-07-04&realtime_end=9999-12-31&observation_start=1900-01-01' % (sid, key))
    with urllib.request.urlopen(u, timeout=180) as r:
        return json.load(r)

ki, rep = 0, []
for sid in WANT:
    p = os.path.join(VDIR, sid + '_vintages.csv')
    if os.path.exists(p) and os.path.getsize(p) > 200:
        rep.append((sid, 'cached', os.path.getsize(p), '', '')); continue
    err = None
    for _ in range(len(KEYS) * 3):
        k = KEYS[ki % len(KEYS)]; ki += 1
        try:
            d = pull(sid, k)
            obs = [o for o in d.get('observations', []) if o['value'] not in ('.', '')]
            if not obs:
                err = 'empty'; break
            with open(p, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['date', 'realtime_start', 'realtime_end', 'value'])
                for o in obs:
                    w.writerow([o['date'], o['realtime_start'], o['realtime_end'], o['value']])
            # the first print of each observation, which is all a causal rule may read
            fp, seen = [], set()
            for o in obs:
                if o['date'] in seen: continue
                seen.add(o['date']); fp.append((o['date'], o['realtime_start'], o['value']))
            fp.sort()
            with open(os.path.join(VDIR, sid + '_firstprint.csv'), 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['date', 'published', 'value']); w.writerows(fp)
            rep.append((sid, 'ok', len(obs), fp[0][0], fp[-1][0])); err = None; break
        except urllib.error.HTTPError as e:
            err = 'HTTP %s' % e.code
            if e.code in (429, 403): time.sleep(3); continue
            break
        except Exception as e:
            err = type(e).__name__ + ':' + str(e)[:60]; time.sleep(2)
    if err: rep.append((sid, err, 0, '', ''))
    time.sleep(0.3)

with open(os.path.join(OUT, 'MANIFEST_vintages.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'status', 'rows', 'first_obs', 'last_obs']); w.writerows(rep)
ok = [r for r in rep if r[1] in ('ok', 'cached')]
print('vintages fetched or already held: %d of %d' % (len(ok), len(WANT)))
for r in rep:
    if r[1] not in ('ok', 'cached'): print('  FAIL %-12s %s' % (r[0], r[1]))
for r in rep:
    if r[1] == 'ok': print('  ok   %-12s rows=%-8d %s .. %s' % (r[0], r[2], r[3], r[4]))
