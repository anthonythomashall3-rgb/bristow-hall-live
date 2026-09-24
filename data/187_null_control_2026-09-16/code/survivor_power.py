#!/usr/bin/env python3
"""The refinement the first false-discovery test needs: configurations, not just clearances.

THE WEAKNESS IN THE FIRST STATISTIC. `channel_fdr.py` records whether a channel produced ANY admissible
configuration under a fake chronology. For a channel whose best settings fire once or twice in eighty
years, that question is nearly always answered "no" — not because the channel means anything, but
because a signal that fires twice has almost no chance of landing near any peak, true or fake. The
window mass is thirteen peaks times forty-five days out of about twenty-nine thousand days, roughly
two per cent. A one-firing channel therefore scores 0 out of 16 whatever it measures, and the test has
almost no power against it.

THE FIX. Record how MANY admissible configurations each channel produces under each chronology, not
whether it produced one. A channel with 222 admissible configurations on the true chronology and a
handful on fakes is saying something; a channel with 18 on the true chronology and 9 on the average
fake is not, even if it technically "cleared" fewer fake chronologies. The ratio is the statistic, and
it is only meaningful with enough draws, so this runs the surviving shortlist alone and runs it forty
times.
"""
import os, sys, json, time, random, collections, warnings
import numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
import late_screen as L
import late_null as NU

TRUE_CSV = os.environ.get('TRUE_CSV', '/mnt/user-data/outputs/late_out/late_null_true.csv')
OUT = os.environ.get('POWER_OUT', '/mnt/user-data/outputs/late_out2')
NDRAWS = int(os.environ.get('NDRAWS', '40'))
SEED = int(os.environ.get('SEED', '2718'))
CHANS = os.environ.get('CHANS', '').split(',') if os.environ.get('CHANS') else None

if __name__ == '__main__':
    T = pd.read_csv(TRUE_CSV)
    # Accept either the raw screen output (one row per admissible configuration, column `proposer`)
    # or a pre-aggregated count table (columns `channel`, `n_cfg`).
    if 'proposer' in T.columns:
        true_cfg_map = T.groupby('proposer').size().to_dict()
    else:
        true_cfg_map = dict(zip(T['channel'], T['n_cfg']))
    if CHANS is None:
        R = pd.read_csv(os.path.join(OUT, 'channel_fdr.csv'))
        CHANS = list(R[R.fake_rate <= 0.125].channel)
    cand = sorted(set(CHANS))
    true_cfg = true_cfg_map
    print('power test: %d channels, %d fake chronologies' % (len(cand), NDRAWS), flush=True)
    rng = random.Random(SEED)
    fake_counts = collections.defaultdict(list)
    t0 = time.time()
    for d in range(NDRAWS):
        pk, tr = NU.draw(rng, len(NU.TRUE_PK))
        c = collections.Counter()
        with mp.Pool(max(1, os.cpu_count() or 2), initializer=NU._pool_init,
                     initargs=((pk, tr), L.FOLDERS, L.FP2)) as pool:
            for res in pool.imap_unordered(L.one, cand, chunksize=2):
                for r in res: c[r['proposer']] += 1
        for sid in cand: fake_counts[sid].append(c.get(sid, 0))
        if (d + 1) % 5 == 0:
            print('  draw %d/%d, %.1f min' % (d + 1, NDRAWS, (time.time() - t0) / 60), flush=True)
    rows = []
    for sid in cand:
        f = np.array(fake_counts[sid], float); t = float(true_cfg.get(sid, 0))
        rows.append(dict(channel=sid, true_cfg=int(t), fake_mean=f.mean(), fake_max=int(f.max()),
                         fake_zero_share=float((f == 0).mean()),
                         ratio=(t / f.mean()) if f.mean() > 0 else float('inf'),
                         p_exceed=float((f >= t).mean())))
    D = pd.DataFrame(rows).sort_values('p_exceed')
    D.to_csv(os.path.join(OUT, 'survivor_power.csv'), index=False)
    print('\n%-24s %8s %9s %8s %8s %9s' % ('channel', 'true', 'fake mean', 'fake max', 'ratio', 'P(fake>=true)'))
    for _, r in D.iterrows():
        print('%-24s %8d %9.1f %8d %8.1f %9.3f'
              % (r.channel[:24], r.true_cfg, r.fake_mean, r.fake_max, r.ratio, r.p_exceed))
