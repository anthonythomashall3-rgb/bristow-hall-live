#!/usr/bin/env python3
"""Span-matched null for the high-frequency screen (same design as 187_null_control/code/span_null.py): for each channel,
fake peaks are drawn only from the months where the channel could have had a quantile line (three years after its
first observation, to its last observation), as many fake peaks as real peaks in that span, each fake chronology at
least a year clear of every real recession; NDRAWS fake chronologies; the statistic is the number of admissible
configurations on the true chronology against the fake mean, and P(fake >= true).
Run:  python3 hf_null.py [workers] [ndraws]"""
import os, sys, json, time, random, collections, warnings
import numpy as np, pandas as pd, multiprocessing as mp
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hf_screen as H; L = H.L
OUT = H.OUT
TRUE_PK, TRUE_TR = list(L.PK), list(L.TR)
DUR = [int((r - p).days) for p, r in zip(TRUE_PK, TRUE_TR)]
ALLM = pd.date_range(pd.Timestamp('1946-06-30'), pd.Timestamp('2026-06-30'), freq='ME')
CLEAR = np.ones(len(ALLM), bool)
for p, r in zip(TRUE_PK, TRUE_TR):
    CLEAR &= ~((ALLM >= p - pd.Timedelta(days=365)) & (ALLM <= r + pd.Timedelta(days=365)))
def install(pk, tr):
    L.PK, L.TR = pk, tr
    L.PK_POS = [(int((p - L.D0).days), p.strftime('%Y-%m')) for p in pk]
    ins = np.zeros(L.NIDX, bool)
    for p, r in zip(pk, tr):
        i = max(0, int((p - L.D0).days)); j = min(L.NIDX - 1, int((r - L.D0).days))
        if j >= i: ins[i:j + 1] = True
    L.INSIDE = ins
def span_of(sid):
    s = L.rd_any(sid)
    if s is None or len(s) < 60: return None
    return s.index.min() + pd.DateOffset(years=3), s.index.max()
def real_in_span(lo, hi): return [(p, r) for p, r in zip(TRUE_PK, TRUE_TR) if lo <= p <= hi]
def draw_in_span(rng, lo, hi, n):
    free = [m for m, ok in zip(ALLM, CLEAR) if ok and lo <= m <= hi]
    if len(free) < n * 3: return None
    for _ in range(4000):
        pk = sorted(rng.sample(free, n))
        if n == 1 or min((pk[i + 1] - pk[i]).days for i in range(n - 1)) >= 365:
            return pk, [min(p + pd.Timedelta(days=rng.choice(DUR)), L.IDX[-1]) for p in pk]
    return None
def _score_one(args):
    sid, pk, tr, tag = args
    install(pk, tr); L.init(); rows = H.one(sid)
    return sid, tag, len(rows), sorted({p for r in rows for p in json.loads(r['wide'])}), max([r['n_wide'] for r in rows] or [0])
if __name__ == '__main__':
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 5; nd = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    chans = [f[:-4] for f in sorted(os.listdir(H.DATA)) if f.endswith('.csv') and f[:-4] not in H.CONF_IDS]
    rng = random.Random(4242); jobs, meta = [], {}
    for sid in chans:
        sp = span_of(sid)
        if sp is None: continue
        lo, hi = sp; real = real_in_span(lo, hi)
        if not real: continue
        meta[sid] = dict(lo=lo, hi=hi, n_real=len(real), real=' '.join(p.strftime('%Y-%m') for p, _ in real))
        jobs.append((sid, [p for p, _ in real], [r for _, r in real], 'TRUE'))
        for d in range(nd):
            dr = draw_in_span(rng, lo, hi, len(real))
            if dr: jobs.append((sid, dr[0], dr[1], 'fake'))
    print('span-matched null: %d channels, %d evaluations, %d workers' % (len(meta), len(jobs), nw), flush=True)
    t0 = time.time(); res = collections.defaultdict(list); resmax = collections.defaultdict(list); true_map = {}
    with mp.Pool(nw) as pool:
        for i, (sid, tag, n, peaks, mx) in enumerate(pool.imap_unordered(_score_one, jobs, chunksize=2)):
            if tag == 'TRUE': true_map[sid] = (n, peaks, mx)
            else: res[sid].append(n); resmax[sid].append(mx)
            if (i + 1) % 100 == 0: print('  %d/%d, %.1f min' % (i + 1, len(jobs), (time.time() - t0) / 60), flush=True)
    rows = []
    for sid in meta:
        t_n, t_pk, t_mx = true_map.get(sid, (0, [], 0)); f = np.array(res[sid], float); fm = np.array(resmax[sid], float)
        rows.append(dict(channel=sid, span_from=meta[sid]['lo'].date(), span_to=meta[sid]['hi'].date(), real_peaks_in_span=meta[sid]['n_real'],
                         real_peaks=meta[sid]['real'], true_cfg=t_n, true_peaks=' '.join(t_pk), true_max_peaks=t_mx,
                         fake_mean=f.mean() if len(f) else np.nan, fake_max=int(f.max()) if len(f) else 0, n_fake=len(f),
                         fake_max_peaks_mean=fm.mean() if len(fm) else np.nan,
                         ratio=(t_n / f.mean()) if len(f) and f.mean() > 0 else (float('inf') if t_n else 0.0),
                         p_exceed=float((f >= t_n).mean()) if len(f) else np.nan))
    D = pd.DataFrame(rows).sort_values(['p_exceed', 'ratio'], ascending=[True, False])
    D.to_csv(os.path.join(OUT, 'hf_span_null.csv'), index=False)
    pd.set_option('display.width', 250); print(D.to_string(index=False))
