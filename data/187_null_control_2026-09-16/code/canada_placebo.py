#!/usr/bin/env python3
"""How many Canadian configurations would clear the same bar against a chronology that is WRONG?

WHY THIS HAS TO BE RUN. The Canadian screen returned 1,758 admissible configurations over 297
channels. That number means nothing on its own: 1,109 channels x 4 directions x 8 proposer settings x
12 confirmer settings is about 425,000 conjunctions, and a bar of "no quiet firings, at least one call
1-92 days before a peak" will be cleared by some of them by luck. The cover the selector built says so
out loud -- it reaches 2008 and 2020 through POULTRY PRODUCTION and 1974 through New York Stock
Exchange customer debit balances. Those are not mechanisms.

THE CONTROL. Run the identical screen against chronologies that are deliberately false: the C.D. Howe
peaks shifted whole by a fixed number of years. A shifted chronology has the same number of peaks, the
same spacing and the same in-sample span, so it is the same multiple-comparisons problem with the
economics removed. If a false chronology draws about as many admissible configurations as the true
one, the screen is counting luck; if it draws far fewer, the surplus on the true chronology is the
part worth keeping.

The shift is applied to peaks AND troughs together so the in-recession mask moves with them, and
shifts are chosen to avoid landing on a true peak.
"""
import os, sys, json, itertools, warnings, numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canada_screen as C
from fastscreen import hold_np, daily_np
warnings.filterwarnings('ignore')

SHIFTS = [int(z) for z in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['4', '7', '-5', '11'])]

def build(shift_years):
    pk = [p + pd.DateOffset(years=shift_years) for p in C.PK]
    tr = [t + pd.DateOffset(years=shift_years) for t in C.TR]
    pk = [pd.Timestamp(x) + pd.offsets.MonthEnd(0) for x in pk]
    tr = [pd.Timestamp(x) + pd.offsets.MonthEnd(0) for x in tr]
    return pk, tr

def install(pk, tr):
    C.PK, C.TR = pk, tr
    def inside(t): return any(p <= t <= r for p, r in zip(pk, tr))
    C.inside = inside
    def score(calls):
        used, leads = set(), {}
        for p in pk:
            c = [t for t in calls if 0 <= (p - t).days <= 400]
            if c: t = max(c); leads[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
        quiet = [t for t in calls if t not in used and not inside(t)]
        inwin = {k: v for k, v in leads.items() if -92 <= v <= -1}
        return (len(calls), len(leads), len(inwin), len(quiet), 0, json.dumps(inwin), json.dumps(leads))
    C.score = score

_SH = 0
def _init():
    pk, tr = build(_SH); install(pk, tr); C.init()

def run(shift):
    global _SH
    _SH = shift
    pk, tr = build(shift); install(pk, tr)
    rows = []
    with mp.Pool(max(1, os.cpu_count() or 2), initializer=_worker_init, initargs=(shift,)) as pool:
        for res in pool.imap_unordered(C.one, CAND, chunksize=8): rows += res
    peaks = collections_count(rows)
    return len(rows), len({r['proposer'] for r in rows}), peaks

def _worker_init(shift):
    pk, tr = build(shift); install(pk, tr); C.init()

def collections_count(rows):
    import collections
    c = collections.Counter()
    for r in rows:
        for p in json.loads(r['inwindow']): c[p] += 1
    return dict(sorted(c.items()))

if __name__ == '__main__':
    conf_ids = {v[0] for v in C.CONFS.values()}
    seen = []; s = set()
    for f in C.FOLDERS:
        if not os.path.isdir(f): continue
        for fn_ in sorted(os.listdir(f)):
            if not fn_.endswith('.csv') or fn_.startswith('MANIFEST'): continue
            sid = fn_[:-4]
            if sid in s or sid in conf_ids or C.LEAK.match(sid): continue
            s.add(sid); seen.append(sid)
    CAND = seen; C.CAND = seen
    print('candidates %d' % len(CAND), flush=True)
    print('%-8s %10s %10s' % ('shift', 'configs', 'channels'), flush=True)
    print('%-8s %10d %10d   (true chronology, from canada_screen.csv)'
          % ('0', len(pd.read_csv(os.path.join(C.OUT, 'canada_screen.csv'))),
             pd.read_csv(os.path.join(C.OUT, 'canada_screen.csv')).proposer.nunique()), flush=True)
    res = []
    for sh in SHIFTS:
        n, ch, per = run(sh)
        res.append((sh, n, ch, per))
        print('%-8s %10d %10d   %s' % ('%+dy' % sh, n, ch, per), flush=True)
    pd.DataFrame(res, columns=['shift_years', 'n_configs', 'n_channels', 'per_peak']).to_csv(
        os.path.join(C.OUT, 'canada_placebo.csv'), index=False)
