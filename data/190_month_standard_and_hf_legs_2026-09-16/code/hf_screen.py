#!/usr/bin/env python3
"""THE HIGH-FREQUENCY TRANSMISSION SCREEN (16 September 2026). Declared before running.

Question: can a daily or weekly, never-revised transmission object -- payments (Treasury withheld taxes, UI benefits
paid, customs duties), physical activity (electricity demand, TSA throughput, petroleum products supplied), plumbing
(OFR stress index), hiring (Indeed postings), credit cost (30-year mortgage rate), attention (EPU, GPR), equity tail
(SKEW, VVIX) -- be a leg in the episode form the rule already uses (proposer held open x causally different confirmer
held open), admitted only with ZERO quiet firings over its whole span and at least one call inside [-92, -1] days
of a peak-month end?

What differs from the 187 screen, and why (each declared here, none tuned after seeing results):
  1. the same engine (187_null_control/code/late_screen.py), FOLDERS pointed at this collection's data;
  2. the rolling window of the quantile line is 3, 5 or 10 YEARS (the 187 screen used 10 and 20) because these
     histories begin in 1990-2020; the window is part of the configuration and is reported;
  3. a year-over-year horizon (365 days) is added to 91/182/273, because daily payment and travel flows carry a
     calendar that only the same calendar a year earlier cancels;
  4. spacing = MEAN spacing over the last two years (business-daily series have median 1 and mean 1.4), so that
     "91 days" means 91 calendar days for every series;
  5. publication lag charged per source instead of the generic 1/12/40: DTS next business day (1), TSA next day
     (1), EIA-930 next day (1), OFR next business day (2), Indeed three days (3), EIA weekly petroleum five days
     (Wednesday after the Friday week, 5), Freddie PMMS (1), EPU/GPR (1), Cboe (1);
  6. four extra confirmers, causally different from the proposers they will be paired with and themselves daily or
     weekly: withheld taxes falling (65-day sum, yoy), UI benefits paid rising (20-day sum), petroleum products
     supplied falling (4-week mean), and the standard eight monthly confirmers of the 187 screen.
Admission is on the wide window [-92, -1]; every matched firing must be inside it (no firing 93-400 days before a
peak) -- the 187 strict filter (late_full_strict92) applied at entry.
Run:  python3 hf_screen.py  [workers]"""
import os, sys, json, time, itertools, collections, warnings
import numpy as np, pandas as pd, multiprocessing as mp
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
sys.path.insert(0, os.path.join(ROOT, '187_null_control_2026-09-16', 'code'))
import late_screen as L
HERE = os.path.join(ROOT, '190_month_standard_and_hf_legs_2026-09-16')
DATA = os.path.join(HERE, 'data'); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
L.FOLDERS = [DATA] + L.FOLDERS
L.HORIZONS = (91, 182, 273, 365)
LAG = {'DTS': 1, 'UIB': 1, 'TSA': 1, 'EIA930': 1, 'OFR': 2, 'INDEED': 3, 'EIAW': 5, 'PMMS': 1, 'EPU': 1, 'GPR': 1, 'SKEW': 1, 'VVIX': 1}
def lag_of(sid):
    for k, v in LAG.items():
        if sid.startswith(k): return v
    return None
def spacing(s):
    if len(s) < 9: return 30.0
    t = s.index[s.index >= s.index.max() - pd.Timedelta(days=730)]
    if len(t) < 9: t = s.index
    return float((t.max() - t.min()).days) / max(1, len(t) - 1)
L.spacing = spacing
_orig_lag = L.lag_for
def as_of(sid, fn, horizon):
    s, pb = L.fp(sid)
    if s is not None and len(s) > 60:
        return L.as_of.__wrapped__(sid, fn, horizon) if hasattr(L.as_of, '__wrapped__') else _asof_fp(sid, fn, horizon)
    s = L.rd_any(sid)
    if s is None or len(s) < 60: return None, None, None
    sp = spacing(s); k = max(1, int(round(horizon / max(sp, 1))))
    x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 60: return None, None, None
    lag = lag_of(sid); lag = _orig_lag(sp) if lag is None else lag
    x = x.copy(); x.index = x.index + pd.Timedelta(days=lag)
    return x, max(1, int(round(365.0 / max(sp, 1)))), 'current+lag%d' % lag
def _asof_fp(sid, fn, horizon):
    s, pb = L.fp(sid); sp = spacing(s); k = max(1, int(round(horizon / max(sp, 1))))
    x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
    a = pd.to_datetime(pb.reindex(x.index), errors='coerce'); m = a.notna().values
    if int(m.sum()) > 60:
        y = pd.Series(x.values[m], index=pd.DatetimeIndex(a.values[m])).sort_index()
        return y[~y.index.duplicated(keep='first')], max(1, int(round(365.0 / max(sp, 1)))), 'firstprint'
    return None, None, None
L.as_of = as_of
L.CONFS = dict(L.CONFS)
L.CONFS.update({
 'withheld_falling':  ('DTSWITHHELD_S65', lambda s, k: -s.pct_change(k) * 100),
 'ui_benefits_rising': ('UIBENEFITS_S20', lambda s, k: s.pct_change(k) * 100),
 'petroleum_falling': ('EIAWRPUPUS2_M4', lambda s, k: -s.pct_change(k) * 100),
})
WINDOWS = (3, 5, 10)
def one(sid):
    out = []
    for ph in L.HORIZONS:
        for dname, dfn in L.DIRS.items():
            x, ny, how = L.as_of(sid, dfn, ph)
            if x is None: continue
            for pq, pwy, phold in itertools.product((95, 97), WINDOWS, (90, 180)):
                Pb = L.hold_np(L.daily_np(L.over_q(x, pq, max(12, int(pwy * ny)))), phold)
                for (cn, ch, cq, chold), Cb in L.CB.items():
                    n, nq, nc, tight, wide, leads = L.score(L.episodes_np(Pb & Cb))
                    if nq == 0 and len(wide) > 0 and all(-92 <= v <= -1 for v in leads.values()):
                        out.append(dict(proposer=sid, p_horizon=ph, direction=dname, p_read=how, p_q=pq, p_win=pwy, p_hold=phold,
                                        confirmer=cn, c_horizon=ch, c_q=cq, c_hold=chold, n_fire=n, n_quiet=nq,
                                        n_wide=len(wide), wide=json.dumps(wide), all_leads=json.dumps(leads)))
    return out
def init(): L.init()
CONF_IDS = {v[0] for v in L.CONFS.values()}
if __name__ == '__main__':
    cand = [f[:-4] for f in sorted(os.listdir(DATA)) if f.endswith('.csv') and f[:-4] not in CONF_IDS]
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 2)
    print('candidates', len(cand), cand, 'workers', nw, flush=True)
    t0 = time.time(); rows = []
    with mp.Pool(nw, initializer=init) as pool:
        for i, res in enumerate(pool.imap_unordered(one, cand, chunksize=1)):
            rows += res; print('  %d/%d done, %d admissible, %.1f min' % (i + 1, len(cand), len(rows), (time.time() - t0) / 60), flush=True)
    D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, 'hf_screen.csv'), index=False)
    per = collections.Counter()
    for r in rows:
        for p in json.loads(r['wide']): per[p] += 1
    print('done %.1f min; admissible %d over %d channels' % ((time.time() - t0) / 60, len(D), D.proposer.nunique() if len(D) else 0))
    print('peaks reached in window:', dict(sorted(per.items())))
    if len(D):
        g = D.groupby('proposer').agg(configs=('n_wide', 'size'), max_peaks=('n_wide', 'max')).sort_values('configs', ascending=False)
        print(g.to_string())
