#!/usr/bin/env python3
"""The null control for the tight-window screen, whose grid is eighteen times larger.

WHY IT IS MANDATORY HERE. The standard screen tests 512 conjunctions per channel and its null showed
that at five of eleven scored peaks the admissible counts are indistinguishable from randomly placed
fake peaks. The tight-window screen tests 9,216 per channel -- three proposer horizons, four
directions, eight proposer settings, ninety-six confirmer settings. Eighteen times the search means
eighteen times the chance that a channel clears the bar by luck, so the count of configurations
reaching a peak inside 45 days means nothing at all until this has been run.

SAMPLED, AND THE SAME SAMPLE THROUGHOUT. A single chronology over the whole pool is about three hours
on two cores at this grid size, so the null runs on a fixed random sample of channels, drawn once and
used for the true chronology and every draw. The comparison is then between chronologies, not between
channel sets, which is the only thing it needs to be.
"""
import os, sys, json, time, random, collections, warnings
import numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
import late_screen as L

L.FOLDERS = [os.environ.get('US_DATA', '/mnt/user-data/outputs/us')]
L.FP2 = os.environ.get('US_FP', '/mnt/user-data/outputs/fp2')
L.VDIR = L.FP2
L.OUT = os.environ.get('LATE_OUT', '/mnt/user-data/outputs/late_out')
os.makedirs(L.OUT, exist_ok=True)

NSAMPLE = int(os.environ.get('NSAMPLE', '600'))
NDRAWS = int(os.environ.get('NDRAWS', '4'))
SEED = int(os.environ.get('SEED', '20260916'))
TRUE_PK, TRUE_TR = list(L.PK), list(L.TR)

def free_months():
    months = pd.date_range(pd.Timestamp('1946-06-30'), pd.Timestamp('2026-06-30'), freq='ME')
    bad = np.zeros(len(months), bool)
    for p, r in zip(TRUE_PK, TRUE_TR):
        bad |= ((months >= p - pd.Timedelta(days=365)) & (months <= r + pd.Timedelta(days=365)))
    return list(months[~bad])
FREE = free_months()
DUR = [int((r - p).days) for p, r in zip(TRUE_PK, TRUE_TR)]

def draw(rng, npk):
    for _ in range(8000):
        pk = sorted(rng.sample(FREE, npk))
        if min((pk[i + 1] - pk[i]).days for i in range(npk - 1)) >= 365:
            return pk, [min(p + pd.Timedelta(days=rng.choice(DUR)), L.IDX[-1]) for p in pk]
    raise RuntimeError('no admissible fake chronology found')

def install(pk, tr):
    L.PK, L.TR = pk, tr
    L.PK_POS = [(int((p - L.D0).days), p.strftime('%Y-%m')) for p in pk]
    ins = np.zeros(L.NIDX, bool)
    for p, r in zip(pk, tr):
        i = max(0, int((p - L.D0).days)); j = min(L.NIDX - 1, int((r - L.D0).days))
        if j >= i: ins[i:j + 1] = True
    L.INSIDE = ins

def _pool_init(pktr, folders, fp2):
    L.FOLDERS = folders; L.FP2 = fp2; L.VDIR = fp2
    install(*pktr); L.init()

def run(pk, tr, cand, tag):
    t0 = time.time(); rows = []
    with mp.Pool(max(1, os.cpu_count() or 2), initializer=_pool_init,
                 initargs=((pk, tr), L.FOLDERS, L.FP2)) as pool:
        for res in pool.imap_unordered(L.one, cand, chunksize=4): rows += res
    per = collections.Counter()
    for r in rows:
        for p in json.loads(r['tight']): per[p] += 1
    print('%-9s %7d configs, %5d channels, %.1f min  %s'
          % (tag, len(rows), len({r['proposer'] for r in rows}), (time.time() - t0) / 60,
             dict(sorted(per.items()))), flush=True)
    return rows, per

if __name__ == '__main__':
    cand_all = L.candidates()
    rng = random.Random(SEED)
    cand = sorted(rng.sample(cand_all, min(NSAMPLE, len(cand_all))))
    print('tight-window null: sample %d of %d, draws %d, workers %d'
          % (len(cand), len(cand_all), NDRAWS, os.cpu_count()), flush=True)
    rows, per_true = run(TRUE_PK, TRUE_TR, cand, 'TRUE')
    pd.DataFrame(rows).to_csv(os.path.join(L.OUT, 'late_null_true.csv'), index=False)
    allper, recs = [], []
    for d in range(NDRAWS):
        pk, tr = draw(rng, len(TRUE_PK))
        _, per = run(pk, tr, cand, 'null %d' % (d + 1))
        allper += list(per.values())
        recs.append(dict(draw=d + 1, peaks=','.join(p.strftime('%Y-%m') for p in pk),
                         n_config=sum(per.values()), per=json.dumps(dict(sorted(per.items())))))
    pd.DataFrame(recs).to_csv(os.path.join(L.OUT, 'late_null_draws.csv'), index=False)
    a = allper or [0]
    print('\nTRUE total: %d.  NULL totals: %s' % (sum(per_true.values()), [r['n_config'] for r in recs]))
    print('null per-FAKE-peak: median %.0f, 90th %.0f, max %d over %d fake peaks'
          % (float(np.median(a)), float(np.percentile(a, 90)), max(a), len(a)))
    print('\nper-peak, true against the null distribution:')
    for k, v in sorted(per_true.items()):
        print('  %-8s true %6d   above %.0f%% of fake peaks' % (k, v, 100.0 * np.mean([v > z for z in a])))
