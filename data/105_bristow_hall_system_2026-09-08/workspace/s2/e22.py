"""s2/e22.py - THE E22 ENDER, LIVE (collection 1031, 9 November 2026; Anthony 06:21 PT: "lets port e22"). Replaces v3.76's closers.
The harness is 1026/code/ender_on_v4/battery_1028.py fam()['E22'] (RECORD-1027/1028/1030); every function below is that harness's, copied,
with one change only: the harness bounded each search by the NBER trough (+500/+700 days) and measured the NSA print's coverage to the trough
+548 days; live there is no NBER date, so searches run to the newest print and coverage is measured over the open's first 548 days (or to today).
After an episode opened by C1021, END on the first day either leg fires:
  LEG A - insured unemployment, 4-week average of the seasonally adjusted first prints, keyed by release day. Primed by an unbroken run of
  8 weekly rises whose 8th rise is released after the open (or, at the open, the newest print ends such a run). Falls: the newest print below
  the post-priming high by more than 3 x the median absolute weekly change of the prior 52 prints (also the NSA 4-week year-on-year ratio when
  it covers >= 80% of the weeks; the later of the two). Then the first print day on which the 8-print second difference is negative (both
  prints when two) and the policy rate is below its level 12 months earlier (FEDFUNDS; TB3MS before July 1954; known the first business day
  after the month).
  LEG S - the S&P 500 at least 20 per cent above its lowest close since the open (the published bull-market definition), insured unemployment
  not at a new post-priming high, and the policy rate below its level 12 months earlier.
  LEG Q (1032) - the same bull-market line and insured unemployment off its high, with no policy-rate condition but insured unemployment below
  its print a quarter (13 prints) earlier: the end of a recession in which the Fed does not ease.
  LEG QG (1034) - the same bull-market line and insured unemployment off its high, insured unemployment OR initial claims (4-week mean of the SA
  first prints) below its print a quarter earlier, but only after insured unemployment has risen by a third over its print on the open day
  (a recovery follows damage): ends a no-ease recession sooner.
  DEPTH GATE (1041) on legs S and QG - when the S&P's fall since the open (from the highest close of the 365 days before the open) is deeper
  than its deepest fall on any day of the 20 years before the open outside earlier recessions, the leg also needs industrial production (the
  newest ALFRED INDPRO vintage known that day) above its lowest month since the open by more than its median monthly move of the prior 24
  months: in a deep bear market a 20% rally can come before the economy turns.
Chronology: C1021's calls open (out/c1021_state.json); an open needs no open episode and more than 183 days since the last close.
Inputs: s2/e22_history.csv (chain v4 1946-2026, frozen: week, iu_nsa, iu_rtsa (SA first print), iu_release, ic_rtsa, ic_release), then the merged first-print
table cache/national_first_prints_1985_live.csv (+ cache/c1021/claims_nsa_first_prints.csv) for newer weeks; s2/e22_rate_history.csv then
cache/c1021/FEDFUNDS.csv; the S&P daily file as s2/c1021.py reads it. Writes out/e22_state.json.
Run from the live workspace after s2/c1021.py: python3 s2/e22.py   (BHS_E22_GATE=1 prints the gate against the harness's record)."""
import os, sys, json, datetime as dt
import numpy as np, pandas as pd
ROOT = os.environ.get('BHS_ROOT') or next((r for r in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')) if os.path.isdir(r)), '')
W = os.getcwd(); S2 = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(W, 'out'); os.makedirs(OUT, exist_ok=True)
TODAY = pd.Timestamp(os.environ.get('BHS_TODAY') or dt.date.today())
K_RUN, K_SIG, H_SIG, L_DEC, BULL, GAP, COV, COV_DAYS = 8, 3, 1, 8, 1.2, 183, 0.8, 548
QTR, DMG = 13, 1.0 / 3.0
DEPTH_YEARS = 20   # the depth gate's quiet record: the 20 years before the open
AL = os.environ.get('BHS_C1021_ALFRED') or os.path.join(ROOT, 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages')
BOARD = [('1948-11', '1949-10'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'), ('1969-12', '1970-11'), ('1973-11', '1975-03'),
         ('1980-01', '1980-07'), ('1981-07', '1982-11'), ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04')]
SPANS = [(pd.Timestamp(a + '-01'), pd.Timestamp(b + '-01') + pd.offsets.MonthEnd(0)) for a, b in BOARD]   # + the tool's own closed episodes after 2020 (chronology)
IPV = None   # (vintage days array, list of Series), loaded once   # leg Q/QG: a quarter of weekly prints; QG's damage line (insured unemployment up a third over the open)
LOG = []; READING = []
def say(*a):
    s = ' '.join(str(x) for x in a); LOG.append(s); print('e22:', s, flush=True)

# ---------------------------------------------------------------- inputs
def load_weekly():
    H = pd.read_csv(os.path.join(S2, 'e22_history.csv'), parse_dates=['week_ending', 'iu_release', 'ic_release']).set_index('week_ending').sort_index()
    lastc = H.index[H['ic_rtsa'].notna()].max(); ictail = []
    last = H.index[H['iu_rtsa'].notna()].max(); tail = []
    f = os.path.join(W, 'cache', 'national_first_prints_1985_live.csv')
    f45 = os.path.join(ROOT, '45_dol_first_prints_2026-09', 'national_first_prints.csv')   # the update appends each release here; the build's merged table follows at the build
    fs = [x for x in (f, f45) if os.path.exists(x)]
    if fs:
        d = pd.concat([pd.read_csv(x, dtype=str) for x in fs], ignore_index=True).fillna('')
        d['rel'] = pd.to_datetime(d['release_date'], errors='coerce'); d['iuw'] = pd.to_datetime(d['iu_week_ended'], errors='coerce')
        for c in ('iusa', 'iunsa'): d[c] = pd.to_numeric(d[c], errors='coerce')
        fn = os.path.join(W, 'cache', 'c1021', 'claims_nsa_first_prints.csv')
        nsa = {}
        if os.path.exists(fn):
            x = pd.read_csv(fn, parse_dates=['release_date', 'iu_week_ended'])
            for r in x.itertuples():
                if pd.notna(r.iunsa) and pd.notna(r.iu_week_ended): nsa.setdefault(pd.Timestamp(r.iu_week_ended), float(r.iunsa))
        x = d[d.iusa.notna() & d.iuw.notna() & d.rel.notna()].sort_values('rel').drop_duplicates('iuw', keep='first')
        x = x[x.iuw > last]
        for r in x.itertuples():
            wk = r.iuw + pd.Timedelta(days=(5 - r.iuw.weekday()) % 7)
            n = r.iunsa if pd.notna(r.iunsa) else nsa.get(r.iuw, np.nan)
            tail.append(dict(week_ending=wk, iu_nsa=n, iu_rtsa=float(r.iusa), iu_release=r.rel))
        # 1034: initial claims SA first print (icsa) for weeks after the frozen chain, first release of each week
        d['icw'] = pd.to_datetime(d['ic_week_ended'], errors='coerce'); d['icsa_'] = pd.to_numeric(d['icsa'], errors='coerce')
        y = d[d.icsa_.notna() & d.icw.notna() & d.rel.notna()].sort_values('rel').drop_duplicates('icw', keep='first')
        for r in y[y.icw > lastc].itertuples():
            ictail.append((r.icw + pd.Timedelta(days=(5 - r.icw.weekday()) % 7), float(r.icsa_), r.rel))
    if tail:
        T = pd.DataFrame(tail).set_index('week_ending'); H = pd.concat([H[H.index <= last], T[~T.index.duplicated(keep='first')]]).sort_index()
    # 1031c (9 Nov 2026, the open-episode drill): the frozen chain's NSA level has holes in its newest weeks (2026-08-08..09-12), and a hole
    # breaks the NSA print's 4-week mean, so a live episode read one print where it should read two. NSA holes from 2025 on are filled from the
    # first prints the update keeps (ALFRED's initial release of CCNSA, then the release tables' iunsa); no record episode reads a week after 2024.
    nfill = 0
    if fs:
        for r in d[d.iunsa.notna() & d.iuw.notna()].sort_values('rel').drop_duplicates('iuw', keep='first').itertuples():
            nsa.setdefault(pd.Timestamp(r.iuw), float(r.iunsa))
        for wk0, v in nsa.items():
            wk = wk0 + pd.Timedelta(days=(5 - wk0.weekday()) % 7)
            if wk >= pd.Timestamp('2025-01-01') and wk in H.index and pd.isna(H.at[wk, 'iu_nsa']): H.at[wk, 'iu_nsa'] = v; nfill += 1
    if nfill: say('NSA holes filled from first prints (2025 on): %d weeks' % nfill)
    for wk, x, rl in ictail:
        if wk not in H.index: H.loc[wk, 'iu_rtsa'] = np.nan
        if pd.isna(H.at[wk, 'ic_rtsa']): H.at[wk, 'ic_rtsa'] = x; H.at[wk, 'ic_release'] = rl
    H = H.sort_index()
    if ictail: say('initial claims: frozen chain to %s, %d live weeks after' % (lastc.date(), len(ictail)))
    grid = pd.date_range(H.index.min(), H.index.max(), freq='7D')
    H = H.reindex(grid); H.index.name = 'week_ending'
    say('weekly insured unemployment: frozen chain to %s, %d live weeks after (newest week %s, released %s)' % (last.date(), len(tail), H.index[H.iu_rtsa.notna()].max().date(), H.loc[H.iu_rtsa.notna(), 'iu_release'].max().date()))
    return H, len(tail)
def load_rate():
    R = pd.read_csv(os.path.join(S2, 'e22_rate_history.csv'), parse_dates=['month']).set_index('month').rate.astype(float)
    f = os.path.join(W, 'cache', 'c1021', 'FEDFUNDS.csv')
    if os.path.exists(f):
        ff = pd.read_csv(f, parse_dates=['date']).set_index('date').v.astype(float)
        new = ff[ff.index > R.index.max()]
        if len(new): R = pd.concat([R, new]).sort_index()
    yo = (R < R.shift(12)); known = sorted([(m + pd.offsets.MonthEnd(0) + pd.offsets.BDay(1), bool(e)) for m, e in zip(yo.index, yo.values) if pd.notna(R.shift(12).get(m))])
    say('policy rate: to %s (%.2f), below a year earlier: %s' % (R.index.max().date(), R.iloc[-1], known[-1][1]))
    return R, known
def load_sp():
    spf = os.path.join(ROOT, '24_bristow_rule_lab', 'workspace', 'lab', 'speed2', 'data', 'sp500_daily_yahoo.csv')
    if not os.path.exists(spf) and os.environ.get('BHS_PRIVATE_ROOT'): spf = os.path.join(os.environ['BHS_PRIVATE_ROOT'], '24_bristow_rule_lab', 'workspace', 'lab', 'speed2', 'data', 'sp500_daily_yahoo.csv')
    if os.environ.get('BHS_E22_SPFILE'): spf = os.environ['BHS_E22_SPFILE']
    if not os.path.exists(spf): raise SystemExit('e22: the S&P 500 daily file is missing (%s) - the run stops' % spf)
    sp = pd.read_csv(spf, index_col=0, parse_dates=True).iloc[:, 0].astype(float).dropna(); sp = sp[~sp.index.duplicated()].sort_index()
    say('S&P 500: to %s (%.2f)' % (sp.index[-1].date(), sp.iloc[-1])); return sp

def load_ip():
    global IPV
    if IPV is not None: return IPV
    f = os.path.join(AL, 'INDPRO_all_vintages.csv')
    if not os.path.exists(f) and os.path.exists(f + '.gz'): f = f + '.gz'
    if not os.path.exists(f): raise SystemExit('e22: the ALFRED INDPRO vintage table is missing (%s) - the run stops' % f)
    T = pd.read_csv(f); T.index = pd.to_datetime(T.iloc[:, 0]); T = T.drop(columns=[T.columns[0]])
    vs = []
    for c in T.columns:
        try: vd = pd.Timestamp(c.split('_')[-1])
        except Exception: continue
        x = pd.to_numeric(T[c], errors='coerce').dropna().astype(float)
        if len(x): vs.append((vd, x))
    vs.sort(key=lambda t: t[0]); IPV = (np.array([v for v, _ in vs], dtype='datetime64[ns]'), [x for _, x in vs])
    say('industrial production: %d ALFRED vintages, newest %s' % (len(vs), str(vs[-1][0].date())))
    return IPV
QCACHE = {}
def quiet_depth(SP, s0):
    k = (id(SP), pd.Timestamp(s0))
    if k in QCACHE: return QCACHE[k]
    dd = 1 - SP / SP.rolling('365D').max(); s0 = pd.Timestamp(s0)
    x = dd[(dd.index >= s0 - pd.DateOffset(years=DEPTH_YEARS)) & (dd.index <= s0 - pd.Timedelta(days=365))]
    m = np.ones(len(x), bool)
    for a, b in SPANS: m &= ~((x.index >= a) & (x.index <= b))
    QCACHE[k] = float(x[m].max()) if m.any() else 0.0; return QCACHE[k]
def depth_ok(SP, s0, d):
    """True when the leg may fire on day d: the fall is not deeper than the quiet record, or industrial production is off its low"""
    seg = SP[(SP.index > s0) & (SP.index <= d)]
    if not len(seg): return True
    ld = seg.idxmin(); pk = SP[(SP.index > s0 - pd.Timedelta(days=365)) & (SP.index <= ld)].max()
    if 1 - seg.min() / pk <= quiet_depth(SP, s0): return True
    VD, VS = load_ip(); j = int(np.searchsorted(VD, np.datetime64(pd.Timestamp(d)), side='right')) - 1
    if j < 0: return False
    x = VS[j]
    if len(x) < 26: return False
    m0 = pd.Timestamp(s0.year, s0.month, 1); sg = x[x.index >= m0]
    if len(sg) < 2: return False
    sc = np.median(np.abs(np.diff(x.values[-25:])))
    return bool(x.iloc[-1] - sg.min() > sc)

# ---------------------------------------------------------------- the harness's functions (copied; caps -> None live)
def mk(vals, r):
    return sorted([(r.iloc[j], float(vals[j])) for j in range(len(vals)) if pd.notna(r.iloc[j]) and np.isfinite(vals[j])])
def paths(X):
    v = X['iu_nsa'].astype(float).values; rel = pd.to_datetime(X['iu_release'], errors='coerce'); sa = X['iu_rtsa'].astype(float).values
    s4 = pd.Series(v).rolling(4).mean(); yy = (s4 / s4.shift(52)).values; a = pd.Series(sa).rolling(4).mean().values
    P = {'IU4': mk(a, rel), 'IUy4': mk(yy, rel)}
    if 'ic_rtsa' in X.columns:   # 1034: initial claims, 4-week mean of the SA first prints, keyed by release day
        P['IC4'] = mk(pd.Series(X['ic_rtsa'].astype(float).values).rolling(4).mean().values, pd.to_datetime(X['ic_release'], errors='coerce'))
    return P
def prime_idx(path, s0, K=K_RUN):
    prev = None; run = 0
    for i, (kd, x) in enumerate(path):
        if prev is not None:
            run = run + 1 if x > prev else 0
            if run >= K and kd > s0: return i
        prev = x
        if kd > s0 + pd.Timedelta(days=900): return None
    return None
def prime_ix(path, s0, K=K_RUN):
    """F2 (PREREG-41): at the open, a newest print that ends an unbroken run of >= K rises primes at the first print after the open"""
    ks = [kd for kd, _ in path]
    j = max([i for i, kd in enumerate(ks) if kd <= s0], default=None); first_after = next((i for i, kd in enumerate(ks) if kd > s0), None)
    if j is not None and first_after is not None:
        r = 0
        while j - r - 1 >= 0 and path[j - r][1] > path[j - r - 1][1]: r += 1
        if r >= K: return (first_after, j - r)
    i = prime_idx(path, s0, K); return (i, i)
def hold_sig(path, s0, cap, H, k, K=K_RUN):
    i0, ir = prime_ix(path, s0, K)
    if i0 is None: return None, None
    xs = np.array([x for _, x in path]); d1 = np.abs(np.diff(xs, prepend=np.nan))
    j = int(np.argmax(xs[ir:i0 + 1])) + ir; hi = xs[j]; th = path[j][0]; c = 0
    for i in range(i0 + 1, len(path)):
        kd, x = path[i]
        if cap is not None and kd > cap: return None, None
        if x > hi: hi = x; th = kd; c = 0; continue
        sc = np.nanmedian(d1[max(0, i - 52):i])
        c = c + 1 if (hi - x) > k * sc else 0
        if c >= H: return kd, th
    return None, None
def below_high_state(path, s0, K=K_RUN):
    i0, ir = prime_ix(path, s0, K)
    if i0 is None: return []
    hi = max(x for _, x in path[ir:i0 + 1]); st = []
    for kd, x in path[i0 + 1:]:
        if x > hi: hi = x; st.append((kd, False))
        else: st.append((kd, True))
    return st
def diffs(path, L, n):
    p = path
    for _ in range(n): p = [(p[i][0], p[i][1] - p[i - L][1]) for i in range(L, len(p))]
    return p
def statesL(path, L):
    d2 = dict(diffs(path, L, 2)); S = {}
    for kd, _ in path:
        if kd in d2: S[kd] = d2[kd] < 0
    return S
def witness(known):
    K = np.array([k for k, _ in known], dtype='datetime64[ns]'); E = [e for _, e in known]
    def ok(day):
        i = np.searchsorted(K, np.datetime64(pd.Timestamp(day)), side='right') - 1
        return bool(E[i]) if i >= 0 else False
    return ok
def ender(P, SP, witness_ok, s0, cap=None, cov_end=None):
    """E22 for one episode opened on s0; returns (close day or None, detail dict)"""
    s0 = pd.Timestamp(s0)
    ks = np.array([k for k, _ in P['IUy4']], dtype='datetime64[ns]'); a = np.datetime64(s0)
    b = np.datetime64(cov_end if cov_end is not None else min(TODAY, s0 + pd.Timedelta(days=COV_DAYS)))
    weeks = max((b - a).astype('timedelta64[D]').astype(int) / 7, 1); two = ((ks > a) & (ks <= b)).sum() / weeks >= COV
    sa = hold_sig(P['IU4'], s0, cap, H_SIG, K_SIG)[0]; yy = hold_sig(P['IUy4'], s0, cap, H_SIG, K_SIG)[0]
    sa = None if sa is None else pd.Timestamp(sa).normalize(); yy = None if yy is None else pd.Timestamp(yy).normalize()
    fire = (None if sa is None or yy is None else max(sa, yy)) if two else sa
    A = statesL(P['IU4'], L_DEC); B = statesL(P['IUy4'], L_DEC); ka = sorted(A); kb = sorted(B)
    KA = np.array(ka, dtype='datetime64[ns]'); KB = np.array(kb, dtype='datetime64[ns]')
    def st(S, keys, KK, t):
        i = np.searchsorted(KK, np.datetime64(t), side='right') - 1
        return S[keys[i]] if i >= 0 else False
    legA = None
    if fire is not None:
        for c in [k for k in ka if k >= fire]:
            if cap is not None and c > cap: break
            if st(A, ka, KA, c) and ((not two) or st(B, kb, KB, c)) and witness_ok(c): legA = c; break
    legS = None; stt = below_high_state(P['IU4'], s0)
    if stt:
        kk = np.array([k for k, _ in stt], dtype='datetime64[ns]'); vs = [x for _, x in stt]
        seg = SP[(SP.index > s0) & ((SP.index <= cap) if cap is not None else True)]; lo = seg.cummin()
        for d in seg[seg >= lo * BULL].index:
            i = np.searchsorted(kk, np.datetime64(d), side='right') - 1
            if i >= 0 and vs[i] and witness_ok(d) and depth_ok(SP, s0, d): legS = d; break
    # LEG Q (1032, 9 Nov 2026; PREREG-52, out/battery_1034*.txt): the bull-market line without the policy-rate witness, guarded instead by labour -
    # insured unemployment off its post-priming high AND its newest print below the print a quarter (13 prints) earlier. On every historical,
    # noise, severity, arming and revision test it never fires before E22's own legs (identical records); in a recession the Fed does not ease it
    # ends the episode (no-ease worlds: MAD 210.6 -> 55.2 held flat, 353.7 -> 71.2 rising, never-ends 1 -> 0).
    legQ = None
    if stt:
        ks0 = np.array([k for k, _ in P['IU4']], dtype='datetime64[ns]'); xs0 = np.array([x for _, x in P['IU4']])
        for d in seg[seg >= lo * BULL].index:
            i = np.searchsorted(kk, np.datetime64(d), side='right') - 1; j = np.searchsorted(ks0, np.datetime64(d), side='right') - 1
            if i >= 0 and vs[i] and j >= 13 and xs0[j] < xs0[j - 13]: legQ = d; break
    # LEG QG (1034, 9 Nov 2026; PREREG-53..56, 1031/out/battery_1035-1038; RECORD-1034): the bull line, insured unemployment off its high,
    # insured unemployment OR initial claims below a quarter earlier - only after insured unemployment's running high since the open is at least
    # a third above its print on the open day (no recovery without damage: the gate that stops the harsh-1980 world's Feb-1980 false end).
    # Record, revisions, noise, severity, arming: identical to legs A/S/Q; no-ease worlds 55.2 -> 34.6 (flat), 71.2 -> 45.4 (rising).
    legG = None
    if stt and 'IC4' in P:
        ks0 = np.array([k for k, _ in P['IU4']], dtype='datetime64[ns]'); xs0 = np.array([x for _, x in P['IU4']])
        kc = np.array([k for k, _ in P['IC4']], dtype='datetime64[ns]'); xc = np.array([x for _, x in P['IC4']])
        j0 = int(np.searchsorted(ks0, np.datetime64(s0), side='right')) - 1; base = xs0[j0] if j0 >= 0 else xs0[0]
        for d in seg[seg >= lo * BULL].index:
            i = np.searchsorted(kk, np.datetime64(d), side='right') - 1
            if not (i >= 0 and vs[i]): continue
            jd = int(np.searchsorted(ks0, np.datetime64(d), side='right')) - 1
            if jd <= max(j0, 0) or xs0[max(j0 + 1, 0):jd + 1].max() / base < 1 + DMG: continue
            c_ = int(np.searchsorted(kc, np.datetime64(d), side='right')) - 1
            if (jd >= QTR and xs0[jd] < xs0[jd - QTR]) or (c_ >= QTR and xc[c_] < xc[c_ - QTR]):
                if depth_ok(SP, s0, d): legG = d; break
    c = [x for x in (legA, legS, legQ, legG) if x is not None]; close = min(c) if c else None
    # THE CLOSING READING (descriptive, for the page's chart; it decides nothing): on each insured-unemployment release day from the open to the
    # close (or today), the larger of leg A's share of its four conditions (primed, the significant fall, the deceleration, the policy rate) and
    # leg S's share of its three (the market 20 per cent off its low, insured unemployment off its high, the policy rate); 1.00 on the close day.
    i0 = prime_ix(P['IU4'], s0)[0]; t_prime = P['IU4'][i0][0] if i0 is not None else None
    kk2 = np.array([k for k, _ in stt], dtype='datetime64[ns]') if stt else None; vs2 = [x for _, x in stt] if stt else []
    end = close if close is not None else TODAY; rd = []
    for d in [k for k, _ in P['IU4'] if s0 < k <= end]:
        m_ = witness_ok(d); g_ = bool(st(A, ka, KA, d) and ((not two) or st(B, kb, KB, d)))
        a_ = (int(t_prime is not None and t_prime <= d) + int(fire is not None and fire <= d) + int(g_) + int(m_)) / 4.0
        seg2 = SP[(SP.index > s0) & (SP.index <= d)]
        bull = bool(len(seg2) and seg2.iloc[-1] >= seg2.min() * BULL)
        nh = False
        if kk2 is not None and len(kk2):
            i = np.searchsorted(kk2, np.datetime64(d), side='right') - 1; nh = bool(i >= 0 and vs2[i])
        s_ = (int(bull) + int(nh) + int(m_)) / 3.0
        jq = int(np.searchsorted(np.array([k for k, _ in P['IU4']], dtype='datetime64[ns]'), np.datetime64(d), side='right')) - 1
        qq = bool(jq >= 13 and P['IU4'][jq][1] < P['IU4'][jq - 13][1])
        q_ = (int(bull) + int(nh) + int(qq)) / 3.0
        rd.append((pd.Timestamp(d), round(max(a_, s_, q_), 3)))
    if close is not None: rd = [(t, v) for t, v in rd if t < pd.Timestamp(close)] + [(pd.Timestamp(close).normalize(), 1.0)]
    READING.extend(rd)
    det = dict(open=str(s0.date()), two_prints=bool(two), legA_fall=None if fire is None else str(pd.Timestamp(fire).date()), legA=None if legA is None else str(pd.Timestamp(legA).date()),
               legS=None if legS is None else str(pd.Timestamp(legS).date()), close=None if close is None else str(pd.Timestamp(close).date()),
               legQ=None if legQ is None else str(pd.Timestamp(legQ).date()), legQG=None if legG is None else str(pd.Timestamp(legG).date()),
               leg=None if close is None else ('A' if close == legA else ('S' if close == legS else ('Q' if close == legQ else 'G'))), primed=bool(prime_ix(P['IU4'], s0)[0] is not None))
    return (None if close is None else pd.Timestamp(close).normalize()), det

# ---------------------------------------------------------------- the chronology: C1021 opens, E22 closes
def chronology(calls, P, SP, wok):
    eps = []; last_close = None; open_ = None
    for d in sorted(calls):
        d = pd.Timestamp(d)
        if open_ is not None: continue
        if last_close is not None and (d <= last_close or (d - last_close).days <= GAP): continue
        cl, det = ender(P, SP, wok, d); eps.append(det); open_ = d
        if cl is not None and cl <= TODAY:
            last_close = cl; open_ = None
            if d > SPANS[-1][1] and d.year > 2020: SPANS.append((d, pd.Timestamp(cl))); QCACHE.clear()   # the tool's own episodes join the quiet record's exclusions
        else: det['close'] = None; det['leg'] = None
    return eps

if __name__ == '__main__':
    X, ntail = load_weekly(); R, known = load_rate(); SP = load_sp(); wok = witness(known); P = paths(X)
    st = json.load(open(os.path.join(OUT, 'c1021_state.json')))
    calls = [pd.Timestamp(c['day']) for c in st['calls']]
    eps = chronology(calls, P, SP, wok)
    say('episodes: ' + '; '.join('%s -> %s (%s)' % (e['open'], e['close'] or 'OPEN', e['leg'] or '-') for e in eps))
    cur = eps[-1] if eps else None
    state = dict(tool='E22', version='E22 (1031) + leg Q (1032) + leg QG (1034) + depth gate (1041)', built='', today=str(TODAY.date()),
                 episodes=eps, standing=('in recession since %s' % cur['open']) if (cur and cur['close'] is None) else ('closed since %s' % (cur['close'] if cur else '-')),
                 inputs=dict(iu_newest_week=str(X.index[X.iu_rtsa.notna()].max().date()), iu_live_weeks=ntail, rate_month=str(R.index.max().date())[:7], rate=float(R.iloc[-1]),
                             rate_below_year_ago=bool(known[-1][1]), sp_day=str(SP.index[-1].date()), sp=float(SP.iloc[-1])), log=LOG)
    state['built'] = str(dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None)) + 'Z'
    if cur: state['current'] = cur
    _iu = P['IU4'][-1]; _open = cur is not None and cur['close'] is None
    _sp_since = SP[SP.index > pd.Timestamp(cur['open'])] if _open else None
    _nsa_wk = X.index[X.iu_nsa.notna()].max()
    state['values'] = dict(iu4=dict(value=round(_iu[1], 1), release=str(pd.Timestamp(_iu[0]).date()), week=str(X.index[X.iu_rtsa.notna()].max().date())),
                           iu_nsa=dict(week=str(_nsa_wk.date()) if pd.notna(_nsa_wk) else None),
                           rate=dict(month=str(R.index.max().date())[:7], value=float(R.iloc[-1]), year_earlier=float(R.shift(12).iloc[-1]), diff=round(float(R.iloc[-1] - R.shift(12).iloc[-1]), 2)),
                           sp=dict(day=str(SP.index[-1].date()), close=float(SP.iloc[-1]), ratio_to_low_since_open=(round(float(_sp_since.iloc[-1] / _sp_since.min()), 3) if (_open and len(_sp_since)) else None)),
                           episode_open=_open)
    json.dump(state, open(os.path.join(OUT, 'e22_state.json'), 'w'), indent=1, default=str)
    os.makedirs(os.path.join(W, 'cache', 'e22'), exist_ok=True)
    rd = pd.DataFrame(READING, columns=['day', 'reading']).drop_duplicates('day', keep='last').sort_values('day')
    rd.to_csv(os.path.join(W, 'cache', 'e22', 'closing_daily.csv'), index=False)
    say('closing reading: %d days, latest %s' % (len(rd), (str(rd.day.iloc[-1].date()) + ' %.2f' % rd.reading.iloc[-1]) if len(rd) else '-'))
    say('standing:', state['standing'])
