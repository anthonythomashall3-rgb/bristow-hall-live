#!/usr/bin/env python3
"""The null the screen has never been measured against: how many channels clear the bar by luck?

WHY A SHIFT IS THE WRONG NULL, AND THE EVIDENCE FOR SAYING SO. The first attempt at this shifted the
whole chronology by a fixed number of years. On Canadian data a -5 year shift returned 14,132
admissible configurations against the true chronology's 1,758 -- not because a false chronology is
easier, but because shifting five years lands the fake peaks INSIDE real Canadian downturns, where
every channel is already firing. A search over shifts confirms the design is unusable for the United
States: NO whole-chronology shift between -20 and +20 years keeps all thirteen fake peaks even one
year clear of a real NBER recession. American recessions are too frequent for it.

THE NULL USED HERE. Each fake chronology relocates every peak independently, drawn uniformly from the
months at least a year clear of every real recession, with real recession durations resampled for the
troughs and a minimum spacing between fake peaks. That preserves everything that makes the screen easy
-- the number of peaks, the 400-day matching window, the [-92,-1] window, the hundreds of thousands of
configurations -- and removes the only thing that should matter, which is that the peaks are where the
recessions are.

READ IT PER PEAK, NOT IN TOTAL. A total mixes a peak that thirty channels reach with one that twelve
hundred reach. What the selection of legs needs is, for each real peak, how far its admissible count
stands above what a fake peak draws.

The channel sample is drawn once and used for the true chronology and every draw, so the comparison is
between chronologies and not between channel sets.
"""
import os, sys, json, time, random, warnings, collections, numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
import us_screen_local as L
S = L.S

NSAMPLE = int(os.environ.get('NSAMPLE', '1500'))
NDRAWS = int(os.environ.get('NDRAWS', '6'))
SEED = int(os.environ.get('SEED', '20260916'))
OUT = L.OUT

def free_months():
    """Months at least one year clear of every real NBER recession, inside the scored span."""
    months = pd.date_range(pd.Timestamp('1946-06-30'), pd.Timestamp('2026-06-30'), freq='ME')
    bad = np.zeros(len(months), bool)
    for p, r in zip(L._TRUE_PK, L._TRUE_TR):
        bad |= ((months >= p - pd.Timedelta(days=365)) & (months <= r + pd.Timedelta(days=365)))
    return list(months[~bad])

FREE = free_months()
DUR = [int((r - p).days) for p, r in zip(L._TRUE_PK, L._TRUE_TR)]

def draw(rng, npk):
    for _ in range(8000):
        pk = sorted(rng.sample(FREE, npk))
        if min((pk[i + 1] - pk[i]).days for i in range(npk - 1)) >= 365:
            tr = [min(p + pd.Timedelta(days=rng.choice(DUR)), S.IDX[-1]) for p in pk]
            return pk, tr
    raise RuntimeError('no admissible fake chronology found')

def install(pk, tr):
    S.PK, S.TR = pk, tr
    n = len(S.IDX); d0 = S.IDX[0]
    pk_pos = [(int((p - d0).days), p.strftime('%Y-%m')) for p in pk]
    ins = np.zeros(n, bool)
    for p, r in zip(pk, tr):
        i = max(0, int((p - d0).days)); j = min(n - 1, int((r - d0).days))
        if j >= i: ins[i:j + 1] = True
    cr_lo, cr_hi = int((S.CRUNCH[0] - d0).days), int((S.CRUNCH[1] - d0).days)
    S.inside = lambda t: bool(ins[t]) if 0 <= t < n else False
    def score(calls):
        a = np.asarray(calls, dtype=np.int64)
        used, leads = set(), {}
        for pp, key in pk_pos:
            j = int(np.searchsorted(a, pp, side='right')) - 1
            if j >= 0 and a[j] >= pp - 400:
                t = int(a[j]); leads[key] = t - pp; used.add(t)
        quiet = [t for t in a.tolist() if t not in used and not ins[t]]
        crunch = [t for t in quiet if cr_lo <= t <= cr_hi]
        inwin = {k: v for k, v in leads.items() if -92 <= v <= -1}
        return (len(a), len(leads), len(inwin), len(quiet), len(crunch), json.dumps(inwin), json.dumps(leads))
    S.score = score

def _pool_init(pktr):
    L._apply(0); install(*pktr); S.init()

def run(pk, tr, cand, tag):
    t0 = time.time(); rows = []
    with mp.Pool(max(1, os.cpu_count() or 2), initializer=_pool_init, initargs=((pk, tr),)) as pool:
        for res in pool.imap_unordered(L.one_any, cand, chunksize=8): rows += res
    per = collections.Counter()
    for r in rows:
        for p in json.loads(r['inwindow']): per[p] += 1
    print('%-10s %6d configs, %5d channels, %.1f min  %s'
          % (tag, len(rows), len({r['proposer'] for r in rows}), (time.time() - t0) / 60,
             dict(sorted(per.items()))), flush=True)
    return rows, per

if __name__ == '__main__':
    L._apply(0)
    cand_all = L.candidates()
    rng = random.Random(SEED)
    cand = sorted(rng.sample(cand_all, min(NSAMPLE, len(cand_all))))
    print('channel sample %d of %d, draws %d, workers %d'
          % (len(cand), len(cand_all), NDRAWS, os.cpu_count()), flush=True)
    rows, per_true = run(list(L._TRUE_PK), list(L._TRUE_TR), cand, 'TRUE')
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'null_true.csv'), index=False)
    nulls = []
    for d in range(NDRAWS):
        pk, tr = draw(rng, len(L._TRUE_PK))
        _, per = run(pk, tr, cand, 'null %d' % (d + 1))
        nulls.append(dict(draw=d + 1, peaks=','.join(p.strftime('%Y-%m') for p in pk),
                          n_config=sum(per.values()), per=json.dumps(dict(sorted(per.items())))))
    N = pd.DataFrame(nulls); N.to_csv(os.path.join(OUT, 'null_draws.csv'), index=False)
    vals = [sum(json.loads(r).values()) for r in N.per]
    allper = [v for r in N.per for v in json.loads(r).values()] or [0]
    print('\nTRUE total in-window configurations: %d' % sum(per_true.values()))
    print('NULL totals per draw: %s   median %.0f, max %d' % (vals, float(np.median(vals)), max(vals)))
    print('\nnull per-FAKE-peak counts: median %.0f, 90th %.0f, max %d, over %d fake peaks'
          % (float(np.median(allper)), float(np.percentile(allper, 90)), max(allper), len(allper)))
    print('\nper-peak, true vs the null distribution:')
    for k, v in sorted(per_true.items()):
        print('  %-8s true %5d   above %.0f%% of fake peaks' % (k, v, 100.0 * np.mean([v > z for z in allper])))
