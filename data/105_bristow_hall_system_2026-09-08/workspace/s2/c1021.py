"""s2/c1021.py - THE C1021 STARTER, LIVE (collection 1022, 8 November 2026; Anthony 05:45 PT: C1021 replaces v3.76's starter).
C1021 = C1016P + FS + JL (RECORD-1019/1020/1021; 12 of 12 NBER recessions since 1948 and Paper 1's 2024, no false alarm 1948-2026,
noise 0/99, 78 unseen worlds 0 FA). No number in it is fitted: every line is a natural unit (a year ago, a 12-month high or low,
one month, 15 per cent, 1.5 points). This file computes, from the bundle's own data as the update refreshes it, every pillar as of
every day since 2012 and the door firings since the record's cut, writes the call pool bhs_build.py opens episodes from, and the
daily reading the site charts. The record's calls before the cut are frozen (data/c1021_record.json, from the 1021 harness).
  ROUTE (all seven on the same day): I4 insured unemployment NSA, 4-week sum above the same weeks a year earlier (first prints, known
  on the release day); HW help-wanted: JOLTS openings' year-on-year growth below initial claims' (NSA 4-week, first prints); SY the
  S&P 500 below its close 365 days earlier on any of the last 25 days (a market fall held a month); IP industrial production (the newest G.17 print) below its high
  of the prior 12 months; BAA Moody's Baa yield above its low of the prior 12 months (known the 7th of the next month); HH the
  household survey: the two-month average unemployment rate (first prints, within the newest vintage) at least 0.3 above its level
  three months earlier, or payrolls P and at least 0.2; P payrolls (newest print) below their 12-month high and below last month.
  COUNT DOOR: the unemployed count's first print at or above every one of the prior 12 months' first prints (9 or more present),
  and the 4-week mean of initial or insured claims (seasonally adjusted, as first printed) at a 365-day high, and SY.
  FS DOOR: the effective federal funds rate's monthly average up 1.5 points or more on the previous month (known the day after
  month end). JL DOOR: unemployed job losers (first print) up 15 log points or more on a year earlier while the 10-year minus 1-year
  Treasury spread was negative in any of the prior 12 months; in force 75 days; re-armed when the yoy prints at or below zero.
  Between route or door calls the recovery convention: a new call needs payrolls (newest print) above their high of the 12 months
  to the previous call's month. Episodes open on the first call outside an open episode and more than 183 days after a close
  (bhs_build.py: the union); they close by v3.76's closers, unchanged; the damage grade is v3.76's, unchanged.
Run from the live workspace before bhs_build.py: python3 s2/c1021.py  (writes out/c1021_calls.csv, out/c1021_state.json,
cache/c1021/reading_daily.csv). BHS_C1021_IDENTITY=<ref npz> compares every pillar with the harness's arrays and reports."""
import os, sys, io, json, glob, math, datetime as dt, urllib.request
import numpy as np, pandas as pd
ROOT = os.environ.get('BHS_ROOT') or next(r for r in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')) if os.path.isdir(r))
W = os.getcwd(); OUT = os.path.join(W, 'out'); CACHE = os.path.join(W, 'cache', 'c1021'); os.makedirs(OUT, exist_ok=True); os.makedirs(CACHE, exist_ok=True)
TODAY = pd.Timestamp(os.environ.get('BHS_TODAY') or dt.date.today())
D0 = pd.Timestamp('2012-01-01'); N = int((TODAY - D0).days) + 1
def di(t): return int((pd.Timestamp(t) - D0).days)
def day(i): return (D0 + pd.Timedelta(days=int(i)))
AL = os.environ.get('BHS_C1021_ALFRED') or os.path.join(ROOT, 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages')
LINE_UR, LINE_UR2, JL_LINE, FS_LINE, SY_HOLD, CHI_WIN = 0.3, 0.2, 15.0, 1.5, 25, 365
REC = json.load(open(os.path.join(W, 's2', 'c1021_record.json'))) if os.path.exists(os.path.join(W, 's2', 'c1021_record.json')) else json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c1021_record.json')))
RECORD_CUT = pd.Timestamp(REC['record_cut'])
LOG = []
def say(*a):
    s = ' '.join(str(x) for x in a); LOG.append(s); print('c1021:', s, flush=True)

# ---------------------------------------------------------------- helpers: daily painting, ALFRED vintages, FRED monthly
def paint(pairs, default=False):
    """pairs of (day index, value): each value holds from its day to the day before the next pair's day"""
    out = np.full(N, default, dtype=bool if isinstance(default, bool) else float); pairs = sorted(pairs, key=lambda x: x[0])
    for (d, v), (d1, _) in zip(pairs, pairs[1:] + [(N, None)]):
        if d < N and d1 > 0: out[max(d, 0):min(N, d1)] = v
    return out
def alfred(series):
    """{vintage day: Series(month -> value)} from the bundle's ALFRED all-vintages table (every vintage in the file)"""
    f = os.path.join(AL, series + '_all_vintages.csv')
    if not os.path.exists(f) and os.path.exists(f + '.gz'): f = f + '.gz'
    if not os.path.exists(f): raise SystemExit('c1021: the ALFRED vintage table %s is missing (%s); a pillar cannot be read dark - the run stops' % (series, f))
    X = pd.read_csv(f); X.index = pd.to_datetime(X.iloc[:, 0]); X = X.drop(columns=[X.columns[0]])
    out = {}
    for c in X.columns:
        try: vd = pd.Timestamp(c.split('_')[-1])
        except Exception: continue
        s = pd.to_numeric(X[c], errors='coerce').dropna().astype(float)
        if len(s): out[vd] = s
    return dict(sorted(out.items()))
def within(V, test, minlen=14):
    """the newest observation of each vintage tested against that vintage's prior 12 months; painted from the vintage day"""
    pairs = []
    for vd, s in V.items():
        if len(s) < minlen: continue
        last = s.index.max(); prior = s[(s.index < last) & (s.index >= last - pd.DateOffset(months=12))]
        if len(prior) >= 9: pairs.append((di(vd), bool(test(s, last, prior))))
    return paint(pairs)
def first_prints(V):
    """month -> (first vintage day that carries it, value): the series as first printed"""
    fp = {}
    for vd, s in V.items():
        for m, v in s.items():
            if m not in fp: fp[m] = (vd, float(v))
    return dict(sorted(fp.items()))
def fred_monthly(series):
    """FRED's current monthly series (fredgraph csv, no key), cached in cache/c1021/<series>.csv; the cache stands if FRED is unreachable"""
    f = os.path.join(CACHE, series + '.csv')
    try:
        txt = urllib.request.urlopen('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + series, timeout=60).read().decode()
        df = pd.read_csv(io.StringIO(txt)); df.columns = ['date', 'v']; df['v'] = pd.to_numeric(df.v, errors='coerce'); df = df.dropna()
        if len(df) > 100: df.to_csv(f, index=False)
    except Exception as e:
        say('FRED', series, 'not reached; cache stands:', repr(e)[:80])
    if not os.path.exists(f): raise SystemExit('c1021: FRED %s is unreachable and no cache stands (%s) - the run stops' % (series, f))
    df = pd.read_csv(f, parse_dates=['date']); return df.set_index('date').v.astype(float)

# ---------------------------------------------------------------- the weekly claims as first printed (the site's own chain, collection 45 + E66)
def load_claims():
    f = os.path.join(W, 'cache', 'national_first_prints_1985_live.csv')
    if not os.path.exists(f): f = os.path.join(ROOT, '45_dol_first_prints_2026-09', 'national_first_prints.csv')
    d = pd.read_csv(f, dtype=str).fillna('')
    d['rel'] = pd.to_datetime(d['release_date'], errors='coerce')
    for c in ('icsa', 'iusa', 'icnsa', 'iunsa'): d[c] = pd.to_numeric(d[c], errors='coerce')
    d['icw'] = pd.to_datetime(d['ic_week_ended'], errors='coerce'); d['iuw'] = pd.to_datetime(d['iu_week_ended'], errors='coerce')
    # NSA first prints appended by bhs_update.py from ALFRED's initial releases of ICNSA/CCNSA (cache/c1021/claims_nsa_first_prints.csv)
    fn = os.path.join(CACHE, 'claims_nsa_first_prints.csv'); fills = 0
    if os.path.exists(fn):
        x = pd.read_csv(fn, parse_dates=['release_date', 'ic_week_ended', 'iu_week_ended'])
        for r in x.itertuples():
            if pd.notna(r.icnsa):
                m = d.icw == r.ic_week_ended
                if m.any(): d.loc[m & d.icnsa.isna(), 'icnsa'] = r.icnsa
                else: d = pd.concat([d, pd.DataFrame([dict(rel=r.release_date, icw=r.ic_week_ended, icnsa=r.icnsa, kind='alfred-nsa')])], ignore_index=True)
            if pd.notna(r.iunsa):
                m = d.iuw == r.iu_week_ended
                if m.any(): d.loc[m & d.iunsa.isna(), 'iunsa'] = r.iunsa
                else: d = pd.concat([d, pd.DataFrame([dict(rel=r.release_date, iuw=r.iu_week_ended, iunsa=r.iunsa, kind='alfred-nsa')])], ignore_index=True)
    # weeks still without an NSA first print (the newest weeks, before the appender has run): FRED's latest ICNSA/CCNSA, labelled FILL,
    # known on the week's usual release day (initial: week + 5 d, the Thursday; insured: week + 12 d) - the 981 shadow's basis
    FILL = {}
    for col, series, wcol, lag in (('icnsa', 'ICNSA', 'icw', 5), ('iunsa', 'CCNSA', 'iuw', 12)):
        have = set(d.loc[d[col].notna(), wcol].dropna())
        if not have: continue
        s = fred_monthly(series)
        new = s[(s.index > max(have)) & (s.index + pd.Timedelta(days=lag) <= TODAY)]
        for wk, v in new.items():
            d = pd.concat([d, pd.DataFrame([{wcol: wk, col: float(v), 'rel': wk + pd.Timedelta(days=lag), 'kind': 'FILL ' + series}])], ignore_index=True); fills += 1
        FILL[col] = [str(x.date()) for x in new.index]
    return d, FILL
def weekly_prints(d, wcol, vcol):
    """(week-ending days, values, known days) of a first-print column, one row per week (the earliest release), sorted by week"""
    x = d[[wcol, vcol, 'rel']].dropna().sort_values(['rel']).drop_duplicates(wcol, keep='first').sort_values(wcol)
    return x[wcol].values, x[vcol].values.astype(float), x['rel'].values
def weekly_yoy_log(weeks, vals, knowns, w=4, L=52):
    """569 libbuild strict_weekly, form yoy, log: on each known day the newest known week; 100 x log(sum of the w newest weeks / the same w
    weeks 52 weeks earlier), every week of both spans known by that day; painted daily from the known day"""
    w0 = pd.to_datetime(pd.Series(weeks)).values; v0 = np.asarray(vals, float); k0 = pd.to_datetime(pd.Series(knowns)).values
    ok = ~pd.isna(w0) & ~pd.isna(k0) & np.isfinite(v0) & (v0 > 0); w0, v0, k0 = w0[ok], v0[ok], k0[ok]
    if len(w0) == 0: return np.full(N, np.nan)
    o = np.sort(w0); g = np.rint((w0 - o[0]) / np.timedelta64(7, 'D')).astype(int); n = int(g.max()) + 1
    lv = np.full(n, np.nan); k = np.full(n, np.datetime64('NaT'), dtype='datetime64[ns]')
    for j in np.lexsort((k0, g)):
        if np.isnan(lv[g[j]]): lv[g[j]] = v0[j]; k[g[j]] = k0[j]
    has = ~np.isnat(k) & np.isfinite(lv); pairs = []
    for dd in np.unique(k[has]):
        av = has & (k <= dd); i = int(np.flatnonzero(av).max()); x = np.where(av, lv, np.nan)
        if i - L - w + 1 < 0: continue
        cur, base = x[i - w + 1:i + 1], x[i - L - w + 1:i - L + 1]
        if np.isfinite(cur).all() and np.isfinite(base).all() and cur.sum() > 0 and base.sum() > 0:
            pairs.append((di(pd.Timestamp(dd)), 100.0 * math.log(cur.sum() / base.sum())))
    return paint(pairs, default=np.nan)
def weekly_high(weeks, vals, knowns, w=4, win=CHI_WIN):
    """the record's door statistic (1000c high_arr): the 4-week mean of the first prints, each print at its release day, at or above every
    print released in the prior 365 days; painted from the release day to the next"""
    x = pd.DataFrame({'w': pd.to_datetime(pd.Series(weeks)), 'v': np.asarray(vals, float), 'r': pd.to_datetime(pd.Series(knowns))}).dropna().sort_values('w')
    x['m4'] = x.v.rolling(w).mean(); x = x.dropna().sort_values('r').drop_duplicates('r', keep='last')
    r = x.r.values; v = x.m4.values; pairs = []
    for kk in range(1, len(r)):
        lo = np.searchsorted(r, r[kk] - np.timedelta64(win, 'D'), side='left'); prev = v[lo:kk]
        if len(prev): pairs.append((di(pd.Timestamp(r[kk])), bool(v[kk] >= prev.max())))
    return paint(pairs)

# ---------------------------------------------------------------- the pillars, as of every day
def build():
    P = {}; VAL = {}; SRC = {}
    # SY: the S&P 500 close (the site's daily file) below its close 365 calendar days earlier, on 25 consecutive days (920 egrid + held(25))
    spf = os.path.join(ROOT, '24_bristow_rule_lab', 'workspace', 'lab', 'speed2', 'data', 'sp500_daily_yahoo.csv')
    if not os.path.exists(spf) and os.environ.get('BHS_PRIVATE_ROOT'): spf = os.path.join(os.environ['BHS_PRIVATE_ROOT'], '24_bristow_rule_lab', 'workspace', 'lab', 'speed2', 'data', 'sp500_daily_yahoo.csv')   # the private-data repository on the Mac (the runner copies it in at the same path)
    sp = pd.read_csv(spf, index_col=0, parse_dates=True).iloc[:, 0].astype(float).dropna(); sp = sp[~sp.index.duplicated()].sort_index()
    spd = sp.reindex(pd.date_range(sp.index[0], max(sp.index[-1], TODAY))).ffill(); y1 = (spd / spd.shift(365) - 1)
    below = paint([(di(t), bool(v < 0)) for t, v in y1.dropna().items() if di(t) >= -1])
    cs = np.r_[0, np.cumsum(below.astype(int))]; ii = np.arange(N); lo = np.maximum(0, ii - SY_HOLD + 1); held = (cs[ii + 1] - cs[lo]) > 0   # 920 held(): below a year earlier on any of the last 25 days
    since = int(np.flatnonzero(below)[-1]) if below.any() else None
    P['SY'] = held; VAL['SY'] = dict(sp_last=float(sp.iloc[-1]), sp_last_day=str(sp.index[-1].date()), yoy_pct=round(100 * float(y1.dropna().iloc[-1]), 2), last_day_below_year_ago=(str(day(since).date()) if since is not None else None), days_since=(N - 1 - since) if since is not None else None); SRC['SY'] = spf
    # BAA: Moody's Baa monthly average above its low of the prior 12 months, known the 7th of the next month (the record's leg moody_baa_m [m1])
    baa = fred_monthly('BAA'); pairs = []
    for i in range(12, len(baa)):
        m = baa.index[i]; prior = baa.iloc[i - 12:i]; pairs.append((di(m + pd.DateOffset(months=1, days=6)), bool(baa.iloc[i] > prior.min())))
    P['BAA'] = paint(pairs); VAL['BAA'] = dict(month=str(baa.index[-1].date())[:7], value=float(baa.iloc[-1]), low12=float(baa.iloc[-13:-1].min()), pp_above_low=round(float(baa.iloc[-1] - baa.iloc[-13:-1].min()), 2)); SRC['BAA'] = 'FRED BAA (H.15 monthly average)'
    # IP: the newest industrial production print (G.17, ALFRED vintages) below its high of the prior 12 months within that vintage
    VIP = alfred('INDPRO'); P['IP'] = within(VIP, lambda s, last, prior: s.loc[last] < prior.max())
    s = VIP[max(VIP)]; last = s.index.max(); pr = s[(s.index < last) & (s.index >= last - pd.DateOffset(months=12))]
    VAL['IP'] = dict(vintage=str(max(VIP).date()), month=str(last.date())[:7], value=float(s.loc[last]), high12=float(pr.max()), pct_below_high=round(100 * (float(s.loc[last]) / float(pr.max()) - 1), 2)); SRC['IP'] = 'ALFRED INDPRO vintages (G.17)'
    # P: payrolls (newest print) below their high of the prior 12 months and below last month, within the vintage (vint_991 = 1.000 identity, 1019 T2)
    VPA = alfred('PAYEMS'); P['P'] = within(VPA, lambda s, last, prior: s.loc[last] < prior.max() and s.loc[last] < s.iloc[-2])
    s = VPA[max(VPA)]; last = s.index.max(); pr = s[(s.index < last) & (s.index >= last - pd.DateOffset(months=12))]
    VAL['P'] = dict(vintage=str(max(VPA).date()), month=str(last.date())[:7], value=float(s.loc[last]), high12=float(pr.max()), thousands_below_high=round(float(pr.max() - s.loc[last]), 0), below_last_month=bool(s.loc[last] < s.iloc[-2])); SRC['P'] = 'ALFRED PAYEMS vintages (Employment Situation)'
    # HH: the household survey's unemployment rate within the newest vintage: (this month + last month)/2 - (3 and 4 months earlier)/2 >= 0.3 (urd3s), or P and >= 0.2 (urd3s2)
    VUR = alfred('UNRATE')
    def urtest(line):
        def f(s, last, prior):
            q = [s.get(last - pd.DateOffset(months=k)) for k in (1, 3, 4)]
            return None not in q and (s.loc[last] + q[0]) / 2 - (q[1] + q[2]) / 2 >= line - 1e-9
        return f
    urd3s = within(VUR, urtest(LINE_UR)); urd3s2 = within(VUR, urtest(LINE_UR2)); P['HH'] = urd3s | (P['P'] & urd3s2)
    s = VUR[max(VUR)]; last = s.index.max(); q = [s.get(last - pd.DateOffset(months=k)) for k in (1, 3, 4)]
    VAL['HH'] = dict(vintage=str(max(VUR).date()), month=str(last.date())[:7], ur=float(s.loc[last]), two_month_rise=round((s.loc[last] + q[0]) / 2 - (q[1] + q[2]) / 2, 3) if None not in q else None, line=LINE_UR, line_with_payrolls=LINE_UR2); SRC['HH'] = 'ALFRED UNRATE vintages (Employment Situation)'
    # COUNT: the unemployed count's first print at or above every one of the prior 12 months' first prints (9 or more present) - the record's cnt_high
    VCN = alfred('UNEMPLOY'); fp = first_prints(VCN); pairs = []; months = list(fp)
    for j, m in enumerate(months):
        vd, v = fp[m]; prior = [fp[m - pd.DateOffset(months=k)][1] for k in range(1, 13) if (m - pd.DateOffset(months=k)) in fp]
        if len(prior) >= 9: pairs.append((di(vd), bool(v >= max(prior) - 1e-9)))
    P['CNT'] = paint(pairs)
    if months:
        m = months[-1]; prior = [fp[m - pd.DateOffset(months=k)][1] for k in range(1, 13) if (m - pd.DateOffset(months=k)) in fp]
        VAL['CNT'] = dict(month=str(m.date())[:7], first_print=fp[m][1], known=str(fp[m][0].date()), max_prior_12_first_prints=max(prior) if prior else None)
    SRC['CNT'] = 'ALFRED UNEMPLOY vintages: each month as first printed'
    return P, VAL, SRC, dict(VIP=VIP, VPA=VPA, VUR=VUR, VCN=VCN, sp=sp)

def build2(P, VAL, SRC, D):
    # the weekly claims first prints
    cl, FILL = load_claims()
    icw, icv, ick = weekly_prints(cl, 'icw', 'icnsa'); iuw, iuv, iuk = weekly_prints(cl, 'iuw', 'iunsa')
    c4 = weekly_yoy_log(icw, icv, ick, 4); i4 = weekly_yoy_log(iuw, iuv, iuk, 4)
    P['I4'] = np.nan_to_num(i4, nan=-9) > 0
    VAL['I4'] = dict(week=str(pd.Timestamp(iuw[-1]).date()), yoy_log_pts_4wk=round(float(np.nan_to_num(i4, nan=np.nan)[-1]), 2) if np.isfinite(i4[-1]) else None, fills=FILL.get('iunsa', [])); SRC['I4'] = 'DOL weekly claims release: insured unemployment NSA as first printed (45 + E66; ALFRED CCNSA initial releases)'
    # HW: JOLTS openings yoy (ratio - 1, the newest print of each month, from its release day) below initial claims' 4-week NSA yoy (100 x log / 100)
    VJ = alfred('JTSJOL'); fpj = first_prints(VJ); pairs = []
    for m, (vd, v) in fpj.items():
        if (m - pd.DateOffset(years=1)) in fpj:
            # the year-earlier month as it stood on that release day (the newest vintage at or before vd)
            vint = max((k for k in VJ if k <= vd), default=None)
            if vint is None: continue
            s = VJ[vint]; ym = m - pd.DateOffset(years=1)
            if ym in s.index and s[ym] > 0: pairs.append((di(vd), float(v / s[ym] - 1)))
    hy = paint(sorted(pairs + [(d + 41, np.nan) for (d, _), (d2, _) in zip(pairs, pairs[1:] + [(10**9, None)]) if d2 > d + 41]), default=np.nan)
    # a reading older than 40 days past the month it belongs to lapses, as the record's monthly_to_days(ffill=40) does - from the release day
    lapse = paint([(d + 40, np.nan) for d, _ in pairs], default=np.nan)
    P['HW'] = np.nan_to_num(hy - c4 / 100.0, nan=1) < 0; P['HW'][np.isnan(hy)] = True   # HWNAN: no help-wanted print standing = the pillar passes
    VAL['HW'] = dict(jolts_month=str(list(fpj)[-1].date())[:7], jolts_yoy_pct=round(100 * pairs[-1][1], 2) if pairs else None, claims_4wk_yoy_log_pts=round(float(c4[-1]), 2) if np.isfinite(c4[-1]) else None, week=str(pd.Timestamp(icw[-1]).date()), fills=FILL.get('icnsa', [])); SRC['HW'] = 'ALFRED JTSJOL (JOLTS openings) against DOL initial claims NSA first prints'
    # CHI: initial or insured claims, seasonally adjusted as first printed, 4-week mean at a 365-day high (release-day window)
    # the NSA first prints seasonally adjusted in real time by collection 298's routine (factors refit every 1 January from data published
    # before it) - the construction the record's door was scored on (300 weekly_claims_rtsa); the 4-week mean at a 365-day high
    sys.path.insert(0, os.path.join(W, 's2')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import c1021_rtsa as RT
    def rt_series(weeks, vals):
        ser = pd.Series(np.asarray(vals, float), index=pd.to_datetime(pd.Series(weeks))).sort_index(); ser = ser[~ser.index.duplicated()]
        ser = ser.reindex(pd.date_range(ser.index[0], ser.index[-1], freq='W-SAT')) if all(t.weekday() == 5 for t in ser.index[:20]) else ser
        sa, f = RT.rtsa(ser.rename('x')); return sa
    ic_sa = rt_series(icw, icv); iu_sa = rt_series(iuw, iuv)
    kic = dict(zip(pd.to_datetime(pd.Series(icw)), pd.to_datetime(pd.Series(ick)))); kiu = dict(zip(pd.to_datetime(pd.Series(iuw)), pd.to_datetime(pd.Series(iuk))))
    a1 = ic_sa.dropna(); a2 = iu_sa.dropna()
    P['CHI'] = weekly_high(a1.index.values, a1.values, [kic.get(t, pd.NaT) for t in a1.index]) | weekly_high(a2.index.values, a2.values, [kiu.get(t, pd.NaT) for t in a2.index])
    _m1 = a1.rolling(4).mean().dropna(); _m2 = a2.rolling(4).mean().dropna(); _r1 = float(_m1.iloc[-1] / _m1[(_m1.index < _m1.index[-1]) & (_m1.index >= _m1.index[-1] - pd.Timedelta(days=365))].max()); _r2 = float(_m2.iloc[-1] / _m2[(_m2.index < _m2.index[-1]) & (_m2.index >= _m2.index[-1] - pd.Timedelta(days=365))].max())
    VAL['CHI'] = dict(ic_week=str(a1.index[-1].date()), ic_rtsa_4wk=round(float(_m1.iloc[-1]), 0), iu_week=str(a2.index[-1].date()), iu_rtsa_4wk=round(float(_m2.iloc[-1]), 0), ratio_to_365d_max=round(max(_r1, _r2), 4)); SRC['CHI'] = 'DOL weekly claims first prints (NSA), seasonally adjusted in real time (298 rtsa), initial or insured'
    # FS: the effective federal funds rate's monthly average up >= 1.5 pp on the previous month, known the day after month end
    ff = fred_monthly('FEDFUNDS'); fs_days = []; fs_ratio_pairs = []
    for i in range(1, len(ff)):
        rise = float(ff.iloc[i] - ff.iloc[i - 1]); d = di(ff.index[i] + pd.offsets.MonthEnd(0) + pd.Timedelta(days=1))
        fs_ratio_pairs.append((d, rise / FS_LINE))
        if rise >= FS_LINE - 1e-9 and d >= 0: fs_days.append(d)
    P['FS_RATIO'] = paint(fs_ratio_pairs, default=np.nan); VAL['FS'] = dict(month=str(ff.index[-1].date())[:7], rate=float(ff.iloc[-1]), rise_pp=round(float(ff.iloc[-1] - ff.iloc[-2]), 2), line=FS_LINE); SRC['FS'] = 'FRED FEDFUNDS (H.15 monthly average)'
    # JL: job losers' first print up >= 15 log points yoy with the 10y-1y spread negative in any of the prior 12 months; in force 75 d; re-arm at yoy <= 0
    g10 = fred_monthly('GS10'); g1 = fred_monthly('GS1'); inv = ((g10 - g1).dropna() < 0)
    INV = {pd.Period(k, 'M'): bool(v) for k, v in inv.items()}
    VJL = alfred('LNS13023621'); fpl = first_prints(VJL); jl_days = []; jl_ratio_pairs = []; armed = True; jl_last = None
    for m, (vd, v) in fpl.items():
        ym = m - pd.DateOffset(years=1)
        if ym not in fpl or v < 100 or fpl[ym][1] <= 0: continue
        s_ = 100.0 * math.log(v / fpl[ym][1]); jl_last = dict(month=str(m.date())[:7], known=str(vd.date()), yoy_log_pts=round(s_, 2))
        if s_ <= 0: armed = True
        jl_ratio_pairs.append((di(vd), s_ / JL_LINE))
        if s_ < JL_LINE - 1e-9 or not armed: continue
        for k in range(75):
            d = vd + pd.Timedelta(days=k); dm = pd.Period(d, 'M')
            if any(INV.get(dm - j, False) for j in range(1, 13)):
                if di(d) >= 0: jl_days.append(di(d))
                armed = False; break
    P['JL_RATIO'] = paint(jl_ratio_pairs, default=np.nan); P['INV12'] = paint([(di(pd.Timestamp(str(p)) ), any(INV.get(p - j, False) for j in range(1, 13))) for p in sorted(INV)])
    VAL['JL'] = dict(jl_last or {}, line=JL_LINE, curve_inverted_in_prior_12_months=bool(P['INV12'][-1]), spread_last=dict(month=str(inv.index[-1].date())[:7], gs10_minus_gs1=round(float((g10 - g1).dropna().iloc[-1]), 2))); SRC['JL'] = 'ALFRED LNS13023621 (job losers, Employment Situation) with FRED GS10 - GS1'
    return cl, fs_days, jl_days, D

# ---------------------------------------------------------------- the doors, the calls, the reading
ROUTE_KEYS = ('I4', 'HW', 'SY', 'IP', 'BAA', 'HH', 'P'); DOOR_KEYS = ('CNT', 'CHI', 'SY')
def payroll_ok(VPA, t, prev_call):
    """the recovery convention: a new route or door call needs payrolls (the newest print on day t) above their high of the 12 months to the previous call's month"""
    vint = max((k for k in VPA if k <= t), default=None)
    if vint is None: return True
    v = VPA[vint]; lm = prev_call.to_period('M').to_timestamp(); prior = v[(v.index <= lm) & (v.index > lm - pd.DateOffset(months=12))]
    return (not len(prior)) or bool(v.iloc[-1] > prior.max())
def onsets(on, VPA, prev):
    """first days of ON runs, each admitted by the recovery convention against the previous admitted call (prev = the last record call before the grid)"""
    out = []; was = False; last = prev
    for i in range(N):
        if on[i] and not was:
            t = day(i)
            if last is None or payroll_ok(VPA, t, last): out.append(i); last = t
        was = bool(on[i])
    return out
def main():
    P, VAL, SRC, D = build(); cl, fs_days, jl_days, D = build2(P, VAL, SRC, D)
    route = np.ones(N, bool)
    for k in ROUTE_KEYS: route &= P[k]
    door = P['CNT'] & P['CHI'] & P['SY']; P['ROUTE'] = route; P['DOOR'] = door
    # the record's last route and door calls before the grid, for the recovery convention
    rec_calls = [(pd.Timestamp(c['day']), c['door']) for c in REC['calls']]
    prev_route = max((d for d, k in rec_calls if k == 'route' and d < D0), default=None); prev_door = max((d for d, k in rec_calls if k == 'door' and d < D0), default=None)
    pool = [(day(i), 'route') for i in onsets(route, D['VPA'], prev_route)] + [(day(i), 'door') for i in onsets(door, D['VPA'], prev_door)] + [(day(i), 'FS') for i in fs_days] + [(day(i), 'JL') for i in jl_days]
    live = sorted((d, k) for d, k in pool if d >= RECORD_CUT)
    frozen = sorted((d, k) for d, k in rec_calls if d < RECORD_CUT)
    calls = frozen + live
    pd.DataFrame([dict(day=str(d.date()), door=k, basis='record' if d < RECORD_CUT else 'live') for d, k in calls]).to_csv(os.path.join(OUT, 'c1021_calls.csv'), index=False)
    # the reading: each door's share of its conditions on; the fed-shock and job-losers doors by their ratio to the line (1.00 = fires);
    # the day's reading is the strongest door, capped at 0.99 unless a door is actually on (the call is the episode)
    rs = np.mean([P[k] for k in ROUTE_KEYS], axis=0); ds = np.mean([P[k] for k in DOOR_KEYS], axis=0)
    fsr = np.clip(np.nan_to_num(P['FS_RATIO'], nan=0.0), 0, None); jlr = np.clip(np.nan_to_num(P['JL_RATIO'], nan=0.0), 0, None) * P['INV12']
    ev = np.zeros(N, bool)
    for i in fs_days + jl_days:
        if 0 <= i < N: ev[i] = True
    reading = np.maximum.reduce([rs, ds, fsr, jlr]); firing = route | door | ev
    reading = np.where(firing, np.maximum(reading, 1.0), np.minimum(reading, 0.99))
    pd.DataFrame(dict(day=[str(day(i).date()) for i in range(N)], reading=np.round(reading, 4), route_share=np.round(rs, 4), door_share=np.round(ds, 4), fs_ratio=np.round(fsr, 4), jl_ratio=np.round(jlr, 4), **{k: P[k].astype(int) for k in ROUTE_KEYS + ('CNT', 'CHI', 'INV12')})).to_csv(os.path.join(CACHE, 'reading_daily.csv'), index=False)
    today = dict(day=str(TODAY.date()), reading=round(float(reading[-1]), 4), route=dict(on=bool(route[-1]), share=round(float(rs[-1]), 3), pillars={k: bool(P[k][-1]) for k in ROUTE_KEYS}),
                 count_door=dict(on=bool(door[-1]), share=round(float(ds[-1]), 3), conditions={k: bool(P[k][-1]) for k in DOOR_KEYS}), fs_door=dict(on=bool(fs_days and fs_days[-1] == N - 1), ratio=round(float(fsr[-1]), 3)),
                 jl_door=dict(on=bool(jl_days and jl_days[-1] == N - 1), ratio=round(float(jlr[-1]), 3), armed_witness=bool(P['INV12'][-1])))
    state = dict(tool='C1021', built=str(dt.datetime.utcnow())[:19] + 'Z', grid=dict(day0=str(D0.date()), days=N), record_cut=str(RECORD_CUT.date()), today=today, values=VAL, sources=SRC,
                 calls=[dict(day=str(d.date()), door=k, basis='record' if d < RECORD_CUT else 'live') for d, k in calls], live_calls=[dict(day=str(d.date()), door=k) for d, k in live],
                 pillar_last_on={k: (str(day(int(np.flatnonzero(P[k])[-1])).date()) if P[k].any() else None) for k in ROUTE_KEYS + ('CNT', 'CHI')}, log=LOG)
    json.dump(state, open(os.path.join(OUT, 'c1021_state.json'), 'w'), indent=1, default=str)
    say('calls', [(str(d.date()), k) for d, k in calls[-6:]], '| live since', RECORD_CUT.date(), [(str(d.date()), k) for d, k in live], '| today', json.dumps(today)[:400])
    np.savez(os.path.join(CACHE, 'pillars_live.npz'), day0=str(D0.date()), n=N, **{k: v for k, v in P.items() if v.dtype == bool})
    return P, calls
if __name__ == '__main__':
    P, calls = main()
    ref = os.environ.get('BHS_C1021_IDENTITY')
    if ref:   # the identity gate (1022 G1): every pillar against the harness's arrays, day by day, from 2015-01-01 to the end of the harness grid
        Z = np.load(ref); rd0 = pd.Timestamp(str(Z['day0'])); rn = int(Z['n']); a = max(D0, pd.Timestamp('2015-01-01')); b = min(TODAY, rd0 + pd.Timedelta(days=rn - 1))
        ia, ib = di(a), di(b) + 1; ja, jb = int((a - rd0).days), int((b - rd0).days) + 1; rep = {}
        for k in ROUTE_KEYS + ('CNT', 'CHI', 'ROUTE', 'DOOR'):
            if k not in Z.files: continue
            L_ = P[k][ia:ib]; R_ = Z[k][ja:jb].astype(bool); dis = np.flatnonzero(L_ != R_)
            spans = []
            if len(dis):
                st = dis[0]; pv = dis[0]
                for x in dis[1:]:
                    if x != pv + 1: spans.append((str(day(ia + st).date()), str(day(ia + pv).date()))); st = x
                    pv = x
                spans.append((str(day(ia + st).date()), str(day(ia + pv).date())))
            rep[k] = dict(agree=round(float((L_ == R_).mean()), 4), disagreeing_days=int(len(dis)), spans=spans[:10], live_on_days=int(L_.sum()), ref_on_days=int(R_.sum()))
            print('%-6s agree %.4f  dis %4d  live_on %5d ref_on %5d  spans %s' % (k, rep[k]['agree'], len(dis), L_.sum(), R_.sum(), spans[:3]))
        json.dump(dict(window=[str(a.date()), str(b.date())], pillars=rep, live_calls=[(str(d.date()), k) for d, k in calls if d >= pd.Timestamp('2015-01-01')]), open(os.path.join(OUT, 'c1021_identity.json'), 'w'), indent=1)
