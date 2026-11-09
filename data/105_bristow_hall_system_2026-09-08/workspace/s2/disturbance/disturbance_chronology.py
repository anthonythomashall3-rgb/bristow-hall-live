"""Bristow-Hall Disturbance Chronology (retrospective). Built 9 Nov 2026 for the BH System site.

A disturbance is a national growth-cycle contraction that did not reach the recession bar. Every number below is the
definition of record (register v3.1, rulings of 8 Nov 2026 in 00_START_HERE/RULINGS.md); nothing is fitted to episodes.

YARDSTICK  Conference Board-method composite of the four NBER coincident series: PAYEMS, INDPRO, W875RX1 (3-month centered
           mean, ruling 5), CMRMTSPL. Standardized symmetric monthly % changes, inverse-volatility weights renormalized to the
           series available each month, cumulated to an index.
TREND      Hodrick-Prescott filter on log index, lambda 133,107.94 (the OECD's monthly value). Deviation = 100 x (log - trend).
DATING     Bry-Boschan on the deviation. Union dating (floor fix, register v3.1): every window from the OECD parameters
           (window +-5, minimum phase 5, minimum cycle 15), plus every window from the measurement floor (+-2, phase 2,
           cycle 6) that passes D-D and overlaps no 5-month window.
CLASSIFY   R  Recession: the window contains an NBER recession month or Paper 1's 2024-04..2024-08 (a slowdown that runs
              into a recession with no growth-cycle expansion between is that recession's run-up, D-B).
           D-D Real: deviation fall peak to trough >= 1.0 percentage point.
           Class 1 disturbance: not R, passes D-D, and max Sahm indicator from peak to trough + 3 months < 0.50 (D-C).
           Class 2 disturbance (jobless recovery, ruling 8 Nov 2026): a window beginning within 24 months after an NBER
              trough, containing no recession month, passing D-D, with max Sahm < 1.0 and payroll employment below its
              pre-recession peak at the window's peak month. Scored against this bar, not D-C.
           Run-up: a non-recession window whose trough is followed by a recession window's peak with no expansion of at
              least the window's own minimum phase between them.
GRADE      The live site's v3.76 damage grader (damage_dimensions_live_v376.py = site s2/damage_dimensions.py, verbatim)
           on the window's own dates. No labels: the grade is the number, on the same scale as recessions.
PROVISIONAL The HP trend is two-sided, so the newest window moves as data arrive. A window is marked provisional until its
           trough is at least 24 months old. An open window is classified by the same clauses on the data so far (a window
           that contains a recession month is that recession's window, D-B) and is always provisional; an open window not yet
           1.0 pp deep is 'open_unsettled'.

Usage:  python3 disturbance_chronology.py [--data DIR | --fred [--fred-dir DIR]] [--out DIR]
        --fred downloads current FRED data (fredgraph CSV, no key) into DIR/fred_<date>/ and uses it.
Outputs: chronology.json (episodes, deviation path, vintage), chronology.csv.
"""
import argparse, datetime as dt, json, os, sys, urllib.request
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))      # live system: s2/damage_dimensions.py, the site's own grader (v3.76)
try:
    import damage_dimensions as dd
except ImportError:                             # the research folder carries a verbatim copy
    import damage_dimensions_live_v376 as dd

SERIES = ['PAYEMS', 'INDPRO', 'W875RX1', 'CMRMTSPL', 'UNRATE', 'GDPC1']
NBER = [('1948-11', '1949-10'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'),
        ('1969-12', '1970-11'), ('1973-11', '1975-03'), ('1980-01', '1980-07'), ('1981-07', '1982-11'),
        ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04')]
PAPER1 = [('2024-04', '2024-08')]          # Paper 1's 2024 recession (ruling 3)
RECESSIONS = NBER + PAPER1
LAMBDA = 133107.94
DD_MIN = 1.0      # D-D
SAHM_C1 = 0.50    # D-C
SAHM_C2 = 1.0     # class 2 bar
C2_MONTHS = 24    # class 2: begins within 24 months after an NBER trough
PROVISIONAL_MONTHS = 24


def fetch_fred(dest):
    os.makedirs(dest, exist_ok=True)
    for s in SERIES:
        with urllib.request.urlopen(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}', timeout=60) as r:
            open(os.path.join(dest, f'{s}.csv'), 'wb').write(r.read())
    return dest


def load(d, n):
    x = pd.read_csv(os.path.join(d, f'{n}.csv'))
    x.columns = ['date', 'v']
    x['date'] = pd.to_datetime(x['date'])
    x['v'] = pd.to_numeric(x['v'], errors='coerce')
    return x.dropna().set_index('date')['v']


def composite(ser):
    ser = dict(ser)
    ser['W875RX1'] = ser['W875RX1'].rolling(3, center=True).mean().dropna()
    start = pd.Timestamp('1948-01-01')
    chg = {}
    for n in ['PAYEMS', 'INDPRO', 'W875RX1', 'CMRMTSPL']:
        s = ser[n][ser[n].index >= start]
        chg[n] = (200 * (s - s.shift(1)) / (s + s.shift(1))).dropna()
    w = {n: 1 / c.std() for n, c in chg.items()}
    tot = sum(w.values()); w = {n: v / tot for n, v in w.items()}
    df = pd.DataFrame(chg)
    # the composite ends where PAYEMS and INDPRO end (the two series released first); later legs renormalize
    last = min(chg['PAYEMS'].index[-1], chg['INDPRO'].index[-1]); df = df[df.index <= last]
    avail = df.notna()
    wm = pd.DataFrame({n: avail[n] * w[n] for n in w}); wm = wm.div(wm.sum(axis=1), axis=0)
    comp = (df.fillna(0) * wm).sum(axis=1)
    lvl = [100.0]
    for c in comp.values: lvl.append(lvl[-1] * (200 + c) / (200 - c))
    idx = pd.Series(lvl[1:], index=comp.index)
    return idx, {k: round(v, 4) for k, v in w.items()}


def hp(y, lam):
    n = len(y); D = np.zeros((n - 2, n))
    for i in range(n - 2): D[i, i] = 1; D[i, i + 1] = -2; D[i, i + 2] = 1
    return pd.Series(np.linalg.solve(np.eye(n) + lam * D.T @ D, y.values), index=y.index)


def bb(x, win=5, minphase=5, mincycle=15):
    """Bry-Boschan as in growth_cycle_1024_v2.py (register v3.1), unchanged."""
    v = x.values; n = len(v); pk = []; tr_ = []
    for i in range(win, n - win):
        seg = v[i - win:i + win + 1]
        if v[i] == seg.max() and (seg == v[i]).sum() == 1: pk.append(i)
        if v[i] == seg.min() and (seg == v[i]).sum() == 1: tr_.append(i)
    tp = sorted([(i, 'P') for i in pk] + [(i, 'T') for i in tr_])
    out = []
    for i, k in tp:
        if out and out[-1][1] == k:
            j = out[-1][0]
            if (k == 'P' and v[i] > v[j]) or (k == 'T' and v[i] < v[j]): out[-1] = (i, k)
        else: out.append((i, k))
    changed = True
    while changed:
        changed = False
        for a in range(len(out) - 1):
            if out[a + 1][0] - out[a][0] < minphase:
                del out[a:a + 2]; changed = True; break
        if changed: continue
        for a in range(len(out) - 2):
            if out[a + 2][0] - out[a][0] < mincycle:
                del out[a + 1:a + 3]; changed = True; break
        b = []
        for i, k in out:
            if b and b[-1][1] == k:
                j = b[-1][0]
                if (k == 'P' and v[i] > v[j]) or (k == 'T' and v[i] < v[j]): b[-1] = (i, k)
                changed = True
            else: b.append((i, k))
        out = b
    return [(x.index[i], k) for i, k in out]


def windows(dev, win, mp, mc):
    tps = bb(dev, win, mp, mc); out = []; cur = None
    for d, k in tps:
        if k == 'P': cur = d
        elif cur is not None: out.append((cur, d)); cur = None
    if cur is not None: out.append((cur, None))
    return out, tps


M = lambda s: pd.Timestamp(s + '-01')


def overlaps(p, t, a, b):
    t = t if t is not None else pd.Timestamp('2100-01-01')
    return not (t < a or p > b)


def has_recession(p, t):
    return any(overlaps(p, t, M(a), M(b)) for a, b in RECESSIONS)


def sahm(UR):
    u3 = UR.rolling(3).mean()          # as severity_1024_v2.py (the measurements behind rulings 2 and 6)
    return u3 - u3.rolling(12).min()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=os.path.join(HERE, '..', 'data'))
    ap.add_argument('--fred', action='store_true')
    ap.add_argument('--fred-dir', default=None, help='with --fred: download here (overwritten each run) instead of OUT/fred_<date>')
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'out'))
    a = ap.parse_args()
    data = fetch_fred(a.fred_dir or os.path.join(a.out, 'fred_' + dt.date.today().isoformat())) if a.fred else a.data
    ser = {n: load(data, n) for n in SERIES}
    idx, weights = composite(ser)
    ly = np.log(idx); tr = hp(ly, LAMBDA); dev = 100 * (ly - tr)
    UR, IP, G, PAY = ser['UNRATE'], ser['INDPRO'], ser['GDPC1'], ser['PAYEMS']
    SA = sahm(UR)
    last = dev.index[-1]

    w5, tp5 = windows(dev, 5, 5, 15)
    w2, tp2 = windows(dev, 2, 2, 6)
    fall = lambda p, t: float(dev[p] - (dev[t] if t is not None else dev[p:].min()))
    cand = [(p, t, 5) for p, t in w5]
    for p, t in w2:
        if not any(overlaps(p, t, q, (s if s is not None else last)) for q, s, _ in cand if _ == 5) and fall(p, t) >= DD_MIN:
            cand.append((p, t, 2))
    def class2(p, t):
        """Class 2 as written (ruling 8 Nov 2026): begins within 24 months after an NBER trough; no recession month inside;
        passes D-D; the Sahm indicator RISES AGAIN but stays < 1.0 (re-rise = highest Sahm reading after its lowest point
        inside peak..trough+3, so the recession's own residual is not counted); payroll employment below its pre-recession
        peak (highest level in the 12 months to the NBER peak month) in every month from peak to trough."""
        te = t if t is not None else last
        pre_tr = [tr_ for tr_ in nber_tr if tr_ < p <= tr_ + pd.DateOffset(months=C2_MONTHS)]
        if not pre_tr or has_recession(p, t) or fall(p, t) < DD_MIN: return False, None
        trg = pre_tr[-1]; rp = M([a_ for a_, b_ in NBER if M(b_) == trg][0])
        pk = float(PAY[(PAY.index >= rp - pd.DateOffset(months=12)) & (PAY.index <= rp)].max())
        w = SA[(SA.index >= p) & (SA.index <= te + pd.DateOffset(months=3))]
        rerise = float(w[w.index >= w.idxmin()].max())
        below = bool((PAY[(PAY.index >= p) & (PAY.index <= te)] < pk).all())
        return (rerise < SAHM_C2 and below), round(rerise, 2)
    # class-2 candidates: any window (either list) beginning within 24 months after an NBER trough, no recession month inside
    nber_tr = [M(b) for _, b in NBER]
    for p, t in w5 + w2:
        if any(tr_ < p <= tr_ + pd.DateOffset(months=C2_MONTHS) for tr_ in nber_tr) and not has_recession(p, t):
            if not any(p == q for q, _, _ in cand) and class2(p, t)[0]: cand.append((p, t, 2 if (p, t) in w2 else 5))
    cand.sort(key=lambda r: r[0])

    rec_peaks = []
    for p, t, mp in cand:
        if has_recession(p, t): rec_peaks.append(p)
    rows = []
    for p, t, mp in cand:
        te = t if t is not None else last
        months = (te.year - p.year) * 12 + te.month - p.month
        f = fall(p, t)
        smax = float(SA[(SA.index >= p) & (SA.index <= te + pd.DateOffset(months=3))].max())
        c2, rerise = class2(p, t)
        rec_in = [f"{a_}..{b_}" for a_, b_ in RECESSIONS if overlaps(p, t, M(a_), M(b_))]
        if has_recession(p, t):
            # D-B: a window containing a recession month is that recession's window, open or closed
            status = 'recession'
        elif t is None and f < DD_MIN:
            # open and not yet 1.0 pp deep: nothing to classify yet
            status = 'open_unsettled'
        elif c2:
            status = 'disturbance_class2'
        elif any(rp_ > te and (rp_.year - te.year) * 12 + rp_.month - te.month < mp for rp_ in rec_peaks):
            status = 'runup'
        elif f < DD_MIN:
            status = 'fails_DD'
        elif smax >= SAHM_C1:
            status = 'labor_bar_crossed_no_recession'
        else:
            status = 'disturbance_class1'
        # grade (v3.76), labor as the site: base = lowest UR in the 12 months before the peak month
        pre = UR[(UR.index < p) & (UR.index >= p - pd.DateOffset(months=12))]; base = float(pre.min())
        seg = UR[(UR.index >= p) & (UR.index <= te)]; ex = (seg - base).clip(lower=0)
        L = dd.labour_score(float(ex.max()), float(ex.sum()))
        o = dd.output_dimension(G, p, te); q = dd.production_dimension(IP, p, te)
        prov = t is None or (last.year - t.year) * 12 + last.month - t.month < PROVISIONAL_MONTHS
        aft = {}
        if t is None and has_recession(p, t):
            # aftermath facts for an open recession window (page text): last recession month inside, the composite's high
            # after it, and payrolls against the pre-recession peak (the jobless-recovery bar)
            rs = [(M(x), M(y)) for x, y in RECESSIONS if overlaps(p, t, M(x), M(y))]; rpk, rtr = max(rs)
            after = dev[dev.index > rtr]
            ppk = float(PAY[(PAY.index >= rpk - pd.DateOffset(months=12)) & (PAY.index <= rpk)].max())
            aft = dict(rec_trough=rtr.strftime('%Y-%m'), aftermath_from=(rtr + pd.DateOffset(months=1)).strftime('%Y-%m'),
                       peak_dev=round(float(dev[p]), 4), post_high_month=after.idxmax().strftime('%Y-%m'),
                       post_high_dev=round(float(after.max()), 4),
                       fall_since_post_high=round(float(after.max() - after[after.idxmax():].min()), 2),
                       payroll_prerec_peak_k=int(ppk), payroll_latest_k=int(PAY.iloc[-1]), payroll_latest_month=PAY.index[-1].strftime('%Y-%m'),
                       payroll_ever_below_peak=bool((PAY[PAY.index >= rpk] < ppk).any()))
        rows.append(dict(**aft, peak=p.strftime('%Y-%m'), trough=t.strftime('%Y-%m') if t is not None else None,
                         open=t is None, months=months, dating='OECD 5/15' if mp == 5 else 'floor 2/6',
                         status=status, dev_fall_pp=round(f, 2), sahm_max=round(smax, 2), sahm_rerise=rerise,
                         ur_rise_pp=round(float(ex.max()), 2), ip_fall_pct=round(q['pt'], 2), gdp_fall_pct=round(o['pt'], 2),
                         L=round(L, 2), O=round(o['score'], 2), P=round(q['score'], 2),
                         grade=round(dd.grade(L, o['score'], q['score']), 2), provisional=bool(prov),
                         recession_months_inside=rec_in, passes_DD=bool(f >= DD_MIN), passes_DC=bool(smax < SAHM_C1)))
    T = pd.DataFrame(rows)
    os.makedirs(a.out, exist_ok=True)
    T.to_csv(os.path.join(a.out, 'chronology.csv'), index=False)
    path = pd.DataFrame({'date': dev.index.strftime('%Y-%m'), 'dev': dev.round(3).values})
    J = dict(built=dt.datetime.now().isoformat(timespec='seconds'), data=os.path.abspath(data),
             composite_last_month=last.strftime('%Y-%m'), weights=weights,
             series_last={n: s.index[-1].strftime('%Y-%m') for n, s in ser.items()},
             rules=dict(lambda_hp=LAMBDA, dd_min_pp=DD_MIN, sahm_class1=SAHM_C1, sahm_class2=SAHM_C2,
                        class2_months_after_trough=C2_MONTHS, provisional_months=PROVISIONAL_MONTHS),
             recessions=[dict(peak=a_, trough=b_, source='NBER' if (a_, b_) in NBER else 'Paper 1') for a_, b_ in RECESSIONS],
             episodes=rows, deviation=path.to_dict('list'))
    json.dump(J, open(os.path.join(a.out, 'chronology.json'), 'w'), indent=1)
    pd.set_option('display.width', 250)
    print(T.to_string(index=False))
    print('composite ends', last.strftime('%Y-%m'), 'weights', weights)


if __name__ == '__main__':
    main()
