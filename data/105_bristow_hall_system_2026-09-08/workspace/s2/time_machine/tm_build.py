#!/usr/bin/env python3
"""Time Machine (collection 1137, 16 November 2026): the data behind /time-machine/.

For each series below it asks ALFRED (the St. Louis Fed's archive of every published vintage) for every value the series has
ever carried and the day each value was published, and writes one small file per series to site/public/time-machine/d/<ID>.json:
    {"id", "obs": [day numbers of the observation periods], "v": [[vintage day, value, vintage day, value, ...] per period]}
(day numbers count from 1970-01-01). The page reads a period "as known on day D" as the last value whose vintage day is <= D, so
nothing published after D can show. tm.json lists the rows the page draws and a stamp of each file (ver), which the open page polls
to take a new vintage by itself. No AI; standard library only.

AS FAST AS THE PUBLISHER (22 November 2026, collection 1162; Anthony: "automatically live updating with the most current vintage forever
and always and as fast as it possibly can be"). FRED posts some releases long after the publisher (its own clock, ops/state/fred_posted.json:
the jobs report 9:24 to 10:43 AM ET against the Bureau's 8:30, the CPI 9:08 to 10:10, GDP 8:48 to 11:08). So:
  --fast   no FRED call: the release-day vintage the update itself has just written into the program's vintage tables
           (27_realtime_vintages/alfred_all_vintages/<ID>_all_vintages.csv: FRED's vintages, and on a release day the publisher's own
           first print - s2/publisher_first.py, checked against FRED's vintage of that day when FRED posts) is added for UNRATE, PAYEMS,
           JTSJOL, INDPRO, GDPC1 and HOUST; and on a CPI day the BLS's own unadjusted index (CUUR0000SA0) for CPIAUCNS. Runs in every update.
  (full)   every vintage from ALFRED, as before. An entry the fast path wrote that ALFRED does not have yet (dated after ALFRED's newest
           vintage of the series) is kept until ALFRED has that day; then ALFRED's own values stand, and a difference is printed.
  --check  reads ALFRED and writes nothing; says whether ALFRED has anything the files lack (time-machine.yml then starts a site run).
Every file is written whole or not at all (a temporary file, then a rename): the page and the home card never read half a file.

Run: python3 s2/time_machine/tm_build.py [--fast | --check] [--out <site/public/time-machine>]   (the key: FRED_API_KEY, local.env, or the Keychain)
"""
import json, os, re, sys, csv, time, hashlib, datetime, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'site', 'public', 'time-machine'))
if '--out' in sys.argv: OUT = sys.argv[sys.argv.index('--out') + 1]
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))          # the repository (data/105.../workspace/s2/time_machine)
TABLES = os.path.join(ROOT, 'data', 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages')
FAST_TABLES = ['UNRATE', 'PAYEMS', 'JTSJOL', 'INDPRO', 'GDPC1', 'HOUST']          # the tables the update keeps current (bhs_update.py)

# the rows of the page: label, the series (first that holds a value on the day wins), how the number is made, unit, decimals
ROWS = [
    dict(label='Unemployment rate', ids=['UNRATE'], tf='level', unit='percent', dec=1, scale=1),
    dict(label='Payroll jobs, change on the month', ids=['PAYEMS'], tf='diff', unit='thousands', dec=0, scale=1),
    dict(label='Initial jobless claims, week', ids=['ICSA'], tf='level', unit='persons', dec=0, scale=1),
    dict(label='Job openings', ids=['JTSJOL'], tf='level', unit='millions', dec=2, scale=0.001),
    dict(label='Real GDP, growth on the quarter at an annual rate', ids=['GDPC1', 'GNPC96'], tf='qann', unit='percent', dec=1, scale=1),
    dict(label='Industrial production, change on the year', ids=['INDPRO'], tf='yoy', unit='percent', dec=1, scale=1),
    dict(label='Housing starts, annual rate', ids=['HOUST'], tf='level', unit='thousands', dec=0, scale=1),
    dict(label='Consumer prices, change on the year', ids=['CPIAUCNS', 'CPIAUCSL'], tf='yoy', unit='percent', dec=1, scale=1),
]
SIDS = [s for r in ROWS for s in r['ids']]
EPOCH = datetime.date(1970, 1, 1)
def dn(s): return (datetime.date.fromisoformat(s) - EPOCH).days
def day(n): return (EPOCH + datetime.timedelta(n)).isoformat()
def same(a, b):
    if a is None or b is None: return a is None and b is None
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))

def ny_today():
    from zoneinfo import ZoneInfo
    return datetime.datetime.now(ZoneInfo('America/New_York')).date()

def api_key():
    k = os.environ.get('FRED_API_KEY')
    if k: return k.split(',')[0].strip()
    # the update run writes the keys here (update.yml, "write the keys where the rule looks for them"); bhs_update.py reads the same file
    for env in (os.path.join(ROOT, 'data', 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env'),
                os.path.expanduser('~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env')):
        try:
            for ln in open(env):
                if ln.startswith('FRED_API_KEY='):
                    v = ln.strip().split('=', 1)[1].strip().strip('"').strip("'")
                    if v: return v.split(',')[0].strip()
        except OSError: pass
    for root in (os.path.expanduser('~/Projects/Onset Detector Data/_shared'),):
        if os.path.isfile(os.path.join(root, 'apikeys.py')):
            sys.path.insert(0, root)
            from apikeys import key
            return key('FRED').split(',')[0].strip()
    raise SystemExit('no FRED key')

def get(url, tries=6):
    err = ''
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
    # A VALUE ALFRED WITHDRAWS IS WITHDRAWN HERE TOO (22 Nov 2026, collection 1162). A vintage that leaves a period empty ('.': the
    # chain-weighted GDP of January 1996 began in 1959, the 1972 industrial production index in 1947, a claims week left blank) is recorded
    # as null from that day, so the page shows nothing there, as FRED did that day. Until now an empty value was skipped and the older
    # print, in another base year, stood in its place (GDPC1 1947-1958 as of 1996, INDPRO before 1947 as of 1972: 1,325 and 11,160 cells
    # against the program's ALFRED tables). Empty values before a period's first value carry nothing.
    by = {}
    for r in rows:
        by.setdefault(r['date'], []).append((r['realtime_start'], None if r['value'] in ('.', '') else float(r['value'])))
    obs, v = [], []
    for d in sorted(by):
        seq, last = [], None
        for rs, val in sorted(by[d], key=lambda x: x[0]):
            if not same(val, last): seq += [dn(rs), val]; last = val
        if seq: obs.append(dn(d)); v.append(seq)
    assert obs and all(len(s) >= 2 and s[1] is not None for s in v), sid
    return dict(id=sid, obs=obs, v=v, n_values=sum(len(s) // 2 for s in v), first_vintage=min(s[0] for s in v))

def claims_before_alfred(d):
    """ALFRED holds initial claims from its vintage of 28 May 2009. Before it, the weekly releases as printed (the program's first prints,
    cache/national_first_prints_1985_live.csv, 1975 on): each release day carries that week's first print and the prior week as revised.
    Rows whose level is a later print ('-rev' kinds) are left out: they were not public on their release day."""
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

AGENCY = os.path.join(HERE, 'agency_record.csv')
def agency_record(d):
    """THE PUBLISHER'S OWN RECORD WHERE ALFRED IS LATE OR SHORT (22 November 2026, collection 1162; from the RealTime Database, which
    checks every release day against the agency's own record). agency_record.csv, two kinds of row:
      day    ALFRED dated a vintage on another day than the publisher released it: the G.17 of 1939-1952, 1963 and 1985-86 (64 days,
             FRASER's G.12.3 releases as printed; mostly one or two days late, 16 May 1963 a day early), and 11 CPI releases of 1964-1992
             and the jobs report for January 1965 (BLS's historical release-date list; ALFRED 1-5 days off, 7 of them early). Every entry
             of the series on ALFRED's day moves to the release day. December 1973 (1164): the household survey came out 4 January
             1974 (USDL 74-3, FRASER item 56071), the establishment survey a week later, 11 January (FRASER item 497002), so payrolls
             move and the unemployment rate stays.
      print  a value as published that ALFRED does not hold: the BLS JOLTS releases of 15 April 2004 to 13 July 2010 (ALFRED's job
             openings begin 11 August 2010; each release as printed, 255 values) and 14 initial-claims first prints of 1986-1992 that
             the weekly-release file misses (the page showed them a week late). The unemployment rate, seasonally adjusted, of May 1957
             to January 1960 as printed in Census's P-57 reports and BLS's Monthly Report on the Labor Force (1164: 34 values, read in
             collection 999, on BLS's own release days; ALFRED's unemployment rate begins 15 March 1960; for February to December 1960,
             which both hold, the readings equal ALFRED's first prints, value and day).
    Entries merge by day (on one day ALFRED's entry stands); an entry that repeats the value before it is dropped (one per change)."""
    moves, adds = {}, {}
    for r in csv.DictReader(open(AGENCY, encoding='utf-8')):
        if r['series'] != d['id']: continue
        if r['kind'] == 'day': moves[dn(r['alfred_day'])] = dn(r['day'])
        elif r['kind'] == 'print': adds.setdefault(dn(r['period']), []).append((dn(r['day']), float(r['value'])))
    if not moves and not adds: return d
    ix = {o: i for i, o in enumerate(d['obs'])}; moved = added = 0
    for o in adds:
        assert o in ix, '%s: a print for %s, a period ALFRED does not have' % (d['id'], day(o))
    for i, o in enumerate(d['obs']):
        s = d['v'][i]; es = []
        for k in range(0, len(s), 2):
            es.append((moves.get(s[k], s[k]), 1, s[k + 1])); moved += s[k] in moves
        es += [(rd, 0, x) for rd, x in adds.get(o, [])]
        es.sort(key=lambda e: (e[0], e[1])); seq, last = [], 'start'
        for n, src, x in es:
            if seq and seq[-2] == n: seq[-1] = x; last = x; continue               # the same day: ALFRED's entry (sorted last) stands
            if last != 'start' and same(x, last): continue
            if not seq and x is None: continue                                     # nothing to withdraw before a first value
            seq += [n, x]; last = x; added += src == 0
        k = 2                                                                      # a same-day overwrite can leave a repeat behind it
        while k < len(seq):
            if same(seq[k + 1], seq[k - 1]): del seq[k:k + 2]
            else: k += 2
        d['v'][i] = seq
    d['n_values'] = sum(len(s) // 2 for s in d['v']); d['first_vintage'] = min(s[0] for s in d['v'])
    d['agency'] = dict(moved=moved, added=added)
    return d

# ---------------------------------------------------------------------------------------------------- a file's vintages, kept in order
def last_day(d):
    """the newest vintage day in a file (each period's entries are in day order)"""
    return max(s[-2] for s in d['v'])

def tidy(d):
    """periods in date order, counts brought up to date"""
    z = sorted(zip(d['obs'], d['v']), key=lambda x: x[0])
    d['obs'] = [o for o, _ in z]; d['v'] = [s for _, s in z]
    d['n_values'] = sum(len(s) // 2 for s in d['v']); d['first_vintage'] = min(s[0] for s in d['v'])
    return d

def add_vintage(d, ix, o, vday, val):
    """ALFRED's way: a period carries a new entry only where its value changed. Returns 1 if an entry was added."""
    if o in ix:
        s = d['v'][ix[o]]
        if vday <= s[-2] or same(s[-1], val): return 0
        s += [vday, val]; return 1
    if val is None: return 0                                  # a period begins with a value, never with a gap
    d['obs'].append(o); d['v'].append([vday, val]); ix[o] = len(d['obs']) - 1; return 1

def value_on(seq, n):
    """a period's value as known on day n (the page's own rule), None before its first entry"""
    v = None
    for k in range(0, len(seq), 2):
        if seq[k] <= n: v = seq[k + 1]
        else: break
    return v

def keep_provisional(new, old):
    """entries of the held file dated after ALFRED's newest vintage of the series (written by --fast from the publisher before FRED posted)
    stay until ALFRED has that day. Returns (kept, differ): kept (period, day, value); differ (period, day, release-day value, ALFRED's value)
    for an earlier release-day entry whose day ALFRED now has, at another value - ALFRED's stands, and the log says so."""
    amax = last_day(new); ix = {o: i for i, o in enumerate(new['obs'])}; kept, differ = [], []
    held = list(zip(old['obs'], old['v'])); through = old.get('alfred_through')
    for o, s in held:
        for k in range(0, len(s), 2):
            if s[k] > amax and add_vintage(new, ix, o, s[k], s[k + 1]): kept.append((o, s[k], s[k + 1]))
    if through:                                            # entries the last pull did not have from ALFRED, and ALFRED has the day of now
        for o, s in held:
            for k in range(0, len(s), 2):
                if through < s[k] <= amax:
                    a = value_on(new['v'][ix[o]], s[k]) if o in ix else None
                    if a is None or not same(a, s[k + 1]): differ.append((o, s[k], s[k + 1], a))
    tidy(new)
    return kept, differ

def fast_tables(d, sid):
    """the update's own vintage table of the series: every column dated after the file's newest vintage day, added as ALFRED records it"""
    path = os.path.join(TABLES, sid + '_all_vintages.csv')
    if not os.path.exists(path): return []
    last = last_day(d); pat = re.compile(re.escape(sid) + r'_(\d{8})$')
    with open(path, newline='', encoding='utf-8') as f:
        rd = csv.reader(f); head = next(rd); cols = []
        for j, h in enumerate(head[1:], 1):
            m = pat.match(h)
            if m:
                g = m.group(1); vd = dn('%s-%s-%s' % (g[:4], g[4:6], g[6:]))
                if vd > last: cols.append((vd, j))
        if not cols: return []
        cols.sort(); rows = [(r[0], [r[j] if j < len(r) else '' for _, j in cols]) for r in rd if r and r[0]]
    ix = {o: i for i, o in enumerate(d['obs'])}; added = []
    for c, (vd, _) in enumerate(cols):
        if vd > dn(ny_today().isoformat()): continue                      # a column dated after today is not public yet
        for date, vals in rows:
            x = vals[c].strip()
            if not x: continue
            try: val = float(x)
            except ValueError: continue
            if add_vintage(d, ix, dn(date[:10]), vd, val): added.append((dn(date[:10]), vd, val))
    tidy(d)
    return added

def fast_cpi(d):
    """CPIAUCNS on a CPI day (FRED's calendar for the CPI, release 10): the BLS's own unadjusted index, CUUR0000SA0, once the BLS API has
    the month before this one and the file does not. The months both hold must agree to the published three decimals, or nothing is added.
    The unadjusted CPI-U is not revised, so the release-day vintage is the held values and the new month."""
    today = ny_today(); cal = os.path.join(ROOT, 'ops', 'cache', 'fred_release_dates.json')
    try: days = set(json.load(open(cal))['10']['dates'])
    except Exception: return []
    if today.isoformat() not in days: return []
    want = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)       # the month before this one
    if day(d['obs'][-1]) >= want.isoformat(): return []
    sys.path.insert(0, os.path.dirname(HERE))
    import bls_fetch
    data, served = bls_fetch.fetch(['CUUR0000SA0'], today.year - 1, today.year, fresh=True)
    pts = {}
    for r in (data or {}).get('CUUR0000SA0') or []:
        y, per, x = r[0], r[1], r[2]
        if not re.fullmatch(r'M(0[1-9]|1[0-2])', str(per)): continue
        try: pts[dn('%d-%s-01' % (int(y), str(per)[1:]))] = float(x)
        except (TypeError, ValueError): continue
    if not pts: print('time machine fast: the BLS did not answer for the CPI'); return []
    ix = {o: i for i, o in enumerate(d['obs'])}
    for o, x in pts.items():
        if o in ix and d['v'][ix[o]][-1] is not None and abs(round(d['v'][ix[o]][-1], 3) - round(x, 3)) > 0.0005:
            print('time machine fast: CPI %s held %s, the BLS %s: nothing added' % (day(o)[:7], d['v'][ix[o]][-1], x)); return []
    vd = dn(today.isoformat()); added = []
    for o in sorted(pts):
        if o > d['obs'][-1] and o <= dn(want.isoformat()) and add_vintage(d, ix, o, vd, pts[o]): added.append((o, vd, pts[o]))
    tidy(d)
    if added: print('time machine fast: CPIAUCNS %s from the BLS (%s)' % (', '.join('%s %.3f' % (day(o)[:7], x) for o, _, x in added), served.get('CUUR0000SA0')))
    return added

# --------------------------------------------------------------------------------------------------------------------------- writing
def dump(d): return json.dumps(d, separators=(',', ':'))
def write(path, text):
    tmp = path + '.tmp%d' % os.getpid()
    with open(tmp, 'w') as f: f.write(text)
    os.replace(tmp, path)                     # whole or not at all
def load(sid):
    p = os.path.join(OUT, 'd', sid + '.json')
    try: return json.load(open(p))
    except Exception: return None
def stamp(text): return hashlib.sha1(text.encode()).hexdigest()[:12]
def write_meta(changed):
    ver = {}
    for sid in SIDS:
        p = os.path.join(OUT, 'd', sid + '.json')
        if os.path.exists(p): ver[sid] = stamp(open(p).read())
    meta = dict(rows=ROWS, ver=ver, source='ALFRED, Federal Reserve Bank of St. Louis; initial claims before 28 May 2009: the Department of Labor weekly releases as printed; job openings before 11 August 2010: the BLS JOLTS releases as printed (from 15 April 2004); release days checked against the publisher\'s own record; on a release day, before FRED posts it, the publisher\'s own first print (the BLS, the Federal Reserve Board, the BEA)')
    mp = os.path.join(OUT, 'tm.json'); new = dump(meta)
    if not os.path.exists(mp) or open(mp).read() != new: write(mp, new); changed.append('tm.json')

def fast():
    changed = []
    for sid in SIDS:
        d = load(sid)
        if not d: continue
        before = dump(d); added = []
        try:
            if sid in FAST_TABLES: added = fast_tables(d, sid)
            elif sid == 'CPIAUCNS': added = fast_cpi(d)
        except Exception as e:
            print('time machine fast: %s not read (%s: %s)' % (sid, type(e).__name__, str(e)[:120])); continue
        if added and dump(d) != before:
            write(os.path.join(OUT, 'd', sid + '.json'), dump(d)); changed.append(sid)
            print('time machine fast: %-8s %d new entr%s, the newest %s (%s)' % (sid, len(added), 'y' if len(added) == 1 else 'ies',
                  day(max(a[1] for a in added)), ', '.join('%s %g' % (day(o)[:7], x) for o, _, x in added[-3:])))
    write_meta(changed)
    print('time machine fast:', 'CHANGED ' + ' '.join(changed) if changed else 'nothing new before FRED')

def pull(key, sid):
    d = vintages(sid, key)
    if sid == 'ICSA': d = claims_before_alfred(d)
    d = agency_record(d)
    d['alfred_through'] = last_day(d)
    return d

def check():
    """ALFRED against the files, nothing written: newer=true when ALFRED holds a value, since the files' last pull from it, that the files
    do not show on its day. One small request a series (the values in force from the day after that pull)."""
    key = api_key(); newer = []
    for sid in SIDS:
        o = load(sid)
        if not o: newer.append(sid); continue
        since = o.get('alfred_through') or last_day(o)
        q = urllib.parse.urlencode(dict(series_id=sid, api_key=key, file_type='json', realtime_start=day(since + 1), realtime_end='9999-12-31',
                                        limit=100000, sort_order='asc'))
        rows = get('https://api.stlouisfed.org/fred/series/observations?' + q)['observations']
        ix = {x: i for i, x in enumerate(o['obs'])}; miss = []
        for r in rows:
            x, rs, v = dn(r['date']), dn(r['realtime_start']), None if r['value'] in ('.', '') else float(r['value'])
            held = value_on(o['v'][ix[x]], rs) if x in ix else None
            if not same(held, v): miss.append('%s %s=%s' % (r['realtime_start'], r['date'][:7], r['value']))
        if miss: newer.append(sid)
        print('%-9s the file from ALFRED through %s; %d value%s in force since then not in the file%s' % (sid, day(since), len(miss), '' if len(miss) == 1 else 's',
              (': ' + ', '.join(miss[:4]) + (' ...' if len(miss) > 4 else '')) if miss else ''))
    print('time machine check:', ('ALFRED has more: ' + ' '.join(newer)) if newer else 'the files hold everything ALFRED has')
    go = os.environ.get('GITHUB_OUTPUT')
    if go:
        with open(go, 'a') as f: f.write('newer=%s\n' % ('true' if newer else 'false'))

def main():
    if '--fast' in sys.argv: return fast()
    if '--check' in sys.argv: return check()
    key = api_key(); os.makedirs(os.path.join(OUT, 'd'), exist_ok=True); changed = []
    for sid in SIDS:
        d = pull(key, sid); p = os.path.join(OUT, 'd', sid + '.json'); o = load(sid)
        if o:
            kept, differ = keep_provisional(d, o)
            for x in kept: print('kept until ALFRED has it: %s %s, %s as of %s' % (sid, day(x[0])[:10], x[2], day(x[1])))
            for x in differ: print('ALFRED differs from the release-day entry: %s %s on %s: %s, ALFRED %s (ALFRED stands)' % (sid, day(x[0])[:10], day(x[1]), x[2], x[3]))
            # add-only guard: a refresh never loses a period or a vintage ALFRED gave before (a release-day entry ALFRED never confirms may go)
            base = o.get('alfred_through') or last_day(o)
            had = sum(1 for s in o['v'] if s[0] <= base); had_n = sum(1 for s in o['v'] for k in range(0, len(s), 2) if s[k] <= base)
            assert len(d['obs']) >= had and d['n_values'] >= had_n * 0.98, sid + ': the new pull is smaller than the held file'
        new = dump(d)
        if not o or new != dump(o):
            write(p, new); changed.append(sid)
        print('%-9s %5d periods %7d values, first vintage %s, ALFRED through %s, %d kB%s' % (sid, len(d['obs']), d['n_values'],
              day(d['first_vintage']), day(d['alfred_through']), len(new) // 1024, ' CHANGED' if sid in changed else ''))
    write_meta(changed)
    print('time machine data:', 'CHANGED ' + ' '.join(changed) if changed else 'unchanged')

if __name__ == '__main__': main()
