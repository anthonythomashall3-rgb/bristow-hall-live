# -*- coding: utf-8 -*-
"""THE BRISTOW-HALL SYSTEM - the backstop tier (20 September 2026, audit chat; collection 249).

Three outside rules with zero false alarms on our own real-time record (249/RECORD-backstop-2026-09-20.md), run
live beside the rule as a SHADOW tier: they never open, move or close an episode. Their job is the floor - if the
core ever misses a recession, one of these turns on three to five months after the peak and the miss is logged.

    SOS_NSA   52-week change of the 26-week average of the unadjusted insured unemployment rate (CCNSA / COVEMP),
              line +0.20 pp  (our declared form of O'Trakoun-Scavette's SOS; administrative, unrevised)
    LMSI30    states whose 13-week average insured rate stands >= 0.20 pp above its value 52 weeks earlier, counted
              over the 50 states + DC from the Department's ETA 539 file (rate = c8/c18 keyed by c2); line 30 states
              (our declared form of the SF Fed Labor Market Stress Indicator)
    CFNAI     Chicago Fed National Activity Index, 3-month average, below -0.70 (the Chicago Fed's own rule)

Reads FRED (CCNSA, COVEMP, CFNAIMA3) with the key in local.env, the ETA 539 file the live system already refreshes
(37_dol_eta5159_2026-09/raw/ar539.csv; the Department's own file if that is stale), and out/bhs_state.json for the
rule's standing. Writes out/backstop_state.json, ../site/public/detector/backstop.json and
../site/public/backstop/index.html. Alerts (s2/alert.sh) when a backstop is ON while the rule stands closed.
Never raises: any failure is written into the state file and the page, and the run goes on. Run from the workspace:
    python3 s2/backstop.py
"""
import os, sys, json, time, datetime as dt, subprocess, urllib.request, urllib.parse, io
import pandas as pd, numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # the workspace
COLL = os.path.dirname(HERE)
ROOT = os.path.dirname(COLL)                                                 # Onset Detector Data
MNT = os.path.join(os.path.expanduser('~'), 'mnt', 'Onset Detector Data')
ENV = os.path.join(MNT, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
CACHE = os.path.join(HERE, 'cache', 'backstop'); os.makedirs(CACHE, exist_ok=True)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
SITE = os.path.join(COLL, 'site', 'public')
NOW = dt.datetime.utcnow().replace(microsecond=0)
LINES = {'SOS_NSA': 0.20, 'LMSI30': 30, 'CFNAI': -0.70}
FIRES = {}          # each rule's full firing history by PUBLICATION day (collection 256: the opener's union is built from these)
GATE_WEEKS = 13     # the opener's persistence gate: one quarter ON (256; the plain opener was refused)
STATES51 = ['AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']

def key():
    try:
        for line in open(ENV):
            if line.startswith('FRED_API_KEY='): return line.strip().split('=', 1)[1].strip().strip('"').strip("'")
    except Exception: pass
    return os.environ.get('FRED_API_KEY', '')

def fred(series):
    """Latest observations of a FRED series, cached; the cache is returned if the fetch fails."""
    cp = os.path.join(CACHE, series + '.json')
    try:
        url = 'https://api.stlouisfed.org/fred/series/observations?' + urllib.parse.urlencode({'series_id': series, 'api_key': key(), 'file_type': 'json', 'observation_start': '1960-01-01'})
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'bristow-hall-backstop/1.0'}), timeout=60) as r: j = json.load(r)
        obs = [(o['date'], float(o['value'])) for o in j['observations'] if o['value'] not in ('.', '')]
        json.dump({'fetched': NOW.isoformat(), 'obs': obs}, open(cp, 'w'))
    except Exception as e:
        if not os.path.exists(cp): raise
        j = json.load(open(cp)); obs = j['obs']; obs_note = 'cached %s (%r)' % (j['fetched'], e)
    s = pd.Series(dict((pd.Timestamp(d), v) for d, v in obs)).sort_index()
    return s

def release_next(series):
    """The next day the publisher releases this series, from FRED's own release calendar - never an estimate (20 Sep 2026:
    the data page said 'about Sep 24, 2026' for CFNAIMA3 while FRED's calendar for release 219 listed Sep 21). Cached for
    the day; the cache stands if FRED does not answer. After 10:30 ET on a release day the next date is the one after."""
    from zoneinfo import ZoneInfo
    now = dt.datetime.now(ZoneInfo('America/New_York')); today = now.date().isoformat()
    cp = os.path.join(CACHE, series + '_release_dates.json'); c = None; ds = None
    try:
        c = json.load(open(cp))
        if c.get('day') == today: ds = c.get('dates')
    except Exception: c = None
    if ds is None:
        try:
            def q(path, **kw):
                u = 'https://api.stlouisfed.org/fred/' + path + '?' + urllib.parse.urlencode(dict(kw, api_key=key(), file_type='json'))
                with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'bristow-hall-backstop/1.0'}), timeout=60) as r: return json.load(r)
            rid = q('series/release', series_id=series)['releases'][0]['id']
            ds = [d['date'] for d in q('release/dates', release_id=rid, realtime_start=today, include_release_dates_with_no_data='true',
                                       sort_order='asc', limit=6)['release_dates'] if d['date'] >= today]
            json.dump({'day': today, 'release_id': rid, 'dates': ds}, open(cp, 'w'))
        except Exception:
            ds = [d for d in (c or {}).get('dates', []) if d >= today]
    if ds and ds[0] == today and (now.hour, now.minute) >= (10, 30) and len(ds) > 1: return ds[1]
    return ds[0] if ds else None

def _ar539_read(p):
    a = pd.read_csv(p, low_memory=False); a.columns = [c.strip().strip('"').lower() for c in a.columns]
    a['st'] = a['st'].astype(str).str.strip().str.upper(); a['wk'] = pd.to_datetime(a['c2'], errors='coerce')
    a['cw'] = pd.to_numeric(a['c8'], errors='coerce'); a['ce'] = pd.to_numeric(a['c18'], errors='coerce')
    a = a.dropna(subset=['wk', 'cw', 'ce']); a = a[a['ce'] > 0]; a['r'] = 100.0 * a['cw'] / a['ce']
    W = a.pivot_table(index='wk', columns='st', values='r', aggfunc='median'); W.index = W.index.to_period('W-SAT').to_timestamp('W-SAT')
    return W[~W.index.duplicated()].sort_index()

_AR539 = {}
def ar539():
    """The Department's ETA 539 file as a week x state table of insured rates.

    WHICH COPY IS CURRENT, NOT WHICH IS NEWEST ON DISK (20 September 2026, collection 274). The file this prefers lives in
    the collection (37/raw/ar539.csv), which the cloud bundle does not carry, and freshness was the file's own modification
    date - a git checkout sets that to the moment it ran. On the runner the 13 MB file was therefore downloaded twice a
    run, once for the opener and once for the tier. The test is the data now - a copy is current if it holds a week ending
    within sixteen days, whichever copy it is - so the file is downloaded at most once a run, and only when the copy in
    hand is more than sixteen days behind. Within one process the table is parsed once.
    """
    if _AR539: return _AR539['W'], _AR539['p']
    best = None
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    for p in (os.path.join(ROOT, '37_dol_eta5159_2026-09', 'raw', 'ar539.csv'), os.path.join(CACHE, 'ar539.csv')):
        if not os.path.exists(p): continue
        try: W = _ar539_read(p)
        except Exception: continue
        if best is None or W.index.max() > best[0].index.max(): best = (W, p)
        if (now - W.index.max().to_pydatetime()).days <= 16:
            _AR539.update(W=W, p=p); return W, p
    try:
        with urllib.request.urlopen(urllib.request.Request('https://oui.doleta.gov/unemploy/csv/ar539.csv', headers={'User-Agent': 'bristow-hall-backstop/1.0'}), timeout=120) as r: raw = r.read()
        p2 = os.path.join(CACHE, 'ar539.csv'); open(p2, 'wb').write(raw)
        W = _ar539_read(p2); _AR539.update(W=W, p=p2); return W, p2
    except Exception:
        if best is None: raise
        _AR539.update(W=best[0], p=best[1]); return best

def since(fire):
    f = fire.dropna().astype(bool)
    if f.empty: return None, None
    cur = bool(f.iloc[-1]); k = len(f) - 1
    while k > 0 and bool(f.iloc[k - 1]) == cur: k -= 1
    return cur, f.index[k].strftime('%Y-%m-%d')

def rule_sos_nsa():
    cc = fred('CCNSA'); ce = fred('COVEMP')
    ce = ce.reindex(cc.index.union(ce.index)).interpolate(limit_direction='both').reindex(cc.index).rolling(13, center=True, min_periods=1).median()
    r = (100 * cc / ce).dropna(); ma = r.rolling(26).mean(); ind = (ma - ma.shift(52)).dropna()
    on, s = since(ind > LINES['SOS_NSA'])
    FIRES['SOS_NSA'] = pd.Series((ind > LINES['SOS_NSA']).values, index=ind.index + pd.Timedelta(days=5))
    return {'reading': round(float(ind.iloc[-1]), 3), 'line': LINES['SOS_NSA'], 'on': on, 'since': s, 'data_through': ind.index[-1].strftime('%Y-%m-%d'),
            'unit': 'pp, 52-week change of the 26-week average of CCNSA/COVEMP', 'vintage': 'administrative, unrevised (one-tick margin measured in collection 248)'}

def rule_lmsi30():
    W, src = ar539(); W = W.reindex(columns=[c for c in STATES51 if c in W.columns])
    ma = W.rolling(13).mean(); acc = (ma - ma.shift(52)) >= 0.20
    rep = (ma.notna() & ma.shift(52).notna()).sum(axis=1); cnt = acc.sum(axis=1)
    ok = rep >= 30; fire = pd.Series(np.where(rep >= 45, cnt >= 30, cnt / rep.replace(0, np.nan) >= 30 / 51), index=W.index)[ok]
    on, s = since(fire); last = W.index[-1]
    FIRES['LMSI30'] = pd.Series(fire.values.astype(bool), index=fire.index + pd.Timedelta(days=12))
    lit = [c for c in W.columns if bool(acc.loc[last, c])]
    return {'reading': int(cnt.iloc[-1]), 'line': 30, 'on': on, 'since': s, 'data_through': last.strftime('%Y-%m-%d'), 'reporting': int(rep.iloc[-1]),
            'states_accelerating': lit, 'unit': 'states of 51 whose 13-week average insured rate is >= 0.20 pp above a year earlier', 'vintage': 'ETA 539 c8/c18 by c2, administrative, unrevised', 'source_file': src}

def rule_cfnai():
    s = fred('CFNAIMA3'); on, sn = since(s < LINES['CFNAI'])
    FIRES['CFNAI'] = pd.Series((s < LINES['CFNAI']).values, index=s.index + pd.DateOffset(months=1) + pd.Timedelta(days=23))
    return {'reading': round(float(s.iloc[-1]), 2), 'line': LINES['CFNAI'], 'on': on, 'since': sn, 'data_through': s.index[-1].strftime('%Y-%m-%d'),
            'unit': 'CFNAI three-month average', 'vintage': 'current (the Chicago Fed revises the index)', 'next': release_next('CFNAIMA3')}

# ---- collection 335 (23 September 2026; plan L5): MICHEZ, Michaillat-Saez's rule, as a fourth SHADOW reading - the smaller of the
# ---- unemployment indicator (the three-month average rate over its lowest three-month average of the prior twelve months, first prints)
# ---- and the vacancy indicator (the twelve-month high of the three-month mean vacancy rate over its current value; the vacancy rate
# ---- = openings / (openings + payrolls), openings shifted forward a month as the authors do; JOLTS first prints), at or above 0.29 -
# ---- collection 249's declared form. Evidence on the scoreboard; it never opens, moves or closes an episode.
def rule_michez(line=0.29):
    _root = os.path.expanduser('~/Projects/Onset Detector Data')
    if not os.path.isdir(_root): _root = os.path.expanduser('~/mnt/Onset Detector Data')
    u = pd.read_csv(os.path.join(_root, '186_realtime_channels_2026-09-15', 'vintages', 'UNRATE_firstprint.csv'), parse_dates=['date', 'published']).sort_values('date').drop_duplicates('date', keep='first').set_index('date')
    u3 = u['value'].rolling(3).mean(); uh = (u3 - u3.rolling(12).min().shift(1))
    J = pd.read_csv(os.path.join(HERE, 'cache', 'alfred_first_JTSJOL.csv'), index_col=0, parse_dates=['release']); J.index = pd.to_datetime(J.index)
    Pt = pd.read_csv(os.path.join(_root, 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages', 'PAYEMS_all_vintages.csv'), index_col=0); Pt.index = pd.to_datetime(Pt.index)
    pay = pd.to_numeric(Pt[Pt.columns[-1]], errors='coerce').dropna() * 1000.0
    op = J['first'].astype(float) * 1000.0; v = 100.0 * op / (op + pay.reindex(op.index)); v = v.dropna()
    v.index = v.index + pd.offsets.MonthBegin(1); vpub = pd.Series(J['release'].values, index=J.index + pd.offsets.MonthBegin(1))
    vma = v.rolling(3).mean(); vh = vma.rolling(12).max().shift(1) - vma
    idx = uh.dropna().index.intersection(vh.dropna().index)
    ind = pd.concat([uh.reindex(idx), vh.reindex(idx)], axis=1).min(axis=1)
    pub = pd.concat([u['published'].reindex(idx), pd.to_datetime(vpub.reindex(idx))], axis=1).max(axis=1)
    fire = pd.Series((ind >= line).values, index=pd.to_datetime(pub.values)).sort_index()
    on, sn = since(fire); FIRES['Michez'] = fire
    # the day the reading next moves (23 September 2026, after v3.74's ops check found the row with no release day): the next
    # month's reading needs that month's unemployment rate (the Employment Situation) and the prior month's job openings (JOLTS,
    # which the vacancy side carries one month forward), so it is published when the later of the two still missing is out
    _M = idx[-1] + pd.offsets.MonthBegin(1)
    _need = [d for d in ([release_next('UNRATE')] if _M not in u.index else []) + ([release_next('JTSJOL')] if _M not in v.index else []) if d]
    return {'reading': round(float(ind.iloc[-1]), 3), 'line': line, 'on': on, 'since': sn, 'data_through': idx[-1].strftime('%Y-%m-%d'), 'published': str(pd.Timestamp(pub.iloc[-1]).date()),
            'next': max(_need) if _need else None,
            'unemployment_indicator': round(float(uh.reindex(idx).iloc[-1]), 3), 'vacancy_indicator': round(float(vh.reindex(idx).iloc[-1]), 3),
            'unit': 'points: the smaller of the unemployment indicator (Sahm form, first prints) and the vacancy indicator (12-month high of the 3-month mean vacancy rate over its value), line 0.29',
            'vintage': 'first prints (UNRATE, JOLTS); payrolls the latest vintage', 'shadow_only': True}

# ---- collection 366 (24 September 2026; handoff B item 17; Anthony: "yes"): the WEEKLY ECONOMIC INDEX (Lewis, Mertens and Stock;
# ---- Federal Reserve Bank of Dallas; FRED WEI, release 465, weekly ending Saturday, posted Thursdays) as a fifth SHADOW reading -
# ---- the only weekly read on the labour-hoarding type (output falling while the claims register is still; 349, 365). The reading
# ---- is the 13-week mean, ON at or below 0 (output contracting for a quarter). Current vintage (the index is revised weekly;
# ---- ALFRED vintages held from 16 April 2020, so it is judged in real time on 2020 and 2024 only - 2024 it stayed positive).
# ---- Never in the union, never on the scoreboard (its real-time record is too short for a column beside daters read since 1994).
def rule_wei(line=0.0):
    s = fred('WEI'); m13 = s.rolling(13).mean().dropna()
    fire = pd.Series((m13 <= line).values, index=m13.index + pd.Timedelta(days=5))     # a Saturday week is posted the Thursday after
    on, sn = since(fire); FIRES['WEI'] = fire
    return {'reading': round(float(m13.iloc[-1]), 2), 'line': line, 'on': on, 'since': sn, 'data_through': m13.index[-1].strftime('%Y-%m-%d'),
            'latest_week': round(float(s.iloc[-1]), 2), 'next': release_next('WEI'),
            'unit': '13-week mean of the index (scaled to four-quarter GDP growth, percent), line 0; the latest week %.2f' % float(s.iloc[-1]),
            'vintage': 'current (the Dallas Fed revises the index weekly; ALFRED vintages held from 16 April 2020)', 'shadow_only': True}

# ---- THE OPENER (20 September 2026, collection 256; Anthony's Q1 ruling). The union of the three rules, gated by one quarter
# ---- of persistence: a call on the first day the union has been ON for GATE_WEEKS consecutive weeks, one call per episode
# ---- (episodes separated by more than 182 days without a firing), dated the calendar month of the call. Replayed causally
# ---- on the walked record 1956-2026 the gated opener changes nothing and false-alarms never; the plain opener was refused
# ---- (it moves 1990 and 2024 outside the window). bhs_build.py reads the calls file and may open an episode tagged b.
UNION_RULES = ('SOS_NSA', 'LMSI30', 'CFNAI')   # the gated opener's union is these three and nothing else (collection 256); Michez (335) is a shadow reading only
def union_series():
    fires = [FIRES[k] for k in UNION_RULES if k in FIRES]
    idx = sorted(set().union(*[set(f.index) for f in fires]))
    U = pd.Series(False, index=pd.DatetimeIndex(idx))
    for f in fires:
        f = f[~f.index.duplicated(keep='last')].sort_index()
        ff = f.reindex(U.index, method='ffill').fillna(False).astype(bool)
        last = pd.Series(f.index, index=f.index).reindex(U.index, method='ffill')
        ff = ff & ((U.index - last) <= pd.Timedelta(days=45))     # a reading carries at most 45 days
        U = U | ff.values
    return U

def gated_calls(on, gap_days=182, need_weeks=GATE_WEEKS):
    out = []; run_start = None; prev_on = None; episode_called = False
    for t, v in on.items():
        if v:
            if run_start is None:
                run_start = t
                if prev_on is None or (t - prev_on).days > gap_days: episode_called = False
            if not episode_called and (t - run_start).days >= 7 * (need_weeks - 1):
                out.append(t); episode_called = True
            prev_on = t
        else:
            run_start = None
    return out

def opener_state():
    if not FIRES: return {'error': 'no rule histories'}
    U = union_series(); calls = gated_calls(U)
    on_now = bool(U.iloc[-1]) if len(U) else False
    k = len(U) - 1
    while k > 0 and bool(U.iloc[k - 1]) == on_now: k -= 1
    run_start = U.index[k] if len(U) else None
    weeks_on = int((U.index[-1] - run_start).days // 7) + 1 if on_now else 0
    would_open = (run_start + pd.Timedelta(days=7 * (GATE_WEEKS - 1))).strftime('%Y-%m-%d') if on_now else None
    rows = 'pub,dated\n' + ''.join('%s,%s\n' % (t.strftime('%Y-%m-%d'), t.strftime('%Y-%m-01')) for t in calls)
    open(os.path.join(OUT, 'backstop_opener_calls.csv'), 'w').write(rows)
    return {'gate_weeks': GATE_WEEKS, 'union_on': on_now, 'union_since': run_start.strftime('%Y-%m-%d') if run_start is not None else None, 'weeks_on': weeks_on,
            'gate_passed': bool(on_now and weeks_on >= GATE_WEEKS), 'would_open_on': would_open, 'data_through': U.index[-1].strftime('%Y-%m-%d') if len(U) else None,
            'calls': [t.strftime('%Y-%m-%d') for t in calls], 'n_calls': len(calls), 'collection': '256_backstop_opener_replay_2026-09-20'}

def standing():
    try: return json.load(open(os.path.join(OUT, 'bhs_state.json'))).get('standing')
    except Exception: return None

def _opener_text(o):
    if not o or 'error' in o: return 'not computed' + (' (%s)' % o['error'] if o and 'error' in o else '')
    if o.get('union_on'): return 'union ON since %s, week %d of %d%s' % (o.get('union_since'), o.get('weeks_on', 0), o.get('gate_weeks', 13), ' - GATE PASSED' if o.get('gate_passed') else ' (opens %s if it stays on)' % o.get('would_open_on'))
    return 'union off (last call %s; %d calls since 1967, every one inside an episode the Rule had already opened)' % ((o.get('calls') or ['none'])[-1], o.get('n_calls', 0))

def page(state):
    rows = ''
    for k in ('SOS_NSA', 'LMSI30', 'CFNAI', 'Michez', 'WEI'):
        r = state['rules'].get(k, {})
        if 'error' in r: rows += '<tr><td>%s</td><td colspan="5">not computed: %s</td></tr>' % (k, r['error']); continue
        rows += '<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td class="%s">%s</td><td>%s</td><td>%s</td></tr>' % (
            k, r['reading'], r['line'], 'on' if r['on'] else 'off', 'ON' if r['on'] else 'off', r['since'] or '', r['data_through'])
    st = state.get('standing') or {}
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bristow-Hall Rule - the backstop tier</title>
<style>body{font-family:Georgia,serif;max-width:920px;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}table{border-collapse:collapse;width:100%%}td,th{border-bottom:1px solid #ddd;padding:.45rem .5rem;text-align:left;font-size:.95rem}
.on{color:#b00020;font-weight:700}.off{color:#2a7}small{color:#666}a{color:#1a4d8f}</style></head><body>
<h1>The backstop tier</h1>
<p>Three outside rules, each with zero false alarms on the programme's own real-time record 1948&ndash;2026 (collection 249, 20 September 2026),
run beside the Bristow-Hall Rule. Each is watched on its own (the shadow readings below). Together they are also an <b>opener</b>
(collection 256, 20 September 2026): once their union has been ON for thirteen consecutive weeks &mdash; one quarter &mdash; and the Rule stands
closed, the tier opens an episode tagged <b>b</b>. Replayed causally over 1956&ndash;2026 the gated opener changes nothing and false-alarms never;
the plain, ungated opener was refused (it would have moved the 1990 and 2024 calls outside the window). The tier is the floor: if the core ever
misses a recession, one of these turns on three to five months after the peak, and a quarter later the episode opens.</p>
<p>The Rule stands <b>%s</b> since %s. Backstops on: <b>%s</b>. Opener: <b>%s</b>.</p>
<table><tr><th>rule</th><th>reading</th><th>line</th><th>state</th><th>since</th><th>data through</th></tr>%s</table>
<p><small>SOS_NSA: 52-week change of the 26-week average of the unadjusted insured unemployment rate (continued claims &divide; covered employment), line +0.20 pp &mdash; the programme's declared form of O'Trakoun &amp; Scavette (2025).
LMSI30: states (of the 50 + DC) whose 13-week average insured rate is at least 0.20 pp above a year earlier, from the Department of Labor's ETA 539 file, line 30 &mdash; the programme's declared form of the San Francisco Fed's Labor Market Stress Indicator (2025).
CFNAI: the Chicago Fed National Activity Index three-month average below &minus;0.70, the Chicago Fed's own rule.
Michez: Michaillat and Saez's rule, the smaller of the unemployment indicator (Sahm form, first prints) and the vacancy indicator (the twelve-month high of the three-month mean vacancy rate over its value) at or above 0.29 &mdash; a shadow reading on the scoreboard, not in the opener. Built %s UTC. <a href="../">Back to the Rule.</a></small></p>
WEI: the Weekly Economic Index (Lewis, Mertens and Stock; Federal Reserve Bank of Dallas, FRED WEI), the 13-week mean of an index scaled to four-quarter GDP growth, at or below 0 &mdash; a shadow reading for the labour-hoarding type (output falling while claims are still), collection 366; current vintage, real-time history from April 2020 only; not in the opener, not on the scoreboard.
%s
</body></html>""" % (st.get('state', '?'), st.get('since', '?'), ', '.join(state['on']) or 'none', _opener_text(state.get('opener') or {}), rows, state['built_at'], scoreboard_html())
    return html

def scoreboard_html():
    """collection 335 (plan L5): the shadow scoreboard - the outside daters against the rule since 1994, evidence never a lesson"""
    p = os.path.join(OUT, 'scoreboard.json')
    if not os.path.exists(p): return ''
    try: sb = json.load(open(p))
    except Exception: return ''
    names = ['the rule', 'Sahm', 'SOS_NSA', 'LMSI30', 'CFNAI', 'Michez']
    h = '<h2>The scoreboard: the outside daters against the Rule since %s</h2>' % sb.get('since', '1994')
    h += '<p><small>Each dater on the programme\'s own real-time data (collection 249, scored in 275; carried forward by this tier). A call counts for a recession inside 122 days before the end of the peak month to 31 days after the end of the trough month, else it is a false alarm. Evidence, never a lesson: the jury of three daters within a month was tested on this record and refused as a lesson source (collection 335).</small></p>'
    h += '<table><tr><th>recession (peak)</th>' + ''.join('<th>%s</th>' % n for n in names) + '<th>first</th></tr>'
    for r in sb.get('recessions', []):
        cells = ['<td>%s</td>' % (r.get('tool') or '&mdash;')]
        for n in names[1:]:
            d = (r.get('daters') or {}).get(n) or {}
            cells.append('<td>%s%s</td>' % (d.get('call') or '&mdash;', (' (+%d d)' % d['days_after_tool']) if d.get('days_after_tool') is not None else ''))
        h += '<tr><td>%s</td>%s<td><b>%s</b></td></tr>' % (r['peak'], ''.join(cells), r.get('first') or '')
    fa = sb.get('false_alarms', {}); h += '<tr><td><b>false alarms since %s</b></td>' % sb.get('since', '1994')[:4] + ''.join('<td>%s</td>' % (', '.join(fa.get(n, [])) or '0') for n in names) + '<td></td></tr></table>'
    return h

def main():
    state = {'built_at': NOW.isoformat(), 'standing': standing(), 'rules': {}, 'on': [], 'lines': LINES, 'collection': '249_backstop_tier_never_miss_2026-09-20'}
    for k, fn in (('SOS_NSA', rule_sos_nsa), ('LMSI30', rule_lmsi30), ('CFNAI', rule_cfnai), ('Michez', rule_michez), ('WEI', rule_wei)):   # Michez (335) and WEI (366): shadow readings only
        try: state['rules'][k] = fn()
        except Exception as e: state['rules'][k] = {'error': repr(e)[:300]}
    state['on'] = [k for k, r in state['rules'].items() if r.get('on') and not r.get('shadow_only')]
    try: state['opener'] = opener_state()
    except Exception as e: state['opener'] = {'error': repr(e)[:300]}
    json.dump(state, open(os.path.join(OUT, 'backstop_state.json'), 'w'), indent=1, default=str)
    try:
        os.makedirs(os.path.join(SITE, 'detector'), exist_ok=True); os.makedirs(os.path.join(SITE, 'backstop'), exist_ok=True)
        json.dump(state, open(os.path.join(SITE, 'detector', 'backstop.json'), 'w'), default=str)
        open(os.path.join(SITE, 'backstop', 'index.html'), 'w', encoding='utf-8').write(page(state))
    except Exception as e: state['site_error'] = repr(e)[:200]
    line = 'backstop: ' + ' | '.join('%s %s%s' % (k, 'ON' if r.get('on') else ('off' if 'error' not in r else 'ERR'), '' if 'error' in r else ' (%s vs %s, through %s)' % (r['reading'], r['line'], r['data_through'])) for k, r in state['rules'].items())
    line += ' | opener: ' + _opener_text(state.get('opener') or {})
    print(line)
    st = state.get('standing') or {}
    if state['on'] and st.get('state') == 'closed':
        try: subprocess.run(['bash', os.path.join(HERE, 's2', 'alert.sh'), 'BACKSTOP ON WHILE THE RULE STANDS CLOSED', line], timeout=60)
        except Exception: pass
    return 0

if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as e:
        print('backstop: failed %r' % (e,)); sys.exit(0)
