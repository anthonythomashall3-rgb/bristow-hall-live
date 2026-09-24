#!/usr/bin/env python3
"""Can any channel call the peaks LATE in the window -- inside 45 days -- and still never fire quietly?

WHY THIS SCREEN. The standing record calls nine peaks at -35, -60, -35, -64, -76, -2, -59, -30 and -88
days. The target is everything inside two months, ideally inside one. Five walks (79, 82, 83, 84, 85)
tried to compress that by changing the OBJECTIVE -- band keys, distance keys -- and all five damaged
the record; walk 85 was decisive, refusing three legs that had been pre-screened to land in the band.
That is a negative about the objective, not about the leads.

The lever those walks never touched is the TRANSFORM HORIZON. Every screen so far has read a channel
as a six-month change, because `k = round(182 / spacing)` is hard-coded in `as_of`. A six-month change
crosses a high quantile when the downturn is six months old; a three-month change answers a different
question at a different moment. Whether that lands calls later or merely noisier is an empirical
question, and this is the screen that asks it: horizons of three, six and nine months, scored on the
tight window [-45, -1] as well as the standing [-92, -1].

WHAT IT DOES NOT DO. It does not change the bar. Zero quiet firings over 1946-2026, the 1965-68 credit
crunch scored like any other stretch, recession indicators excluded at entry. A channel that lands in
the tight window by firing constantly is not admitted, which is the whole difficulty: a call at -1 day
and a call that is late are separated by one day, and the screen must find channels that stop on the
right side of it without being tuned to.
"""
import os, re, sys, json, time, itertools, warnings, collections
import numpy as np, pandas as pd, multiprocessing as mp
warnings.filterwarnings('ignore')

_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(ROOT, '186_realtime_channels_2026-09-15')
VDIR = os.path.join(HERE, 'vintages')
OUT = os.path.join(ROOT, '187_null_control_2026-09-16', 'out')
os.makedirs(OUT, exist_ok=True)
FOLDERS = [os.path.join(HERE, 'data'), os.path.join(HERE, 'data_highfreq'), os.path.join(HERE, 'data_nber'),
           os.path.join(ROOT, '183_transmission_channels_2026-09-15', 'data'),
           os.path.join(ROOT, '182_channel_coverage_2026-09-15', 'data')]
FP2 = os.path.join(ROOT, '187_null_control_2026-09-16', 'out', 'fp2')
LEAK = re.compile(r'^(USREC|RECPRO|JHDUSRGDPBR|USARECD|NBERREC|CANREC|.*RECD[MPQ]$)', re.I)
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))
IDX = pd.date_range('1946-01-31', max(pd.Timestamp('2026-09-30'), pd.Timestamp.today().normalize() + pd.Timedelta(days=45)), freq='D')   # 17 Sep 2026: runs past today (was fixed at 2026-09-30, after which the live high-frequency legs could not have fired); beyond the last datum the states are their ffill, so no proposal can appear after the data
NIDX = len(IDX); D0 = IDX[0]
PK_POS = [(int((p - D0).days), p.strftime('%Y-%m')) for p in PK]
INSIDE = np.zeros(NIDX, bool)
for _p, _r in zip(PK, TR):
    _i = max(0, int((_p - D0).days)); _j = min(NIDX - 1, int((_r - D0).days))
    if _j >= _i: INSIDE[_i:_j + 1] = True
CR_LO, CR_HI = int((CRUNCH[0] - D0).days), int((CRUNCH[1] - D0).days)

def hold_np(a, d):
    a = np.asarray(a, bool); idx = np.arange(a.size)
    last = np.maximum.accumulate(np.where(a, idx, -1))
    return (last >= 0) & ((idx - last) < d)
def daily_np(b):
    if len(b) == 0: return np.zeros(NIDX, bool)
    pos = np.searchsorted(np.asarray(b.index.values), np.asarray(IDX.values), side='right') - 1
    bv = np.asarray(b.values).astype(bool); out = np.zeros(NIDX, bool); ok = pos >= 0
    out[ok] = bv[pos[ok]]; return out
def episodes_np(a, minexp=9):
    a = np.asarray(a, bool); tp = np.flatnonzero(a); fp_ = np.flatnonzero(~a)
    gap = minexp * 30; out, i = [], 0
    while True:
        k = np.searchsorted(tp, i)
        if k >= tp.size: break
        c = int(tp[k]); out.append(c)
        j = np.searchsorted(fp_, c + gap)
        if j >= fp_.size: break
        i = int(fp_[j]) + 1
    return out
def score(calls):
    a = np.asarray(calls, dtype=np.int64)
    used, leads = set(), {}
    for pp, key in PK_POS:
        j = int(np.searchsorted(a, pp, side='right')) - 1
        if j >= 0 and a[j] >= pp - 400:
            t = int(a[j]); leads[key] = t - pp; used.add(t)
    quiet = [t for t in a.tolist() if t not in used and not INSIDE[t]]
    crunch = [t for t in quiet if CR_LO <= t <= CR_HI]
    tight = {k: v for k, v in leads.items() if -45 <= v <= -1}
    wide = {k: v for k, v in leads.items() if -92 <= v <= -1}
    return len(a), len(quiet), len(crunch), tight, wide, leads

_RD, _FP = {}, {}
def rd_any(sid):
    if sid in _RD: return _RD[sid]
    s = None
    for f in FOLDERS:
        p = os.path.join(f, sid + '.csv')
        if not os.path.exists(p): continue
        try: q = pd.read_csv(p)
        except Exception: break
        c = list(q.columns)
        if len(c) < 2: break
        try:
            s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                          index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
            s = s[~s.index.duplicated(keep='last')]
        except Exception: s = None
        break
    if len(_RD) > 400: _RD.clear()
    _RD[sid] = s; return s
def fp(sid):
    if sid in _FP: return _FP[sid]
    out = (None, None)
    for d in (FP2, VDIR):
        p = os.path.join(d, sid + '_firstprint.csv')
        if not os.path.exists(p): continue
        try: q = pd.read_csv(p)
        except Exception: break
        dd = pd.to_datetime(q['date'], errors='coerce'); pb = pd.to_datetime(q['published'], errors='coerce')
        v = pd.to_numeric(q['value'], errors='coerce'); k = dd.notna() & pb.notna() & v.notna()
        s = pd.Series(v[k].values, index=dd[k]).sort_index(); b = pd.Series(pb[k].values, index=dd[k]).sort_index()
        out = (s[~s.index.duplicated(keep='first')], b[~b.index.duplicated(keep='first')]); break
    if len(_FP) > 400: _FP.clear()
    _FP[sid] = out; return out
def spacing(s):
    return float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))) if len(s) > 8 else 30.0
def lag_for(sp): return 1 if sp <= 3 else (12 if sp <= 10 else (40 if sp <= 45 else 120))
def as_of(sid, fn, horizon):
    """horizon in days: the change interval the channel is read over. 182 is every prior screen's value."""
    s, pb = fp(sid)
    if s is not None and len(s) > 60:
        sp = spacing(s); k = max(1, int(round(horizon / max(sp, 1))))
        x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
        a = pd.to_datetime(pb.reindex(x.index), errors='coerce'); m = a.notna().values
        if int(m.sum()) > 60:
            y = pd.Series(x.values[m], index=pd.DatetimeIndex(a.values[m])).sort_index()
            return y[~y.index.duplicated(keep='first')], max(1, int(round(365.0 / max(sp, 1)))), 'firstprint'
    s = rd_any(sid)
    if s is None or len(s) < 60: return None, None, None
    sp = spacing(s); k = max(1, int(round(horizon / max(sp, 1))))
    x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 60: return None, None, None
    x = x.copy(); x.index = x.index + pd.Timedelta(days=lag_for(sp))
    return x, max(1, int(round(365.0 / max(sp, 1)))), 'current+lag'
def over_q(x, q, win):
    ln = x.shift(1).rolling(win, min_periods=max(10, win // 2)).quantile(q / 100.0)
    return (x > ln) & ln.notna()

HORIZONS = (91, 182, 273)
DIRS = {'rise': lambda s, k: s.diff(k), 'fall': lambda s, k: -s.diff(k),
        'pct_up': lambda s, k: s.pct_change(k) * 100, 'pct_down': lambda s, k: -s.pct_change(k) * 100}
CONFS = {
 'ip_falling':      ('INDPRO', lambda s, k: -s.pct_change(k) * 100),
 'hours_falling':   ('AWHMAN', lambda s, k: -s.diff(k)),
 'mfg_emp_falling': ('MANEMP', lambda s, k: -s.pct_change(k) * 100),
 'unrate_rising':   ('UNRATE', lambda s, k: s.diff(k)),
 'starts_falling':  ('HOUST',  lambda s, k: -s.pct_change(k) * 100),
 'overtime_falling':('AWOTMAN', lambda s, k: -s.diff(k)),
 'layoff_rate_rising': ('M0852BUSM497NNBR', lambda s, k: s.diff(k)),
 'freight_cars_falling': ('M03002USM544NNBR', lambda s, k: -s.pct_change(k) * 100),
}
CB = None
def init():
    global CB
    CB = {}
    for cn, (sid, fn) in CONFS.items():
        for ch in HORIZONS:
            x, ny, how = as_of(sid, fn, ch)
            if x is None: continue
            for cq in (90, 95):
                for chold in (135, 270):
                    CB[(cn, ch, cq, chold)] = hold_np(daily_np(over_q(x, cq, max(12, int(10 * ny)))), chold)

# Which window admits a configuration. The tight window is what this screen was written for, but the
# legs already in the system were chosen on the standing [-92, -1] window, and several of their real
# calls (-86, -88) lie outside [-45, -1] entirely. Testing them on the tight window would ask whether
# they do something they were never chosen to do, and answer no. WINDOW=wide asks the right question.
ADMIT = os.environ.get('WINDOW', 'tight')

def one(sid):
    out = []
    for ph in HORIZONS:
        for dname, dfn in DIRS.items():
            x, ny, how = as_of(sid, dfn, ph)
            if x is None: continue
            for pq, pwy, phold in itertools.product((95, 97), (10, 20), (90, 180)):
                Pb = hold_np(daily_np(over_q(x, pq, max(12, int(pwy * ny)))), phold)
                for (cn, ch, cq, chold), Cb in CB.items():
                    n, nq, nc, tight, wide, leads = score(episodes_np(Pb & Cb))
                    admit = tight if ADMIT == 'tight' else wide
                    if nq == 0 and len(admit) > 0:
                        out.append(dict(proposer=sid, p_horizon=ph, direction=dname, p_read=how, p_q=pq,
                                        p_win=pwy, p_hold=phold, confirmer=cn, c_horizon=ch, c_q=cq,
                                        c_hold=chold, n_fire=n, n_quiet=nq, n_crunch=nc,
                                        n_tight=len(tight), n_wide=len(wide),
                                        tight=json.dumps(admit), wide=json.dumps(wide),
                                        all_leads=json.dumps(leads)))
    return out

def candidates():
    conf_ids = {v[0] for v in CONFS.values()}
    seen, cand = set(), []
    for f in FOLDERS:
        if not os.path.isdir(f): continue
        for fn_ in sorted(os.listdir(f)):
            if not fn_.endswith('.csv') or fn_.startswith('MANIFEST'): continue
            sid = fn_[:-4]
            if sid in seen or sid in conf_ids or LEAK.match(sid): continue
            seen.add(sid); cand.append(sid)
    return cand

if __name__ == '__main__':
    cand = candidates()
    part = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    nparts = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    cand = cand[part::nparts]
    ncpu = max(1, (os.cpu_count() or 4) - 1)
    print('candidates %d (part %d of %d), workers %d' % (len(cand), part, nparts, ncpu), flush=True)
    t0 = time.time(); rows = []
    with mp.Pool(ncpu, initializer=init) as pool:
        for i, res in enumerate(pool.imap_unordered(one, cand, chunksize=4)):
            rows += res
            if (i + 1) % 250 == 0:
                print('  %d/%d, %d admissible, %.1f min' % (i + 1, len(cand), len(rows),
                                                            (time.time() - t0) / 60), flush=True)
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, 'late_screen_part%d.csv' % part), index=False)
    per = collections.Counter()
    for r in rows:
        for p in json.loads(r['tight']): per[p] += 1
    print('\ndone %.1f min. admissible %d over %d channels' % ((time.time() - t0) / 60, len(D),
                                                               D.proposer.nunique() if len(D) else 0))
    print('peaks reached INSIDE 45 days: %s' % dict(sorted(per.items())))
