"""THE ACTIVITY OPENER - Core v7-W (v3.63, 21 September 2026, collection 289; Anthony: "Yes port core v7-W to the site
now and make sure to update the data page and the live updating part of the site as well and make sure that the live
updating function is flawless for the site").

A recession has begun on the first day on which ALL FOUR hold:
  1. PRODUCTION  industrial production, AS THEN PUBLISHED (every ALFRED vintage of G.17), stands at least 2.0 log points
                 below its high of the prior twelve months;
  2. MARKET      the S&P 500 stands at least 10 per cent (log) below its high of the prior 250 trading days;
  3. TIGHTENING  the Federal Reserve's policy rate stands at least 0.10 point above its low of the prior 365 days (the
                 FOMC target range's upper limit, FRED DFEDTARU; before 1994 the discount rate);
  4. BREADTH     in the latest month public that day, at least 33 per cent of the states have their insured-rate proxy
                 (continued weeks claimed per week, over payroll employment) at least 0.45 point above its minimum of
                 the prior twelve months. A month is public 21 days after it ends.
A call re-arms after 182 days without a firing. bhs_build.py adds the calls to the rule as leg P, refused inside an
episode the rule already has open and for 183 days after a close (the backstop opener's bars): the opener opens only
what the labour core has not seen and never moves a call the core has made.

WHY THESE LINES. They are the walk's (collection 288, RECORD-core-v7-walk-1948-breadth-2026-09-21): a causal walk from
1948 that learned only from recessions already dated at each cut (the five pre-war ones a 1948 reader knew - 1920, 1923,
1926, 1929, 1937 - then the postwar ones as each was announced) chose this cell at every cut from 1977 and the gate at
0.33 from the first cut that knew a postwar recession (1956). Walked with the labour core (E13t): 13 of 13 recessions
(NBER and Paper 1's 2024), 12 inside three months early to one month late of the end of the peak month (1960 +122 the
residual), zero false alarms on both chronologies. The opener's walked calls: 1948-09-27 (-64 days), 1953-08-31 (+31),
1957-08-26 (-5); and 1970-01-21, 1974-03-15, 1981-11-13 inside recessions the core had already opened.
DISCLOSED ON THE RECORD: the zero-false-alarm result needs the breadth month public within about 21 days (at 35 or 45
days the walk false-alarms in October 1956) - hence the weekly ETA 539 file, not the monthly ETA 5159 report; the
gate's 1956 margin is about three states; the live breadth object is built from the weekly file while the walked
history is the Fieldhouse panel and ETA 5159 (collection 289, T4, says what the difference does to the walk).

INPUTS (cache/activity/ unless named)
  indpro_fall12_by_vintage.csv  one row per ALFRED vintage of INDPRO: log(max of the 12 prior months) - log(latest), in
                                that vintage. New vintages are APPENDED from the FRED API, never rewritten.
  policy_rate_points.csv        the policy rate, 1914 -> (collection 289, code/build_ship.py: walk C's sources); new
                                DFEDTARU days are APPENDED from the FRED API.
  state_breadth_S.csv           the breadth object by month: month, published, S_0.30 .. S_0.70, states, source. The
                                walked history 1947-12 .. 2026-07 (collection 288) is never rewritten; each later month
                                is APPENDED on its publication day (month end + 21 days) once at least 45 states have
                                every week of it in the Department's file.
  state_cw_nsa_monthly.csv      continued weeks claimed by state, not seasonally adjusted: the lab's OWN construction to
                                2026-07; later months APPENDED from https://oui.doleta.gov/unemploy/csv/ar539.csv (c8,
                                the mean of the weeks whose report date falls in the month, times the month's weekdays/5).
  state_payrolls_sa.csv         state payroll employment, FRED {ST}NA (thousands, seasonally adjusted), as last read.
  24_bristow_rule_lab/workspace/lab/speed2/data/sp500_daily_yahoo.csv   the chain's S&P 500 close.
The breadth month: the continued weeks are seasonally adjusted in real time (24/lab/fh/build_rt.py, verbatim: month-of-
year medians of the deviations from a centred 13-month mean over the prior seven years, a state's own factors once it has
five years of history), divided by the month's weeks and by payrolls; the 13 months m-12..m in one construction.
OUTPUTS
  out/activity_opener_calls.csv    pub,dated - the calls of today's lines over the whole history (the frozen rule's leg P)
  out/activity_picture_days.csv    v3.68 (22 September 2026, collections 300 and 301): every day since 1947 on which the activity picture ACT(0.010) holds -
                                   the four conditions with the production line at 0.010 - read by the concurrence branch
  out/activity_opener_state.json   today's reading of the four legs, the lines, the gate, armed, the last firing, the
                                   walked calls, each input's date and channel status (E5), the next release days
Never fails the run: an error leaves the previous outputs in place and says why.
    python3 s2/activity_opener.py            from the collection 105 workspace
    python3 s2/activity_opener.py --check    compute and print; write nothing (no appends, no outputs)
"""
import os, sys, json, time, datetime, tempfile, urllib.request, urllib.parse, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')

HERE = os.path.dirname(os.path.abspath(__file__)); WS = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(WS))
ACT = os.path.join(WS, 'cache', 'activity')
HIST = os.path.join(ACT, 'indpro_fall12_by_vintage.csv')
POLICY = os.path.join(ACT, 'policy_rate_points.csv')
BREADTH = os.path.join(ACT, 'state_breadth_S.csv')
CLAIMS = os.path.join(ACT, 'state_cw_nsa_monthly.csv')
PAYROLLS = os.path.join(ACT, 'state_payrolls_sa.csv')
AR539_HDR = os.path.join(ACT, 'ar539_last_read.json')
SPX = os.path.join(ROOT, '24_bristow_rule_lab', 'workspace', 'lab', 'speed2', 'data', 'sp500_daily_yahoo.csv')
ENV = os.path.join(ROOT, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
OUT_CALLS = os.path.join(WS, 'out', 'activity_opener_calls.csv'); OUT_STATE = os.path.join(WS, 'out', 'activity_opener_state.json')
OUT_ACT = os.path.join(WS, 'out', 'activity_picture_days.csv')   # v3.68 (22 September 2026, collections 300 and 301)
ACT_LINE = 0.010      # the concurrence branch's production line (walked from 1956: 0.010 at every cut; collection 300 A2)
AR539_URL = 'https://oui.doleta.gov/unemploy/csv/ar539.csv'
I_LINE, M_LINE, T_LINE = 0.02, 0.10, 0.10          # the walked cell (collection 288)
G_UNIT, G_SHARE = 0.45, 0.33                      # the walked breadth gate
REARM, BAR_DAYS = 182, 183
PUB_LAG, MIN_COMPLETE, MIN_STATES = 21, 45, 25
UNITS = (0.30, 0.35, 0.45, 0.55, 0.70)
G17 = 13          # FRED release id of G.17 Industrial Production and Capacity Utilization
STATES = ('AK AL AR AZ CA CO CT DC DE FL GA HI IA ID IL IN KS KY LA MA MD ME MI MN MO MS MT NC ND NE NH NJ NM NV NY '
          'OH OK OR PA RI SC SD TN TX UT VA VT WA WI WV WY').split()
# FOMC decision days (the second day of each scheduled meeting; the statement at 2:00 PM ET), from the Federal Reserve's
# calendar (https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm, read 21 September 2026). The Board publishes
# the next year's calendar each summer: extend this list then. Past its end the next day is estimated (flagged).
FOMC = ['2026-01-28', '2026-03-18', '2026-04-29', '2026-06-17', '2026-07-29', '2026-09-16', '2026-10-28', '2026-12-09',
        '2027-01-27', '2027-03-17', '2027-04-28', '2027-06-09', '2027-07-28', '2027-09-15', '2027-10-27', '2027-12-08']
# E5: how long each channel may go without a new reading before it is stale (twice that: dark), and what stands in
LIMITS = {'production': 45, 'market': 5, 'policy': 10, 'breadth': 56}
SUBST = {'production': 'the FRED current file of INDPRO (flagged: revised values), then the G.17 release text',
         'market': 'the official FRED SP500 close, then the Yahoo feed',
         'policy': 'the FOMC statement on federalreserve.gov (the rate carried from the last reading until then)',
         'breadth': 'the ETA 5159 monthly report (slower: the walk needs the month within about 21 days), then the last month read'}


def say(*a): print('activity opener:', *a, flush=True)


def fred_key():
    k = os.environ.get('FRED_API_KEY', '')
    if not k and os.path.exists(ENV):
        for line in open(ENV):
            if line.startswith('FRED_API_KEY='): k = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
    return k


def fred(path, **q):
    q.update(api_key=fred_key(), file_type='json')
    url = 'https://api.stlouisfed.org/fred/' + path + '?' + urllib.parse.urlencode(q)
    err = None
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                return json.load(r)
        except Exception as e:
            err = e; time.sleep(3 * (i + 1))
    raise err


def atomic_csv(df, path, **kw):
    tmp = path + '.tmp'; df.to_csv(tmp, **kw); os.replace(tmp, path)


# ---------------------------------------------------------------- 1. production (G.17 as published), as in v3.62
def f12(values):
    v = np.asarray(values, dtype=float)
    if len(v) < 13 or not v[-1] > 0: return np.nan
    return float(np.log(np.max(v[-13:-1])) - np.log(v[-1]))


def update_history(h, write=True):
    """Append every INDPRO vintage FRED has published after the last one in hand. Returns (history, added, note)."""
    if not fred_key(): return h, 0, 'no FRED key; the production history in hand is used'
    last = pd.Timestamp(h['vintage_date'].iloc[-1])
    # FRED answers HTTP 500, not an empty list, when the window holds no vintage (21 September 2026): ask for the 400
    # days to today and keep only the vintages newer than the history in hand
    start = (last - pd.Timedelta(days=400)).date().isoformat(); end = datetime.date.today().isoformat()
    try:
        vd = fred('series/vintagedates', series_id='INDPRO', realtime_start=start, realtime_end=end).get('vintage_dates', [])
    except Exception as e:
        return h, 0, 'FRED vintage dates not read (%s); the production history in hand is used' % type(e).__name__
    rows = []
    for d in sorted(x for x in vd if x > h['vintage_date'].iloc[-1]):
        try:
            obs = fred('series/observations', series_id='INDPRO', realtime_start=d, realtime_end=d).get('observations', [])
        except Exception as e:
            return h, 0, 'the INDPRO vintage of %s was not read (%s); the production history in hand is used' % (d, type(e).__name__)
        vals = [(o['date'], float(o['value'])) for o in obs if o.get('value') not in (None, '', '.')]
        if not vals: continue
        vals.sort(); f = f12([v for _, v in vals])
        if np.isfinite(f): rows.append((d, vals[-1][0][:7], f, vals[-1][1]))
    if rows:
        h = pd.concat([h, pd.DataFrame(rows, columns=['vintage_date', 'last_obs', 'fall12', 'last_value'])], ignore_index=True)
        if write: atomic_csv(h, HIST, index=False, float_format='%.10f')
    return h, len(rows), ('appended %d INDPRO vintage(s)' % len(rows)) if rows else 'no new INDPRO vintage since %s' % last.date()


def g17_dates(today):
    """G.17's scheduled release days from today on (FRED's release calendar, release 13); [] when FRED cannot be read."""
    if not fred_key(): return []
    try:
        r = fred('release/dates', release_id=G17, realtime_start=today.date().isoformat(), realtime_end='9999-12-31',
                 include_release_dates_with_no_data='true', sort_order='asc', limit=40)
        return sorted({x['date'] for x in r.get('release_dates', []) if x['date'] >= today.date().isoformat()})
    except Exception:
        return []


# ---------------------------------------------------------------- 2. the market, T2 verbatim (collection 276)
def drawdown(close, window=250):
    close = close.sort_index().dropna()
    dd = np.log(close.rolling(window, min_periods=100).max()) - np.log(close)
    days = pd.date_range(dd.index[0], max(dd.index[-1], pd.Timestamp.today().normalize()), freq='D')
    return dd.reindex(days, method='ffill')


def fire(fall12, dd, I=I_LINE, M=M_LINE):
    idx = fall12.index.union(dd.index)
    a = fall12.reindex(idx, method='ffill'); b = dd.reindex(idx, method='ffill')
    return ((a >= I) & (b >= M)).fillna(False)


def calls(on, rearm=REARM, start='1948-01-01'):
    on = on.fillna(False); idx = on[on].index; out = []; last = None
    for t in idx:
        if last is None or (t - last).days >= rearm:
            out.append(t)
        last = t
    return [t for t in out if t >= pd.Timestamp(start)]


# ---------------------------------------------------------------- 3. tightening (walk C's policy_rate(), 279)
def update_policy(P, write=True):
    """Append every DFEDTARU day FRED has published after the last day in hand. Returns (points, added, note)."""
    if not fred_key(): return P, 0, 'no FRED key; the policy rate in hand is used'
    last = str(P['date'].iloc[-1])
    try:
        obs = fred('series/observations', series_id='DFEDTARU',
                   observation_start=(pd.Timestamp(last) - pd.Timedelta(days=30)).date().isoformat()).get('observations', [])
    except Exception as e:
        return P, 0, 'FRED DFEDTARU not read (%s); the policy rate in hand is used' % type(e).__name__
    rows = [(o['date'], float(o['value']), 'FRED DFEDTARU') for o in obs if o.get('value') not in (None, '', '.') and o['date'] > last]
    if rows:
        P = pd.concat([P, pd.DataFrame(rows, columns=['date', 'rate', 'source'])], ignore_index=True)
        if write: atomic_csv(P, POLICY, index=False)
    return P, len(rows), ('appended %d DFEDTARU day(s) through %s' % (len(rows), rows[-1][0])) if rows else 'no new DFEDTARU day since %s' % last


def tightening(P, end):
    s = pd.Series(P['rate'].astype(float).values, index=pd.to_datetime(P['date'])).sort_index()
    s = s[~s.index.duplicated(keep='last')]
    full = pd.date_range('1914-11-01', max(pd.Timestamp(end), s.index[-1]), freq='D')
    r = s.reindex(full.union(s.index)).ffill().reindex(full)
    low = r.rolling(366, min_periods=1).min()      # the prior 365 days and today
    return r, low, (r - low) >= T_LINE - 1e-9


def next_fomc(today):
    d = next((x for x in FOMC if x >= today.date().isoformat()), None)
    if d: return d, False
    # past the list: six weeks on from the last listed day, flagged; the list is extended each summer
    t = pd.Timestamp(FOMC[-1])
    while t.date() < today.date(): t += pd.Timedelta(days=42)
    return t.date().isoformat(), True


# ---------------------------------------------------------------- 4. breadth (collection 288's object, fed live)
# month_factors and sa_realtime are 24_bristow_rule_lab/workspace/lab/fh/build_rt.py's, verbatim (collection 289 T2:
# they reproduce the lab's OWN_state_claims_sa_rt_log.csv to 1e-14)
WIN = 7; OWN_YEARS = 5
def month_factors(X):
    R=X-X.rolling(13,center=True,min_periods=7).mean()
    own={}; pooled={}
    for mth in range(1,13):
        sel=R[R.index.month==mth]
        if len(sel)==0: continue
        v=sel.values[~np.isnan(sel.values)]
        if len(v): pooled[mth]=float(np.median(v))
        for c in X.columns:
            q=sel[c].dropna()
            if len(q)>=3: own[(c,mth)]=float(np.median(q))
    if pooled:
        mu=np.median(list(pooled.values())); pooled={k:v-mu for k,v in pooled.items()}
    if own:
        mo_=np.median(list(own.values())); own={k:v-mo_ for k,v in own.items()}
    return own,pooled
def sa_realtime(P,own_years=OWN_YEARS,win=WIN):
    X=np.log(P.replace(0,np.nan)).interpolate().bfill()
    out=pd.DataFrame(index=X.index,columns=X.columns,dtype=float)
    for y in sorted(set(X.index.year)):
        hist=X[(X.index.year<y)&(X.index.year>=y-win)]
        m=(X.index.year==y)
        if len(hist)<24: out.loc[m]=X.loc[m]; continue
        own,pooled=month_factors(hist)
        for c in X.columns:
            use_own=len(X[X.index.year<y][c].dropna())>=own_years*12
            adj=np.array([(own.get((c,t.month),pooled.get(t.month,0.0)) if use_own
                           else pooled.get(t.month,0.0)) for t in X.index[m]])
            out.loc[m,c]=X.loc[m,c].values-adj
    return out.dropna(how='all')


def mstart(x): return pd.Timestamp(str(x)[:7] + '-01')
def month_end(m): return mstart(m) + pd.offsets.MonthEnd(0)
def pub_day(m): return month_end(m) + pd.Timedelta(days=PUB_LAG)


def read_claims():
    C = pd.read_csv(CLAIMS, index_col=0, dtype={'month': str})
    C.index = pd.to_datetime([str(i)[:7] + '-01' for i in C.index]); return C.astype(float)


def read_ar539(note):
    """The Department's weekly file (13 MB): st, rptdate, c8. Downloaded to a temporary file, never kept in the repository.
    Returns (frame or None, headers)."""
    tmp = os.path.join(tempfile.gettempdir(), 'bhr_ar539.csv'); hd = {}
    req = urllib.request.Request(AR539_URL, headers={'User-Agent': 'bristow-hall-rule/3.63 (activity opener; oui.doleta.gov ETA 539)'})
    err = None
    for k in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r, open(tmp, 'wb') as f:
                hd = {'etag': r.headers.get('ETag'), 'last-modified': r.headers.get('Last-Modified'), 'content-length': r.headers.get('Content-Length')}
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b)
            if os.path.getsize(tmp) > 1_000_000: break
            err = 'short file'
        except Exception as e:
            err = '%s: %s' % (type(e).__name__, str(e)[:80]); time.sleep(10 * (k + 1))
    else:
        note.append('the ETA 539 file was not read (%s)' % err); return None, hd
    w = pd.read_csv(tmp, usecols=['st', 'rptdate', 'c8'], low_memory=False)
    w['rptdate'] = pd.to_datetime(w['rptdate'], errors='coerce'); w['c8'] = pd.to_numeric(w['c8'], errors='coerce')
    w = w.dropna(subset=['rptdate']); w = w[w['st'].isin(STATES)]
    try: os.remove(tmp)
    except Exception: pass
    return w, hd


def own_month(w, m):
    """The OWN construction for month m: per state, the mean of c8 over the weeks whose report date falls in m, times the
    month's weekdays / 5. A state is complete when it has every report week (Saturday) of the month."""
    m = mstart(m); e = month_end(m)
    sats = [d for d in pd.date_range(m, e, freq='D') if d.weekday() == 5]
    x = w[(w['rptdate'] >= m) & (w['rptdate'] <= e)].dropna(subset=['c8'])
    g = x.groupby('st')['c8'].agg(['mean', 'count'])
    wd = np.busday_count(m.date(), (m + pd.offsets.MonthBegin(1)).date())
    val = (g['mean'] * wd / 5.0).reindex(STATES)
    complete = [s for s in STATES if s in g.index and int(g.loc[s, 'count']) == len(sats)]
    return val, complete


def read_payrolls(months_needed, note, write=True):
    """FRED {ST}NA (thousands, SA) for the 51 states, re-read when the cached file lacks the months asked for.
    Returns a frame indexed by month start (NaN where a state's month is not yet published)."""
    P = None
    if os.path.exists(PAYROLLS):
        P = pd.read_csv(PAYROLLS, index_col=0); P.index = pd.to_datetime([str(i)[:7] + '-01' for i in P.index])
    have = (P is not None and len(P) and P.index.max() >= max(months_needed) and P.reindex(months_needed).notna().all().all())
    if have or not fred_key(): return P
    cols = {}; bad = []
    for st in STATES:
        try:
            obs = fred('series/observations', series_id=st + 'NA', observation_start='2015-01-01').get('observations', [])
            cols[st] = pd.Series({pd.Timestamp(o['date']): float(o['value']) for o in obs if o.get('value') not in (None, '', '.')})
        except Exception:
            bad.append(st)
    if cols:
        N = pd.DataFrame(cols)
        if P is not None:
            N = N.combine_first(P)            # a state FRED did not answer keeps the months in hand
        P = N.sort_index()
        if write:
            Q = P.copy(); Q.index = Q.index.strftime('%Y-%m'); Q.index.name = 'month'; atomic_csv(Q, PAYROLLS)
        note.append('state payrolls re-read from FRED (%d states%s), through %s' % (len(cols), (', not answered: ' + ' '.join(bad)) if bad else '', P.index.max().strftime('%Y-%m')))
    else:
        note.append('state payrolls not re-read (FRED did not answer); the file in hand is used')
    return P


def breadth_month(C, Pay, m):
    """S(m, u) for every unit from ONE construction over m-12 .. m: the OWN panel seasonally adjusted in real time
    (sa_realtime over the whole panel, each year adjusted with the seven years before it), per week of the month, over
    payrolls (a state's latest payroll carried into months not yet published). Returns (dict unit -> share, states)."""
    m = mstart(m)
    SA = sa_realtime(C[C.index <= m])
    months = pd.date_range(m - pd.DateOffset(months=12), m, freq='MS')
    pay = Pay.reindex(Pay.index.union(months)).sort_index().ffill().reindex(months)
    cols = [s for s in STATES if s in SA.columns and s in pay.columns]
    weeks = pd.Series(months.days_in_month / 7.0, index=months)
    U = 100.0 * np.exp(SA.reindex(months)[cols]).div(weeks, axis=0) / (pay[cols] * 1000.0)
    raw = C.reindex([m])[cols].iloc[0]
    prior = U.iloc[:-1]; last = U.iloc[-1].where(raw.notna())    # a state with no week of m in the file is not counted
    valid = prior.notna().sum() == 12
    valid &= last.notna()
    gap = (last - prior.min())[valid]
    n = int(valid.sum())
    if n < MIN_STATES: return None, n
    return {u: float((gap >= u - 1e-9).sum()) / n for u in UNITS}, n


def update_breadth(today, S, note, write=True):
    """Publish every month whose day has come (month end + 21 days) and whose weeks are in the Department's file for at
    least 45 states. Appends to state_cw_nsa_monthly.csv and state_breadth_S.csv; never rewrites a month in hand."""
    last = mstart(S['month'].iloc[-1]); nxt = last + pd.DateOffset(months=1)
    if today < pub_day(nxt):
        note.append('breadth: %s is public on %s' % (nxt.strftime('%Y-%m'), pub_day(nxt).date())); return S, 0
    C = read_claims()
    need = [m for m in pd.date_range(C.index.max() + pd.DateOffset(months=1), nxt, freq='MS') if pub_day(m) <= today]
    if need:
        # the Department's file changes weekly: read it once per new Last-Modified while a month waits (the headers of the
        # last read are kept, so the 13 MB file is not downloaded at every run while the month is incomplete)
        prev = {}
        try: prev = json.load(open(AR539_HDR))
        except Exception: pass
        try:
            h = urllib.request.urlopen(urllib.request.Request(AR539_URL, method='HEAD', headers={'User-Agent': 'bristow-hall-rule/3.63'}), timeout=30).headers
            head = {'etag': h.get('ETag'), 'last-modified': h.get('Last-Modified'), 'content-length': h.get('Content-Length')}
        except Exception:
            head = {}
        if head and prev.get('waiting') and all(prev.get(k) == head.get(k) for k in ('etag', 'last-modified', 'content-length')):
            note.append('breadth: %s waits for the Department (its file unchanged since %s; %s of 45 states complete)' % (
                need[0].strftime('%Y-%m'), head.get('last-modified'), prev.get('complete')))
            return S, 0
        w, hd = read_ar539(note)
        if w is None: return S, 0
        added = []
        for m in need:
            val, complete = own_month(w, m)
            if len(complete) < MIN_COMPLETE:
                if write: json.dump(dict(hd or head, waiting=m.strftime('%Y-%m'), complete=len(complete), read=str(today.date())), open(AR539_HDR, 'w'))
                note.append('breadth: %s incomplete in the Department\'s file (%d of the 45 states needed have every week)' % (m.strftime('%Y-%m'), len(complete)))
                break
            C.loc[m] = val.reindex(C.columns).values; added.append(m)
        if added:
            C = C.sort_index()
            if write:
                Q = C.copy(); Q.index = Q.index.strftime('%Y-%m'); Q.index.name = 'month'; atomic_csv(Q, CLAIMS, float_format='%.6f')
                json.dump(dict(hd or head, waiting=None, read=str(today.date())), open(AR539_HDR, 'w'))
            note.append('breadth: continued weeks appended for %s' % ', '.join(m.strftime('%Y-%m') for m in added))
    n_added = 0
    m = nxt
    while pub_day(m) <= today and m <= C.index.max():
        Pay = read_payrolls(list(pd.date_range(m - pd.DateOffset(months=12), m, freq='MS')), note, write)
        if Pay is None: note.append('breadth: no state payrolls in hand; %s not published' % m.strftime('%Y-%m')); break
        shares, n = breadth_month(C, Pay, m)
        if shares is None: note.append('breadth: %s has %d states with 13 months (25 needed)' % (m.strftime('%Y-%m'), n)); break
        row = dict(month=m.date().isoformat(), published=pub_day(m).date().isoformat(), states=n,
                   source='live: ETA 539 continued weeks (OWN construction), real-time seasonal adjustment, FRED state payrolls')
        row.update({'S_%.2f' % u: v for u, v in shares.items()})
        S = pd.concat([S, pd.DataFrame([row])], ignore_index=True); n_added += 1
        note.append('breadth: %s published, %.0f%% of %d states 0.45 over their 12-month low' % (m.strftime('%Y-%m'), 100 * shares[G_UNIT], n))
        m = m + pd.DateOffset(months=1)
    if n_added and write: atomic_csv(S, BREADTH, index=False)
    return S, n_added


def gate_daily(S, days):
    s = pd.Series(S['S_%.2f' % G_UNIT].astype(float).values, index=pd.to_datetime(S['published'])).sort_index()
    s = s[~s.index.duplicated(keep='last')]
    return s.reindex(days.union(s.index)).ffill().reindex(days)      # NaN before 1948-01-21: the gate is open


def status(name, last, today):
    lim = LIMITS[name]; age = (today - pd.Timestamp(last)).days if last is not None else None
    st = 'dark' if age is None or age > 2 * lim else ('stale' if age > lim else 'current')
    return dict(status=st, age_days=age, limit_days=lim, substitute=None if st == 'current' else SUBST[name])


# ---------------------------------------------------------------- 5. the rule, today's reading, the outputs
WALKED_CALLS = ['1948-09-27', '1953-08-31', '1957-08-26', '1970-01-21', '1974-03-15', '1981-11-13']   # collection 288, walk D early/B


def main(check=False, today=None):
    today = pd.Timestamp(today or datetime.datetime.now().date())
    write = not check
    prev = {}
    try: prev = json.load(open(OUT_STATE))
    except Exception: pass
    notes = []
    h = pd.read_csv(HIST, dtype={'vintage_date': str, 'last_obs': str})
    h, added, n1 = update_history(h, write); say(n1)
    P = pd.read_csv(POLICY, dtype={'date': str})
    P, padd, n2 = update_policy(P, write); say(n2)
    S = pd.read_csv(BREADTH, dtype={'month': str, 'published': str})
    try:
        S, sadd = update_breadth(today, S, notes, write)
    except Exception as e:
        sadd = 0; notes.append('breadth update FAILED (%s: %s); the months in hand are used' % (type(e).__name__, e))
    for n in notes: say(n)
    # the four legs, daily
    st_ = pd.Series(h['fall12'].values, index=pd.to_datetime(h['vintage_date'])).sort_index()
    st_ = st_[~st_.index.duplicated(keep='last')]
    close = pd.read_csv(SPX, index_col=0, parse_dates=True).iloc[:, 0].dropna()
    end = max(today, st_.index[-1], close.index[-1])
    days = pd.date_range('1947-01-01', end, freq='D')
    fall12 = st_.reindex(days.union(st_.index)).ffill().reindex(days)
    dd = drawdown(close)
    rate, low, tight = tightening(P, end)
    gate = gate_daily(S, days)
    on = fire(fall12, dd).reindex(days).fillna(False) & tight.reindex(days).fillna(False)
    on = on & ((gate >= G_SHARE - 1e-9) | gate.isna())
    cl = calls(on)
    # v3.68 (22 September 2026, collections 300 and 301): the activity picture of the concurrence branch - the same four conditions, production at 0.010
    act = fire(fall12, dd, I=ACT_LINE).reindex(days).fillna(False) & tight.reindex(days).fillna(False) & ((gate >= G_SHARE - 1e-9) | gate.isna())
    # today's reading
    at = lambda s: s.reindex([today], method='ffill').iloc[0]
    f = float(at(fall12)); d = float(at(dd)); r_ = float(at(rate)); lo_ = float(at(low)); tg = bool(at(tight))
    Sl = S.iloc[-1]; share = float(Sl['S_%.2f' % G_UNIT])
    pub_ok = pd.Timestamp(Sl['published']) <= today
    if not pub_ok:   # never read a month before its day (the file is only appended on the day, so this does not happen)
        Sl = S[pd.to_datetime(S['published']) <= today].iloc[-1]; share = float(Sl['S_%.2f' % G_UNIT])
    gate_open = share >= G_SHARE - 1e-9
    last_fire = on[on].index[-1] if on.any() else None
    armed = last_fire is None or (today - last_fire).days >= REARM
    prod_last = st_.index[-1]; mkt_last = close.index[-1]; pol_last = pd.Timestamp(P['date'].iloc[-1])
    br_month = mstart(Sl['month']); br_end = month_end(br_month)
    nf, nf_est = next_fomc(today)
    nb = pub_day(br_month + pd.DateOffset(months=1))
    nb = max(nb, today)          # a month past its day that waits for the Department: the next run is its next chance
    four = bool(f >= I_LINE and d >= M_LINE and tg and gate_open)
    state = dict(
        rule=('industrial production as published >= 2.0 log points below its prior-12-month high AND the S&P 500 >= 10 per cent '
              '(log) below its 250-trading-day high AND the policy rate >= 0.10 point above its low of the prior 365 days AND, in the '
              'latest month public (21 days after it ends), >= 33 per cent of states with the insured-rate proxy 0.45 point above its '
              'prior-12-month minimum (Core v7-W: the cell and gate the causal walk from 1948 chose, collection 288)'),
        lines=dict(production=I_LINE, market=M_LINE, tightening=T_LINE, breadth_unit=G_UNIT, breadth_share=G_SHARE,
                   rearm_days=REARM, bar_days_after_close=BAR_DAYS, breadth_public_days_after_month=PUB_LAG),
        asof=str(today.date()),
        reading=dict(production_fall12=round(f, 4), production_distance=round(I_LINE - f, 4), production_vintage=str(prod_last.date()),
                     production_level=round(float(h['last_value'].iloc[-1]), 4), production_last_month=str(h['last_obs'].iloc[-1]),
                     market_drawdown=round(d, 4), market_distance=round(M_LINE - d, 4), market_close=round(float(close.iloc[-1]), 2),
                     market_close_date=str(mkt_last.date()),
                     policy_rate=round(r_, 4), policy_low_365=round(lo_, 4), policy_rise=round(r_ - lo_, 4), policy_date=str(pol_last.date()),
                     tightening=tg,
                     breadth_month=br_month.strftime('%Y-%m'), breadth_published=str(Sl['published'])[:10], breadth_share=round(share, 4),
                     breadth_states=int(Sl['states']), breadth_source=str(Sl.get('source', '')), gate_open=bool(gate_open),
                     all_four_hold=four, both_hold=bool(f >= I_LINE and d >= M_LINE), armed=bool(armed),
                     last_fire=(str(last_fire.date()) if last_fire is not None else None)),
        activity_picture=dict(line=ACT_LINE, holds_today=bool(act.reindex([today], method='ffill').iloc[0]), days_since_1947=int(act.sum()),
                              last_day=(str(act[act].index[-1].date()) if act.any() else None),
                              note='the four conditions with production 1.0 log point below its twelve-month high: the concurrence branch confirms a standing labour proposal on such a day (v3.68)'),
        calls=[str(t.date()) for t in cl],
        calls_note='the calls of today\'s lines over the whole history (the frozen rule\'s opener branch); the walked record is walked_calls',
        walked_calls=WALKED_CALLS,
        vintages=int(len(h)), vintages_added_this_run=int(added), policy_days_added_this_run=int(padd), breadth_months_added_this_run=int(sadd),
        g17_dates=(lambda g: g if g else [x for x in (prev.get('g17_dates') or []) if x >= str(today.date())])(g17_dates(today)),
        next_fomc=nf, next_fomc_estimated=nf_est, next_breadth_publication=str(nb.date()),
        channels=dict(production=status('production', prod_last, today), market=status('market', mkt_last, today),
                      policy=status('policy', pol_last, today), breadth=status('breadth', br_end, today)),
        notes=notes,
        collection='289_core_v7w_live_port_2026-09-21 (rule: 288 RECORD-core-v7-walk-1948-breadth; opener walk: 279 walk C, 288 walk D)')
    state['next_production_release'] = next((x for x in state['g17_dates'] if x >= str(today.date())), None)
    r = state['reading']
    say('production %.2f log points below its 12-month high (line 2.0; vintage %s); S&P 500 %.1f%% below its 250-day high (line 10; '
        'close %s); policy rate %.2f, %.2f over its 365-day low (line 0.10; %s); breadth %s: %.0f%% of %d states (gate 33%%) - %s; %s; '
        'last firing %s; %d calls since 1948 at these lines' % (
        100 * r['production_fall12'], r['production_vintage'], 100 * r['market_drawdown'], r['market_close_date'], r['policy_rate'],
        r['policy_rise'], r['policy_date'], r['breadth_month'], 100 * r['breadth_share'], r['breadth_states'],
        'ALL FOUR HOLD' if four else 'not all four', 'armed' if r['armed'] else 'not re-armed', r['last_fire'], len(cl)))
    if check: return state, cl
    os.makedirs(os.path.dirname(OUT_CALLS), exist_ok=True)
    atomic_csv(pd.DataFrame({'pub': [str(t.date()) for t in cl], 'dated': [t.strftime('%Y-%m') for t in cl]}), OUT_CALLS, index=False)
    atomic_csv(pd.DataFrame({'day': [str(t.date()) for t in act[act].index]}), OUT_ACT, index=False)   # v3.68 (22 September 2026, collections 300 and 301)
    tmp = OUT_STATE + '.tmp'; json.dump(state, open(tmp, 'w'), indent=1); os.replace(tmp, OUT_STATE)
    return state, cl


if __name__ == '__main__':
    try:
        main(check='--check' in sys.argv)
    except Exception as e:
        say('FAILED (%s: %s); the previous outputs stand' % (type(e).__name__, e))
        sys.exit(0)
