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
Chronology: C1021's calls open (out/c1021_state.json); an open needs no open episode and more than 183 days since the last close.
Inputs: s2/e22_history.csv (chain v4 1946-2026, frozen: week, iu_nsa, iu_rtsa (SA first print), iu_release), then the merged first-print
table cache/national_first_prints_1985_live.csv (+ cache/c1021/claims_nsa_first_prints.csv) for newer weeks; s2/e22_rate_history.csv then
cache/c1021/FEDFUNDS.csv; the S&P daily file as s2/c1021.py reads it. Writes out/e22_state.json.
Run from the live workspace after s2/c1021.py: python3 s2/e22.py   (BHS_E22_GATE=1 prints the gate against the harness's record)."""
import os, sys, json, datetime as dt
import numpy as np, pandas as pd
ROOT = os.environ.get('BHS_ROOT') or next((r for r in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')) if os.path.isdir(r)), '')
W = os.getcwd(); S2 = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(W, 'out'); os.makedirs(OUT, exist_ok=True)
TODAY = pd.Timestamp(os.environ.get('BHS_TODAY') or dt.date.today())
K_RUN, K_SIG, H_SIG, L_DEC, BULL, GAP, COV, COV_DAYS = 8, 3, 1, 8, 1.2, 183, 0.8, 548
LOG = []; READING = []
def say(*a):
    s = ' '.join(str(x) for x in a); LOG.append(s); print('e22:', s, flush=True)

# ---------------------------------------------------------------- inputs
def load_weekly():
    H = pd.read_csv(os.path.join(S2, 'e22_history.csv'), parse_dates=['week_ending', 'iu_release']).set_index('week_ending').sort_index()
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
    if tail:
        T = pd.DataFrame(tail).set_index('week_ending'); H = pd.concat([H[H.index <= last], T[~T.index.duplicated(keep='first')]]).sort_index()
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

# ---------------------------------------------------------------- the harness's functions (copied; caps -> None live)
def mk(vals, r):
    return sorted([(r.iloc[j], float(vals[j])) for j in range(len(vals)) if pd.notna(r.iloc[j]) and np.isfinite(vals[j])])
def paths(X):
    v = X['iu_nsa'].astype(float).values; rel = pd.to_datetime(X['iu_release'], errors='coerce'); sa = X['iu_rtsa'].astype(float).values
    s4 = pd.Series(v).rolling(4).mean(); yy = (s4 / s4.shift(52)).values; a = pd.Series(sa).rolling(4).mean().values
    return {'IU4': mk(a, rel), 'IUy4': mk(yy, rel)}
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
            if i >= 0 and vs[i] and witness_ok(d): legS = d; break
    c = [x for x in (legA, legS) if x is not None]; close = min(c) if c else None
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
        rd.append((pd.Timestamp(d), round(max(a_, s_), 3)))
    if close is not None: rd = [(t, v) for t, v in rd if t < pd.Timestamp(close)] + [(pd.Timestamp(close).normalize(), 1.0)]
    READING.extend(rd)
    det = dict(open=str(s0.date()), two_prints=bool(two), legA_fall=None if fire is None else str(pd.Timestamp(fire).date()), legA=None if legA is None else str(pd.Timestamp(legA).date()),
               legS=None if legS is None else str(pd.Timestamp(legS).date()), close=None if close is None else str(pd.Timestamp(close).date()),
               leg=None if close is None else ('A' if close == legA else 'S'), primed=bool(prime_ix(P['IU4'], s0)[0] is not None))
    return (None if close is None else pd.Timestamp(close).normalize()), det

# ---------------------------------------------------------------- the chronology: C1021 opens, E22 closes
def chronology(calls, P, SP, wok):
    eps = []; last_close = None; open_ = None
    for d in sorted(calls):
        d = pd.Timestamp(d)
        if open_ is not None: continue
        if last_close is not None and (d <= last_close or (d - last_close).days <= GAP): continue
        cl, det = ender(P, SP, wok, d); eps.append(det); open_ = d
        if cl is not None and cl <= TODAY: last_close = cl; open_ = None
        else: det['close'] = None; det['leg'] = None
    return eps

if __name__ == '__main__':
    X, ntail = load_weekly(); R, known = load_rate(); SP = load_sp(); wok = witness(known); P = paths(X)
    st = json.load(open(os.path.join(OUT, 'c1021_state.json')))
    calls = [pd.Timestamp(c['day']) for c in st['calls']]
    eps = chronology(calls, P, SP, wok)
    say('episodes: ' + '; '.join('%s -> %s (%s)' % (e['open'], e['close'] or 'OPEN', e['leg'] or '-') for e in eps))
    cur = eps[-1] if eps else None
    state = dict(tool='E22', version='E22 (1031)', built='', today=str(TODAY.date()),
                 episodes=eps, standing=('in recession since %s' % cur['open']) if (cur and cur['close'] is None) else ('closed since %s' % (cur['close'] if cur else '-')),
                 inputs=dict(iu_newest_week=str(X.index[X.iu_rtsa.notna()].max().date()), iu_live_weeks=ntail, rate_month=str(R.index.max().date())[:7], rate=float(R.iloc[-1]),
                             rate_below_year_ago=bool(known[-1][1]), sp_day=str(SP.index[-1].date()), sp=float(SP.iloc[-1])), log=LOG)
    state['built'] = str(dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None)) + 'Z'
    if cur: state['current'] = cur
    _iu = P['IU4'][-1]; _open = cur is not None and cur['close'] is None
    _sp_since = SP[SP.index > pd.Timestamp(cur['open'])] if _open else None
    state['values'] = dict(iu4=dict(value=round(_iu[1], 1), release=str(pd.Timestamp(_iu[0]).date()), week=str(X.index[X.iu_rtsa.notna()].max().date())),
                           rate=dict(month=str(R.index.max().date())[:7], value=float(R.iloc[-1]), year_earlier=float(R.shift(12).iloc[-1]), diff=round(float(R.iloc[-1] - R.shift(12).iloc[-1]), 2)),
                           sp=dict(day=str(SP.index[-1].date()), close=float(SP.iloc[-1]), ratio_to_low_since_open=(round(float(_sp_since.iloc[-1] / _sp_since.min()), 3) if (_open and len(_sp_since)) else None)),
                           episode_open=_open)
    json.dump(state, open(os.path.join(OUT, 'e22_state.json'), 'w'), indent=1, default=str)
    os.makedirs(os.path.join(W, 'cache', 'e22'), exist_ok=True)
    rd = pd.DataFrame(READING, columns=['day', 'reading']).drop_duplicates('day', keep='last').sort_values('day')
    rd.to_csv(os.path.join(W, 'cache', 'e22', 'closing_daily.csv'), index=False)
    say('closing reading: %d days, latest %s' % (len(rd), (str(rd.day.iloc[-1].date()) + ' %.2f' % rd.reading.iloc[-1]) if len(rd) else '-'))
    say('standing:', state['standing'])
