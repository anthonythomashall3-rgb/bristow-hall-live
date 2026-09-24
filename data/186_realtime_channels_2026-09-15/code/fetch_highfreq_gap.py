#!/usr/bin/env python3
"""Every weekly and daily American series FRED has that this programme does not already hold.

WHY A CATALOGUE SWEEP RATHER THAN A WISH LIST. Every earlier harvest in this programme started from a
list of series someone thought of. That finds what was already imagined and misses the rest. This
starts from FRED's own catalogue instead: all 3,560 series tagged usa+weekly and all 7,414 tagged
usa+daily, 7,609 of which came back, minus everything already held, keeping those that begin in
January 2012 or earlier -- so they reach at least one recession -- and whose popularity is 20 or more,
which is FRED's own measure and is used here only to keep the set finite.

WHY HIGH FREQUENCY SPECIFICALLY. The rule's weakness is not knowing things late; it is knowing things
that were published late. A monthly series charged forty days is forty days of blindness. Weekly and
daily series cost twelve days and one. And most of what is daily is a market price, which is **never
revised** -- the category this programme is shortest of, because `price_firstprints.py` showed that
almost every object with a long usable history is a revised one.

Nothing is filtered by whether it looks like a recession indicator. That judgement is what the pricing
sweeps are for, and making it here would smuggle the answer into the question.
"""
import os, re, csv, json, time, urllib.request, urllib.error
BASE = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(BASE): BASE = os.path.expanduser('~/mnt/Onset Detector Data')
HERE = os.path.join(BASE, '186_realtime_channels_2026-09-15')
CAT, DATA, OUT = os.path.join(HERE, 'catalog'), os.path.join(HERE, 'data_highfreq'), os.path.join(HERE, 'out')
os.makedirs(DATA, exist_ok=True)
txt = open(os.path.join(BASE, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
POOL = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in POOL.group(1).strip().strip('"').strip("'").split(',')
                                    if k.strip()] if POOL else [])))
want = [(r['id'], r['freq'], r['title']) for r in csv.DictReader(open(os.path.join(CAT, 'fred_highfreq_new.csv')))]
print('to fetch: %d' % len(want), flush=True)
ki, ok, bad = 0, [], []
for i, (sid, fq, title) in enumerate(want):
    p = os.path.join(DATA, sid + '.csv')
    if os.path.exists(p) and os.path.getsize(p) > 80:
        ok.append((sid, fq, 'cached', '', title)); continue
    err = None
    for _ in range(len(KEYS) * 2):
        k = KEYS[ki % len(KEYS)]; ki += 1
        try:
            u = ('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s'
                 '&file_type=json&observation_start=1900-01-01' % (sid, k))
            with urllib.request.urlopen(u, timeout=60) as r:
                d = json.load(r)
            rows = [(o['date'], o['value']) for o in d.get('observations', []) if o['value'] not in ('.', '')]
            if not rows: err = 'empty'; break
            with open(p, 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['date', 'value']); w.writerows(rows)
            ok.append((sid, fq, rows[0][0], rows[-1][0], title)); err = None; break
        except urllib.error.HTTPError as e:
            err = 'HTTP %s' % e.code
            if e.code in (429, 403): time.sleep(2); continue
            break
        except Exception as e:
            err = type(e).__name__; time.sleep(1)
    if err: bad.append((sid, err, title))
    time.sleep(0.08)
    if (i + 1) % 40 == 0: print('  %d/%d ok=%d fail=%d' % (i + 1, len(want), len(ok), len(bad)), flush=True)
with open(os.path.join(OUT, 'MANIFEST_highfreq.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'freq', 'first', 'last', 'title']); w.writerows(ok)
with open(os.path.join(OUT, 'FAILED_highfreq.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'reason', 'title']); w.writerows(bad)
print('fetched or cached %d, failed %d' % (len(ok), len(bad)))
