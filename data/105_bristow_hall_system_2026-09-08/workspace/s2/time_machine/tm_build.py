#!/usr/bin/env python3
"""Time Machine (collection 1137, 16 November 2026): the data behind /time-machine/.

For each series below it asks ALFRED (the St. Louis Fed's archive of every published vintage) for every value the series has
ever carried and the day each value was published, and writes one small file per series to site/public/time-machine/d/<ID>.json:
    {"id", "obs": [day numbers of the observation periods], "v": [[vintage day, value, vintage day, value, ...] per period]}
(day numbers count from 1970-01-01). The page reads a period "as known on day D" as the last value whose vintage day is <= D, so
nothing published after D can show. tm.json lists the rows the page draws. No AI; standard library only.

Run: python3 s2/time_machine/tm_build.py [--out <site/public/time-machine>]     (FRED_API_KEY in the environment, or the Keychain)
"""
import json, os, sys, time, datetime, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'site', 'public', 'time-machine'))
if '--out' in sys.argv: OUT = sys.argv[sys.argv.index('--out') + 1]

# the rows of the page: label, the series (first that holds a value on the day wins), how the number is made, unit, decimals
ROWS = [
    dict(label='Unemployment rate', ids=['UNRATE'], tf='level', unit='percent', dec=1, scale=1),
    dict(label='Payroll jobs, change on the month', ids=['PAYEMS'], tf='diff', unit='thousands', dec=0, scale=1),
    dict(label='Initial jobless claims, week', ids=['ICSA'], tf='level', unit='persons', dec=0, scale=1),
    dict(label='Job openings', ids=['JTSJOL'], tf='level', unit='millions', dec=2, scale=0.001),
    dict(label='Real GDP, growth on the quarter at an annual rate', ids=['GDPC1', 'GNPC96'], tf='qann', unit='percent', dec=1, scale=1),
    dict(label='Industrial production, change on the year', ids=['INDPRO'], tf='yoy', unit='percent', dec=1, scale=1),
    dict(label='Housing starts, annual rate', ids=['HOUST'], tf='level', unit='thousands', dec=0, scale=1),
    dict(label='Consumer prices, change on the year', ids=['CPIAUCSL'], tf='yoy', unit='percent', dec=1, scale=1),
]
EPOCH = datetime.date(1970, 1, 1)
def dn(s): return (datetime.date.fromisoformat(s) - EPOCH).days

def api_key():
    k = os.environ.get('FRED_API_KEY')
    if k: return k.split(',')[0].strip()
    for root in (os.path.expanduser('~/Projects/Onset Detector Data/_shared'),):
        if os.path.isdir(root):
            sys.path.insert(0, root)
            from apikeys import key
            return key('FRED').split(',')[0].strip()
    raise SystemExit('no FRED key')

def get(url, tries=6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r: return json.load(r)
        except Exception as e:
            err = type(e).__name__ + (' %s' % getattr(e, 'code', ''))          # never the URL: it carries the key
            time.sleep(3 * (i + 1))
    raise SystemExit('ALFRED did not answer: ' + err)

def vintages(sid, key):
    rows, off = [], 0
    while True:
        q = urllib.parse.urlencode(dict(series_id=sid, api_key=key, file_type='json', realtime_start='1776-07-04',
                                        realtime_end='9999-12-31', limit=100000, offset=off, sort_order='asc'))
        j = get('https://api.stlouisfed.org/fred/series/observations?' + q)
        rows += j['observations']; off += len(j['observations'])
        if off >= int(j['count']) or not j['observations']: break
    by = {}
    for r in rows:
        if r['value'] in ('.', ''): continue
        by.setdefault(r['date'], []).append((r['realtime_start'], float(r['value'])))
    obs, v = [], []
    for d in sorted(by):
        seq, last = [], None
        for rs, val in sorted(by[d]):
            if val != last: seq += [dn(rs), val]; last = val
        obs.append(dn(d)); v.append(seq)
    assert obs and all(len(s) >= 2 for s in v), sid
    return dict(id=sid, obs=obs, v=v, n_values=sum(len(s) // 2 for s in v), first_vintage=min(s[0] for s in v))

def claims_before_alfred(d):
    """ALFRED holds initial claims from its vintage of 28 May 2009. Before it, the weekly releases as printed (the program's first prints,
    cache/national_first_prints_1985_live.csv, 1975 on): each release day carries that week's first print and the prior week as revised.
    Rows whose level is a later print ('-rev' kinds) are left out: they were not public on their release day."""
    import csv
    p = os.path.join(HERE, '..', '..', 'cache', 'national_first_prints_1985_live.csv'); first = d['first_vintage']; add = {}
    for r in csv.DictReader(open(p, encoding='utf-8')):
        if 'rev' in (r.get('kind') or '') or not r.get('release_date') or not r.get('ic_week_ended') or not r.get('icsa'): continue
        rd, wk = dn(r['release_date']), dn(r['ic_week_ended'])
        if rd >= first or rd < wk: continue
        ok = lambda x: 50000 <= float(x) <= 2000000          # a weekly print outside this band before 2009 is a misread number (19 Nov 2026: 321 for 321,000)
        if not ok(r['icsa']): print('refused: initial claims of %s in the release of %s' % (r['icsa'], r['release_date'])); continue
        if r.get('icsa_prev_rev') and not ok(r['icsa_prev_rev']): print('refused: a revised figure of %s in the release of %s' % (r['icsa_prev_rev'], r['release_date'])); r['icsa_prev_rev'] = ''
        add.setdefault(wk, {})[rd] = float(r['icsa'])
        if r.get('icsa_prev_rev'): add.setdefault(wk - 7, {}).setdefault(rd, float(r['icsa_prev_rev']))
    ix = {o: i for i, o in enumerate(d['obs'])}; n = 0
    for wk, vs in add.items():
        if wk not in ix: continue
        seq, last = [], None
        for rd in sorted(vs):
            if vs[rd] != last: seq += [rd, vs[rd]]; last = vs[rd]
        if d['v'][ix[wk]][1] == last: d['v'][ix[wk]] = d['v'][ix[wk]][2:]       # ALFRED's first value repeats the last print: one entry
        d['v'][ix[wk]] = seq + d['v'][ix[wk]]; n += len(seq) // 2
    d['n_values'] = sum(len(s) // 2 for s in d['v']); d['first_vintage'] = min(s[0] for s in d['v']); d['before_alfred'] = n
    return d

def main():
    key = api_key(); os.makedirs(os.path.join(OUT, 'd'), exist_ok=True); changed = []
    for sid in [s for r in ROWS for s in r['ids']]:
        d = vintages(sid, key); p = os.path.join(OUT, 'd', sid + '.json')
        if sid == 'ICSA': d = claims_before_alfred(d)
        new = json.dumps(d, separators=(',', ':'))
        old = open(p).read() if os.path.exists(p) else ''
        if new != old:
            if old:                                                        # add-only guard: a refresh never loses a period or a vintage
                o = json.loads(old)
                assert len(d['obs']) >= len(o['obs']) and d['n_values'] >= o['n_values'] * 0.98, sid + ': the new pull is smaller than the held file'
            open(p, 'w').write(new); changed.append(sid)
        print('%-9s %5d periods %7d values, first vintage %s, %d kB%s' % (sid, len(d['obs']), d['n_values'],
              EPOCH + datetime.timedelta(d['first_vintage']), len(new) // 1024, ' CHANGED' if sid in changed else ''))
    meta = dict(rows=ROWS, source='ALFRED, Federal Reserve Bank of St. Louis; initial claims before 28 May 2009: the Department of Labor weekly releases as printed')
    mp = os.path.join(OUT, 'tm.json'); new = json.dumps(meta, separators=(',', ':'))
    if not os.path.exists(mp) or open(mp).read() != new: open(mp, 'w').write(new); changed.append('tm.json')
    print('time machine data:', 'CHANGED ' + ' '.join(changed) if changed else 'unchanged')

if __name__ == '__main__': main()
