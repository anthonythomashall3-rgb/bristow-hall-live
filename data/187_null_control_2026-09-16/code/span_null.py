#!/usr/bin/env python3
"""The span-matched null: fake peaks drawn from where the channel actually has data.

THE FLAW THIS FIXES. The false-discovery test draws fake peaks uniformly across 1946-2026. A channel
that ends in 1962 cannot reach a fake peak in 1985, so it clears none of them and scores 0 of 16
whatever it measures. The hard-peak shortlist was full of exactly such channels -- NBER Macrohistory
series that stop in the 1960s -- and 33 of 75 "survived". The earlier check found only a weak
correlation between fake rate and start year, but that check was on channels that run to the present;
it did not see the end-date effect, and the end date is what bites here.

THE FIX. For each channel, the fake chronology is drawn ONLY from the months where the channel could
have had a quantile line -- from ten years after its first observation to its last observation -- and
it draws as many fake peaks as there are real peaks in that same span. The channel then faces a null
with the same number of opportunities it had on the true chronology. A channel that reaches 1953 and
1957 with data from 1919 to 1965 is now tested against fake peaks in 1929-1965, of which there are
plenty.

THE STATISTIC. Admissible configurations on the true chronology (restricted to the channel's span)
against the mean across fake chronologies. Both computed here, on this workspace's data, so the two
sides of the ratio come from the same files. The TRUE evaluation is tagged explicitly rather than
recovered by matching counts, because two chronologies can produce the same count.
"""
import os, sys, json, time, random, collections, warnings
import numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
import late_screen as L

L.FOLDERS = [os.environ.get('US_DATA', '/mnt/user-data/outputs/us')]
L.FP2 = os.environ.get('US_FP', '/mnt/user-data/outputs/fp2'); L.VDIR = L.FP2
OUT = os.environ.get('SPAN_OUT', '/mnt/user-data/outputs/span_null'); os.makedirs(OUT, exist_ok=True)
NDRAWS = int(os.environ.get('NDRAWS', '24')); SEED = int(os.environ.get('SEED', '4242'))
WORKERS = int(os.environ.get('WORKERS', '1'))
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
    return s.index.min() + pd.DateOffset(years=10), s.index.max()

def real_in_span(lo, hi):
    return [(p, r) for p, r in zip(TRUE_PK, TRUE_TR) if lo <= p <= hi]

def draw_in_span(rng, lo, hi, n):
    free = [m for m, ok in zip(ALLM, CLEAR) if ok and lo <= m <= hi]
    if len(free) < n * 3: return None
    for _ in range(4000):
        pk = sorted(rng.sample(free, n))
        if n == 1 or min((pk[i + 1] - pk[i]).days for i in range(n - 1)) >= 365:
            return pk, [min(p + pd.Timedelta(days=rng.choice(DUR)), L.IDX[-1]) for p in pk]
    return None

def _score_one(args):
    """One (channel, chronology, tag) evaluation; the chronology is installed inside the worker."""
    sid, pk, tr, tag = args
    install(pk, tr); L.init()
    rows = L.one(sid)
    return sid, tag, len(rows), sorted({p for r in rows for p in json.loads(r['tight'])})

if __name__ == '__main__':
    chans = [c for c in os.environ.get('CHANS', '').split(',') if c]
    if not chans:
        raise SystemExit('CHANS required')
    rng = random.Random(SEED)
    jobs, meta = [], {}
    for sid in chans:
        sp = span_of(sid)
        if sp is None: continue
        lo, hi = sp
        real = real_in_span(lo, hi)
        if not real: continue
        meta[sid] = dict(lo=lo, hi=hi, n_real=len(real))
        jobs.append((sid, [p for p, _ in real], [r for _, r in real], 'TRUE'))
        for d in range(NDRAWS):
            dr = draw_in_span(rng, lo, hi, len(real))
            if dr: jobs.append((sid, dr[0], dr[1], 'fake'))
    print('span-matched null: %d channels, %d evaluations, %d workers' % (len(meta), len(jobs), WORKERS), flush=True)
    t0 = time.time(); res = collections.defaultdict(list); true_map = {}
    with mp.Pool(WORKERS) as pool:
        for i, (sid, tag, n, peaks) in enumerate(pool.imap_unordered(_score_one, jobs, chunksize=1)):
            if tag == 'TRUE': true_map[sid] = (n, peaks)
            else: res[sid].append(n)
            if (i + 1) % 50 == 0: print('  %d/%d, %.1f min' % (i + 1, len(jobs), (time.time() - t0) / 60), flush=True)
    rows = []
    for sid in meta:
        t_n, t_pk = true_map.get(sid, (0, []))
        f = np.array(res[sid], float)
        rows.append(dict(channel=sid, span_from=meta[sid]['lo'].date(), span_to=meta[sid]['hi'].date(),
                         real_peaks_in_span=meta[sid]['n_real'], true_cfg=t_n,
                         true_peaks=' '.join(x[:4] for x in t_pk),
                         fake_mean=f.mean() if len(f) else np.nan, fake_max=int(f.max()) if len(f) else 0,
                         n_fake=len(f),
                         ratio=(t_n / f.mean()) if len(f) and f.mean() > 0 else (float('inf') if t_n else 0.0),
                         p_exceed=float((f >= t_n).mean()) if len(f) else np.nan))
    D = pd.DataFrame(rows).sort_values(['p_exceed', 'ratio'], ascending=[True, False])
    D.to_csv(os.path.join(OUT, 'span_null.csv'), index=False)
    pd.set_option('display.width', 220)
    print(D.to_string(index=False))
