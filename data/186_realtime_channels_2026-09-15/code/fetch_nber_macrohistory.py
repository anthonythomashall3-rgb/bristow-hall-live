#!/usr/bin/env python3
"""The NBER Macrohistory Database, harvested for the peaks nothing live reaches.

WHY. Collection 171 measured which of the twelve peaks have a series still publishing that covers
them, and found seven with none: 1948, 1953, 1957, 1960, 1969, 1973 and 1980. The first four sit in a
period the modern statistical system barely reaches -- weekly claims begin in 1967, JOLTS in 2000,
WARN notices in 1989 -- and the rule is tested on them anyway, because a rule that has never been
scored on 1948 or 1957 has not been scored on a quarter of the record.

The NBER Macrohistory Database is the largest body of monthly American data for that period: 3,036
series, assembled by the Bureau over decades, covering production, orders, inventories, construction,
credit, business failures, hours, wages, freight and prices from the 1860s to the 1960s.

THE LIMIT, STATED PLAINLY. Almost every one of these series is DISCONTINUED. They cannot give the live
tool a witness for a future recession, and nothing here should be presented as if they could. What they
can do is test whether the rule's architecture works on the four early peaks, which is a different and
still necessary job -- and where one of them has a modern successor, collection 175's splice guard
decides whether the two may be joined, by measured overlap correlation rather than by assertion.

THE SELECTION, declared before the fetch. Every series in release 257 that is monthly, American, and
still publishing in January 1955 or later -- so that it reaches at least the 1957 peak -- whose title
contains one of a fixed list of cyclical words: order, inventory, construction, contract, failure,
bankruptcy, hours, employment, unemployment, claim, freight, carload, ton, steel, production, shipment,
sales, credit, loan, debt, bond, stock price, permit, housing, starts, automobile, machine, tool,
capacity, price, wage. The list is written here rather than chosen after looking at results.
"""
import os, re, csv, json, time, urllib.request, urllib.error
BASE = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(BASE): BASE = os.path.expanduser('~/mnt/Onset Detector Data')
HERE = os.path.join(BASE, '186_realtime_channels_2026-09-15')
CAT, DATA, OUT = os.path.join(HERE, 'catalog'), os.path.join(HERE, 'data_nber'), os.path.join(HERE, 'out')
os.makedirs(DATA, exist_ok=True); os.makedirs(OUT, exist_ok=True)
txt = open(os.path.join(BASE, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
POOL = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in POOL.group(1).strip().strip('"').strip("'").split(',')
                                    if k.strip()] if POOL else [])))
want = []
with open(os.path.join(CAT, 'nber_picked.csv')) as f:
    for r in csv.DictReader(f): want.append((r['id'], r['start'], r['end'], r['title']))
print('to fetch: %d' % len(want), flush=True)
ki, ok, bad = 0, [], []
for i, (sid, st, en, title) in enumerate(want):
    p = os.path.join(DATA, sid + '.csv')
    if os.path.exists(p) and os.path.getsize(p) > 80:
        ok.append((sid, 'cached', '', '', title)); continue
    err = None
    for _ in range(len(KEYS) * 2):
        k = KEYS[ki % len(KEYS)]; ki += 1
        try:
            u = ('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s'
                 '&file_type=json&observation_start=1900-01-01' % (sid, k))
            with urllib.request.urlopen(u, timeout=45) as r:
                d = json.load(r)
            rows = [(o['date'], o['value']) for o in d.get('observations', []) if o['value'] not in ('.', '')]
            if not rows: err = 'empty'; break
            with open(p, 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['date', 'value']); w.writerows(rows)
            ok.append((sid, 'ok', rows[0][0], rows[-1][0], title)); err = None; break
        except urllib.error.HTTPError as e:
            err = 'HTTP %s' % e.code
            if e.code in (429, 403): time.sleep(2); continue
            break
        except Exception as e:
            err = type(e).__name__; time.sleep(1)
    if err: bad.append((sid, err, title))
    time.sleep(0.08)
    if (i + 1) % 50 == 0: print('  %d/%d  ok=%d fail=%d' % (i + 1, len(want), len(ok), len(bad)), flush=True)
with open(os.path.join(OUT, 'MANIFEST_nber.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'status', 'first', 'last', 'title']); w.writerows(ok)
with open(os.path.join(OUT, 'FAILED_nber.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['series', 'reason', 'title']); w.writerows(bad)
print('fetched or cached %d, failed %d' % (len(ok), len(bad)))
