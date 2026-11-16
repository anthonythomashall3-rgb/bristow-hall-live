# -*- coding: utf-8 -*-
"""THE PUBLISHER'S FIRST PRINT, READ AT RELEASE TIME (speed program 1052; Anthony 15 Nov 2026: "we need ALL releases within MINUTES",
"the live page to update at MAXIMUM within 5 minutes"). No AI.

The rule reads the Employment Situation (PAYEMS, UNRATE, UNEMPLOY, LNS13023621), JOLTS (JTSJOL) and the G.17 (INDPRO) from ALFRED
vintage tables (27_realtime_vintages/alfred_all_vintages/<S>_all_vintages.csv). FRED posts those releases 6 to 61 minutes after the
publisher, so until now the site waited for FRED. Here the vintage of the release day is read from the PUBLISHER itself - the BLS
API v2 (whole history, 20-year requests) and the Federal Reserve's G.17 data file (ip_sa.txt, series B50001) - and appended to the
table exactly as bhs_update.py's _append_vintages appends FRED's vintage: the same column name (<S>_<release day, New York>), the same
reindex and the same CSV writer. Tested byte-identical to the FRED path on every series (ops/speed/parity_publisher_first.py).

FRED STAYS THE CROSS-CHECK. Every column written here is recorded in cache/publisher_first.json as provisional. Each later run asks
FRED for its vintage of that day; when FRED has it, the column is compared value for value. Equal: marked verified (the file is
already what the FRED path would have written). Different: FRED's vintage replaces the column (exactly the FRED path's file), the
difference is recorded and the phone is told. A column is written only when the publisher carries a month the table lacks.

    newest(series)               the newest month the publisher carries now (one small request; None if it cannot be read)
    wait(groups, tables, limit)  poll every 30 s until every series of the groups carries a month its table lacks, or the limit
    append(series, al, day, ...) write the publisher's vintage of `day` into the table; returns the column name or None
    verify(al, fred_vintage, ...) reconcile provisional columns with FRED's vintages
"""
import io, os, json, time, datetime, subprocess
import pandas as pd

PF = {  # series -> (publisher, publisher id, release group)
    'PAYEMS': ('bls', 'CES0000000001', 'bls_empsit'),
    'UNRATE': ('bls', 'LNS14000000', 'bls_empsit'),
    'UNEMPLOY': ('bls', 'LNS13000000', 'bls_empsit'),
    'LNS13023621': ('bls', 'LNS13023621', 'bls_empsit'),
    'JTSJOL': ('bls', 'JTS000000000000000JOL', 'bls_jolts'),
    'INDPRO': ('g17', 'B50001', 'fed_g17'),
    'GDPC1': ('bea', 'T10106:1:Q', 'bea_gdp'),   # BEA NIPA Table 1.1.6, line 1 (real GDP, chained dollars), quarterly; needs BEA_API_KEY
}
GROUPS = {}
for _s, (_p, _i, _g) in PF.items(): GROUPS.setdefault(_g, []).append(_s)
G17_URL = 'https://www.federalreserve.gov/releases/g17/Current/ipdisk/ip_sa.txt'
BLS_URL = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
UA = 'Mozilla/5.0 (bristow-hall live site; release-time read)'
HERE = os.path.dirname(os.path.abspath(__file__)); WS = os.path.dirname(HERE)
import sys as _sys; _sys.path.insert(0, HERE)   # s2/bls_fetch.py
STATE = os.path.join(WS, 'cache', 'publisher_first.json')
import tempfile
G17_FILE = os.path.join(tempfile.gettempdir(), 'bhr_g17_ip_sa.txt')   # this run's copy only (2.7 MB; not kept in the repository)
_G17 = {}


def ny_day():
    from zoneinfo import ZoneInfo
    return datetime.datetime.now(ZoneInfo('America/New_York')).date().isoformat()


def _load():
    try: return json.load(open(STATE))
    except Exception: return {'columns': {}}


def _save(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + '.tmp'; json.dump(st, open(tmp, 'w'), indent=1, sort_keys=True); os.replace(tmp, STATE)


def bls_key():
    k = os.environ.get('BLS_API_KEY', '').strip()
    if k: return k
    env = os.path.join(os.path.expanduser('~'), 'mnt', 'Onset Detector Data', 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
    try:
        for ln in open(env):
            if ln.startswith('BLS_API_KEY='): return ln.strip().split('=', 1)[1].strip().strip('"').strip("'") or None
    except Exception: pass
    return None


def _bls(ids, y0, y1, key=None, fresh=True):
    """{BLS id: {Timestamp: value}} through the shared BLS layer (s2/bls_fetch.py: the key, a second key, API v1, the flat files, FRED;
    the source of each series is recorded in bls_fetch.SERVED). `key` is kept for the callers; the layer reads the keys itself."""
    import bls_fetch
    data, served = bls_fetch.fetch(list(ids), y0, y1, fresh=fresh)
    if not data: raise RuntimeError('BLS: no source answered (%s)' % '; '.join(bls_fetch.LOG[-3:]))
    out = {}
    for s, rows in data.items():
        obs = out.setdefault(s, {})
        for y, p, v, _ in rows:
            try: obs[pd.Timestamp(int(y), int(p[1:]), 1)] = float(str(v).replace(',', ''))
            except ValueError: pass      # '-' (a month not collected: the 2025 lapse) is a missing month, as in FRED
    return out


def bls_series(sids, full=False, key=None):
    """{series: pd.Series} from the BLS API: the whole history (full) or the last two years"""
    key = key if key is not None else bls_key()
    ids = [PF[s][1] for s in sids]; y1 = datetime.date.today().year
    got = _bls(ids, 1939 if full else y1 - 1, y1, key, fresh=not full)   # a poll asks afresh; the whole history once per run   # the shared layer splits the years and the series into requests itself
    inv = {PF[s][1]: s for s in sids}
    return {inv[b]: pd.Series(o, dtype=float).sort_index() for b, o in got.items() if o}


def g17_fetch():
    """the G.17 data file, fetched only when the Board's server says it changed (If-Modified-Since); returns its text"""
    import urllib.request, urllib.error
    g = _G17
    hdr = {'User-Agent': UA}
    if g.get('last_modified') and os.path.exists(G17_FILE): hdr['If-Modified-Since'] = g['last_modified']
    try:
        with urllib.request.urlopen(urllib.request.Request(G17_URL, headers=hdr), timeout=60) as r:
            txt = r.read().decode('utf-8', 'replace'); lm = r.headers.get('Last-Modified')
        if '"B50001"' not in txt: raise RuntimeError('G.17 file without B50001')
        os.makedirs(os.path.dirname(G17_FILE), exist_ok=True); open(G17_FILE, 'w').write(txt)
        g['last_modified'] = lm
        return txt
    except urllib.error.HTTPError as e:
        if e.code == 304: return open(G17_FILE).read()
        raise


def g17_series(txt, code='B50001'):
    obs = {}
    for ln in txt.splitlines():
        p = ln.split()
        if len(p) >= 3 and p[0] == '"%s"' % code and p[1].isdigit():
            for m, v in enumerate(p[2:14], 1):
                try: obs[pd.Timestamp(int(p[1]), m, 1)] = float(v)
                except ValueError: pass
    return pd.Series(obs, dtype=float).sort_index()


def bea_key():
    k = os.environ.get('BEA_API_KEY', '').strip()
    if k: return k
    env = os.path.join(os.path.expanduser('~'), 'mnt', 'Onset Detector Data', 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
    try:
        for ln in open(env):
            if ln.startswith('BEA_API_KEY='): return ln.strip().split('=', 1)[1].strip().strip('"').strip("'") or None
    except Exception: pass
    return None


def bea_series(table, line, freq, years='ALL', key=None):
    """one NIPA line from the BEA API, in FRED's units (billions: the API's value x 10^UNIT_MULT / 10^9, in exact decimal arithmetic)"""
    from decimal import Decimal
    import urllib.request, urllib.parse
    key = key or bea_key()
    if not key: raise RuntimeError('no BEA_API_KEY')
    q = urllib.parse.urlencode(dict(UserID=key, method='GetData', datasetname='NIPA', TableName=table, Frequency=freq, Year=years, ResultFormat='JSON'))
    with urllib.request.urlopen(urllib.request.Request('https://apps.bea.gov/api/data?' + q, headers={'User-Agent': UA}), timeout=90) as r:
        d = json.load(r)
    res = d.get('BEAAPI', {}).get('Results', {})
    if isinstance(res, list): res = res[0]
    if 'Error' in res or 'Data' not in res: raise RuntimeError('BEA API: %s' % str(res.get('Error') or d)[:160])
    obs = {}
    for o in res['Data']:
        if str(o.get('LineNumber')) != str(line): continue
        v = str(o.get('DataValue', '')).replace(',', '')
        try: x = Decimal(v) * (Decimal(10) ** int(o.get('UNIT_MULT') or 0)) / (Decimal(10) ** 9)
        except Exception: continue
        tp = o['TimePeriod']
        m = pd.Timestamp(int(tp[:4]), (int(tp[5]) - 1) * 3 + 1, 1) if 'Q' in tp else pd.Timestamp(int(tp[:4]), int(tp[5:7]), 1)
        obs[m] = float(str(x.normalize()))
    return pd.Series(obs, dtype=float).sort_index()


def publisher(sids, full=True, key=None):
    """{series: the publisher's series now} for the given series"""
    out = {}
    for s in sids:
        if PF[s][0] == 'bea':
            tb, ln, fq = PF[s][1].split(':'); y = datetime.date.today().year
            out[s] = bea_series(tb, ln, fq, 'ALL' if full else '%d,%d' % (y - 1, y))
    b = [s for s in sids if PF[s][0] == 'bls']
    if b: out.update(bls_series(b, full=full, key=key))
    if any(PF[s][0] == 'g17' for s in sids):
        g = g17_series(g17_fetch())
        for s in sids:
            if PF[s][0] == 'g17': out[s] = g
    return out


def _differs(al, s, cur=None):
    """the publisher's values now differ from the table's newest vintage on a period both carry (a revision released today)"""
    if cur is None: cur = publisher([s], full=False)[s]
    tab = pd.read_csv(os.path.join(al, '%s_all_vintages.csv' % s), index_col=0); tab.index = pd.to_datetime(tab.index)
    old = pd.to_numeric(tab[tab.columns[-1]], errors='coerce').dropna(); cur = cur.dropna()
    ix = old.index.intersection(cur.index)
    return bool(len(ix)) and bool((old.loc[ix] != cur.loc[ix]).any())


def table_newest(al, s):
    """the newest month of the table's newest vintage, and that vintage's column"""
    tab = pd.read_csv(os.path.join(al, '%s_all_vintages.csv' % s), index_col=0); tab.index = pd.to_datetime(tab.index)
    col = tab.columns[-1]; v = pd.to_numeric(tab[col], errors='coerce').dropna()
    return v.index[-1], col


RID = {'bea_gdp': 53, 'bls_empsit': 50, 'bls_jolts': 192, 'fed_g17': 13, 'bls_state': 112, 'bls_cpi': 10, 'dol_claims': 180}   # FRED's release id of each group (the release calendars are keyed by it)


def release_days(group, extra=None):
    """the New York days the group's release is out, from the site's release calendar (ops/calendar_build.py) and the update's
    own leg calendar; a day is used only if one of them lists it"""
    rid = RID[group]; days = set()
    cal = os.path.join(WS, '..', 'site', 'public', 'ops', 'release_calendar.json')
    try:
        for r in json.load(open(cal)).get('rows', []):
            if str(r.get('release_id')) == str(rid):
                days.update(t['ny'][:10] for t in r.get('times') or [] if t.get('ny'))
    except Exception: pass
    try:
        for s, e in json.load(open(os.path.join(WS, 'cache', 'leg_release_dates.json'))).items():
            if str(e.get('rid')) == str(rid): days.update(e.get('dates') or [])
    except Exception: pass
    days.update(extra or [])
    return days


def write_column(path, s, day, cur, replace=False):
    """bhs_update.py _append_vintages, line for line: the vintage `day` of series s as a column of its table. replace=True keeps
    the column where it stands (a provisional column FRED corrects)."""
    tab = pd.read_csv(path, index_col=0); tab.index = pd.to_datetime(tab.index)
    col = f'{s}_{day.replace("-", "")}'
    if replace and col in tab.columns:
        tab = tab.reindex(tab.index.union(cur.index)).sort_index(); tab[col] = cur.reindex(tab.index)
    else:
        if col in tab.columns: tab = tab.drop(columns=[col])
        tab = tab.reindex(tab.index.union(cur.index)).sort_index(); tab = pd.concat([tab, cur.reindex(tab.index).rename(col)], axis=1)
    tab.index.name = 'date'; tab.to_csv(path, na_rep='')
    return col


def append(al, day=None, series=None, say=print, backup=None, force_day=False, pub=None):
    """for every series whose release is out today (New York) and whose publisher carries a month the table lacks: write the
    publisher's vintage of today. Returns {series: column}. force_day: write `day` whatever the calendar says (parity tests)."""
    day = day or ny_day(); st = _load(); done = {}
    want = []
    for s in (series or list(PF)):
        g = PF[s][2]
        if not force_day and day not in release_days(g): continue
        want.append(s)
    if not want: return done
    try: new_last = {s: v.dropna().index[-1] for s, v in (pub or publisher(want, full=False)).items() if len(v.dropna())}
    except Exception as e: say('publisher first: the publishers could not be read (%s); FRED stays the source this run' % str(e)[:120]); return done
    need = [s for s in want if s in new_last and (new_last[s] > table_newest(al, s)[0] or (PF[s][0] == 'bea' and _differs(al, s, (pub or {}).get(s) if pub else None)))]
    if not need:
        say('publisher first: %s - no month beyond the tables yet' % ', '.join('%s %s' % (s, str(new_last.get(s, '-'))[:7]) for s in want)); return done
    full = pub if pub is not None else publisher(need, full=True)
    for s in need:
        cur = full.get(s)
        if cur is None or not len(cur.dropna()): continue
        cur = cur.dropna(); path = os.path.join(al, '%s_all_vintages.csv' % s)
        if backup: backup(path)
        col = write_column(path, s, day, cur)
        st['columns'][col] = dict(series=s, day=day, publisher=PF[s][0], publisher_id=PF[s][1], newest=str(cur.index[-1].date()),
                                  months=int(len(cur)), status='provisional', written_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        done[s] = col
        say('%-14s PUBLISHER FIRST: vintage %s appended from the %s at %s UTC: data through %s (%d months); FRED cross-checks it when it posts'
            % (s, col, {'bls': 'BLS API', 'bea': 'BEA API', 'g17': 'Federal Reserve G.17 file'}[PF[s][0]], st['columns'][col]['written_utc'][11:19], cur.index[-1].date(), len(cur)))
    _save(st)
    return done


def verify(al, fred_vintage, vintage_dates, say=print, backup=None, alert=None):
    """every provisional column against FRED's vintage of the same day. fred_vintage(s, day) -> pd.Series (FRED's vintage, dropna);
    vintage_dates(s, start) -> list of ISO days. Returns the mismatches."""
    st = _load(); bad = []
    for col, c in sorted(st['columns'].items()):
        if c.get('status') != 'provisional': continue
        s, day = c['series'], c['day']
        try:
            if day not in (vintage_dates(s, day) or []):
                if (datetime.date.fromisoformat(ny_day()) - datetime.date.fromisoformat(day)).days >= 3 and not c.get('told'):
                    c['told'] = True; say('%-14s publisher first: FRED has no vintage of %s three days on; %s stays as read from the publisher' % (s, day, col))
                continue
            cur = fred_vintage(s, day).dropna()
            path = os.path.join(al, '%s_all_vintages.csv' % s)
            tab = pd.read_csv(path, index_col=0); tab.index = pd.to_datetime(tab.index)
            mine = pd.to_numeric(tab[col], errors='coerce') if col in tab.columns else None
            same = mine is not None and set(cur.index) <= set(tab.index) and mine.reindex(tab.index).equals(cur.reindex(tab.index).astype(float))
            c['checked_utc'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            if same:
                c['status'] = 'verified'; say('%-14s publisher first: %s equals FRED\'s vintage of %s on all %d months (verified)' % (s, col, day, len(cur)))
            else:
                diff = []
                if mine is not None:
                    ix = tab.index.union(cur.index); a = mine.reindex(ix); b = cur.reindex(ix)
                    diff = [str(d.date()) for d in ix if not ((pd.isna(a[d]) and pd.isna(b[d])) or a[d] == b[d])]
                if backup: backup(path)
                write_column(path, s, day, cur, replace=True)
                c['status'] = 'replaced_by_fred'; c['diff_months'] = diff[:50]
                msg = '%s: the publisher read of %s differs from FRED\'s vintage on %d month(s) (%s); FRED\'s vintage replaced it' % (s, day, len(diff), ', '.join(diff[:6]))
                bad.append(msg); say('PUBLISHER FIRST MISMATCH ' + msg)
                if alert:
                    try: alert(msg)
                    except Exception: pass
        except Exception as e:
            say('%-14s publisher first: FRED cross-check not done this run (%s); next run' % (s, str(e)[:100]))
    _save(st)
    return bad


# RELEASES THE BUILD READS AS BEFORE, WAITED FOR AT RELEASE TIME (1052, 16 Nov 2026). Nothing is written here for them; the slot one
# minute after the release only waits until the source the build reads has the new period, then builds:
#   bls_cpi     the CPI: the home tile takes a month the BLS API has ahead of FRED (s2/home_tiles.py); out when the BLS API has the
#               month before the release month
#   dol_claims  the weekly claims: out when the Department's release (https://www.dol.gov/ui/data.pdf) was modified today
def _today_et():
    from zoneinfo import ZoneInfo
    return datetime.datetime.now(ZoneInfo('America/New_York')).date()


def _probe_cpi():
    t = _today_et(); m = (pd.Timestamp(t.year, t.month, 1) - pd.DateOffset(months=1))
    got = _bls(['CUSR0000SA0'], t.year - 1, t.year, bls_key()).get('CUSR0000SA0') or {}
    return bool(got) and max(got) >= m, 'BLS CPI through %s' % (str(max(got))[:7] if got else '-')


def _probe_claims():
    import urllib.request
    t = _today_et(); sat = t - datetime.timedelta(days=(t.weekday() + 2) % 7)
    k = os.environ.get('FRED_API_KEY', '').strip(); fe = None
    if k:
        with urllib.request.urlopen('https://api.stlouisfed.org/fred/series?series_id=ICSA&file_type=json&api_key=' + k, timeout=30) as r:
            fe = json.load(r)['seriess'][0]['observation_end']
    # curl's own agent and a HEAD request: the Department's site answers a browser or custom agent with 403 (as bhs_dol_press.py found)
    h = subprocess.run(['curl', '-sSI', '-m', '30', 'https://www.dol.gov/ui/data.pdf'], capture_output=True, text=True).stdout
    lm = next((ln.split(':', 1)[1].strip() for ln in h.splitlines() if ln.lower().startswith('last-modified:')), None)
    import email.utils
    from zoneinfo import ZoneInfo
    dol_today = bool(lm) and email.utils.parsedate_to_datetime(lm).astimezone(ZoneInfo('America/New_York')).date() == t
    # 1052 (16 Nov 2026): the Department's release alone decides - the build takes the new week from it (bhs_dol_press.py, home_tiles.py)
    # and the source gate checks it against the same release; FRED's ICSA is the cross-check when it posts
    return dol_today, 'the Department release %s (FRED ICSA through %s)' % ('out today' if dol_today else 'not yet today', fe)


def _probe_state():
    """State Employment and Unemployment (BLS, 10:00): out when the BLS API has the month before the release month for a State's
    unemployment rate (LAUS) and payrolls (CES State); the live tools (State onset, stress map) read these"""
    t = _today_et(); m = (pd.Timestamp(t.year, t.month, 1) - pd.DateOffset(months=1))
    got = _bls(['LASST060000000000003', 'SMS06000000000000001'], t.year - 1, t.year, bls_key())
    ok = len(got) == 2 and all(v and max(v) >= m for v in got.values())
    return ok, 'BLS State through %s' % ', '.join(str(max(v))[:7] for v in got.values() if v)


def _probe_539():
    """the Department's ETA 539 State file (ar539.csv, about 3:55 PM ET on the claims day): out when its last rows (Wyoming's, the file
    is sorted by State and week; the last 1,500 bytes by an HTTP range request, not the 13 MB file) carry the week ended the Saturday
    before the claims release"""
    t = _today_et(); sat = t - datetime.timedelta(days=(t.weekday() + 2) % 7)
    tail = subprocess.run(['curl', '-sS', '-m', '30', '-r', '-1500', 'https://oui.doleta.gov/unemploy/csv/ar539.csv'], capture_output=True, text=True).stdout
    weeks = [ln.split(',')[1].strip('"') for ln in tail.splitlines() if ln.count(',') > 5 and ln.startswith('"')]
    newest = max(weeks) if weeks else None
    return bool(newest and newest >= sat.isoformat()), 'ETA 539 through %s (Wyoming)' % newest


def _fred_json(url, tries=4):
    """a FRED API call that waits out a 429 (the key's limit is shared by every job running at the moment)"""
    import urllib.request, urllib.error
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1: raise
            time.sleep(15 * (i + 1))


def _probe_fred(g):
    """fred:<SID>:<release time, New York, YYYYMMDDHHMM>: out when FRED's last_updated stamp for the series is at or after the release"""
    import urllib.request
    from zoneinfo import ZoneInfo
    _, sid, rel = g.split(':')
    k = os.environ.get('FRED_API_KEY', '').strip()
    lu = _fred_json('https://api.stlouisfed.org/fred/series?series_id=%s&file_type=json&api_key=%s' % (sid, k))['seriess'][0]['last_updated']   # '2026-11-23 07:36:02-06'
    t = datetime.datetime.strptime(lu[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone(datetime.timedelta(hours=int(lu[19:]))))
    r0 = datetime.datetime.strptime(rel, '%Y%m%d%H%M').replace(tzinfo=ZoneInfo('America/New_York'))
    return t >= r0 - datetime.timedelta(minutes=2), 'FRED %s updated %s' % (sid, lu)


WAIT_ONLY = {'bls_cpi': _probe_cpi, 'dol_claims': _probe_claims, 'bls_state': _probe_state, 'dol_539': _probe_539}
LIVE_TOOLS = {'bls_state', 'bls_empsit', 'dol_539'}   # releases the live tools (live-tools.yml) read: a run at their slot starts the live tools


def default_al():
    return os.environ.get('BHS_C1021_ALFRED') or os.path.abspath(os.path.join(WS, '..', '..', 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages'))


def wait(groups, al=None, limit_s=720, every=30, say=print):
    """THE RELEASE-TIME POLL: the slot starts the run a minute after the release; every `every` seconds the publisher is asked (one
    small BLS request for the group's series; a conditional GET of the G.17 file) until each series of the groups carries a month its
    table lacks, or `limit_s` has passed. Returns the groups that were found new. The build then runs either way."""
    al = al or default_al(); t0 = time.time(); left = [g for g in groups if g in GROUPS or g in WAIT_ONLY or g.startswith('fred:')]; found = []
    base = {s: table_newest(al, s)[0] for g in left if g in GROUPS for s in GROUPS[g]}
    while left:
        for g in list(left):
            try:
                if g in WAIT_ONLY or g.startswith('fred:'):
                    ok, what = WAIT_ONLY[g]() if g in WAIT_ONLY else _probe_fred(g)
                    if ok:
                        say('publisher wait: %s is out (%s) after %.0f s' % (g, what, time.time() - t0)); left.remove(g); found.append(g)
                    continue
                new = publisher(GROUPS[g], full=False)
                if all(s in new and len(new[s].dropna()) and (new[s].dropna().index[-1] > base[s] or (PF[s][0] == 'bea' and _differs(al, s, new[s]))) for s in GROUPS[g]):
                    say('publisher wait: %s is out (%s) after %.0f s' % (g, ', '.join('%s %s' % (s, str(new[s].dropna().index[-1])[:7]) for s in GROUPS[g]), time.time() - t0))
                    left.remove(g); found.append(g)
            except Exception as e:
                say('publisher wait: %s not read (%s)' % (g, str(e)[:100]))
        if not left or time.time() - t0 + every > limit_s: break
        time.sleep(every)
    for g in left: say('publisher wait: %s not out after %.0f s; the build runs with what is in hand (the slot\'s look-again runs follow)' % (g, time.time() - t0))
    return found


if __name__ == '__main__':
    import sys
    a = sys.argv[1:]
    if a[:1] == ['wait']:
        lim = 720
        if '--limit' in a: lim = int(a[a.index('--limit') + 1]); a = a[:a.index('--limit')] + a[a.index('--limit') + 2:]
        wait([g for g in a[1:] if g in GROUPS or g in WAIT_ONLY], limit_s=lim)
        sys.exit(0)
    if a[:1] == ['append']:
        print(append(default_al()))
        sys.exit(0)
    print(__doc__)
