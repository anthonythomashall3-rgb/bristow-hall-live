#!/usr/bin/env python3
"""A per-channel false-discovery rate: how often does THIS channel clear the bar on a chronology that is wrong?

WHY PER CHANNEL. The pooled null answers a question about the screen as a whole -- how many
configurations clear the bar by luck. It does not answer the question leg selection actually asks,
which is about one candidate at a time: does this particular channel fire early and stay quiet because
of what it measures, or because it has enough settings to fit anything?

THE STATISTIC. Take the shortlist of channels that did best on the true chronology. Re-run only those
channels, with the identical grid, against many independently drawn fake chronologies. For each
channel, record the share of fake chronologies on which it produces at least one admissible
configuration, and how many peaks it reaches on average when it does. A channel that clears the bar on
most fake chronologies is a channel whose grid is large enough to fit noise; a channel that clears the
true chronology and almost no fake one is a candidate worth walking.

Running only the shortlist is what makes many draws affordable, and many draws is what the statistic
needs: with four draws the finest resolution available is 25%.
"""
import os, sys, json, time, random, collections, warnings
import numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
import late_screen as L
import late_null as NU

TRUE_CSV = os.environ.get('TRUE_CSV', '/mnt/user-data/outputs/late_out/late_null_true.csv')
OUT = os.environ.get('FDR_OUT', '/mnt/user-data/outputs/late_out')
TOPN = int(os.environ.get('TOPN', '40'))
NDRAWS = int(os.environ.get('NDRAWS', '24'))
SEED = int(os.environ.get('SEED', '31415'))

def shortlist(n):
    """Channels ranked by peaks reached inside the window, then by how many of their settings do it.

    PER PEAK, NOT OVERALL. Ranking by "most peaks reached" selects for flexibility, which is exactly
    what the false-discovery test is meant to expose -- the first run of this file shortlisted forty
    channels that way and the median came back clearing a wrong chronology one time in three. The hard
    peaks (1953, 1957, 1980, 1990) have few channels reaching them at all, and none of those channels
    reach many peaks, so a global ranking never sees them. So the shortlist is the union of the top
    channels FOR EACH PEAK, which guarantees every peak is represented in the test.
    """
    D = pd.read_csv(TRUE_CSV)
    D['k'] = D.tight.map(lambda s: len(json.loads(s)))
    D['peaks'] = D.tight.map(lambda s: list(json.loads(s).keys()))
    per_peak = int(os.environ.get('PER_PEAK', '12'))
    picked = []
    allpk = sorted({p for ps in D.peaks for p in ps})
    only = os.environ.get('PEAKS')                      # e.g. "1948-11,1953-07" to test the hard peaks alone
    if only: allpk = [p for p in allpk if p in only.split(',')]
    for pk in allpk:
        sub = D[D.peaks.map(lambda ps: pk in ps)]
        cnt = sub.groupby('proposer').size().sort_values(ascending=False)
        picked += list(cnt.index[:per_peak])
    g = D.groupby('proposer').agg(best_k=('k', 'max'), n_cfg=('k', 'size'))
    g = g.sort_values(['best_k', 'n_cfg'], ascending=[False, False])
    picked += list(g.index[:n])
    # PER MECHANISM. The next recession will not arrive through whichever mechanism produced the
    # most past peaks, so every mechanism with an admissible channel gets its best few tested, not
    # only the mechanisms that dominate the count. Reads channel_mechanism.csv beside TRUE_CSV.
    per_mech = int(os.environ.get('PER_MECH', '0'))
    if per_mech:
        mp_ = os.path.join(os.path.dirname(TRUE_CSV), 'channel_mechanism.csv')
        M = pd.read_csv(mp_).set_index('proposer')['mechanism'].to_dict()
        D['mech'] = D.proposer.map(M).fillna('unclassified')
        for mname, sub in D.groupby('mech'):
            cnt = sub.groupby('proposer').size().sort_values(ascending=False)
            picked += list(cnt.index[:per_mech])
    out = list(dict.fromkeys(picked))
    return out, D, g

if __name__ == '__main__':
    cand, D, g = shortlist(TOPN)
    print('shortlist %d channels, %d fake chronologies' % (len(cand), NDRAWS), flush=True)
    rng = random.Random(SEED)
    true_hit, true_k = {}, {}
    for sid in cand:
        sub = D[D.proposer == sid]
        true_hit[sid] = len(sub) > 0
        true_k[sid] = int(sub.tight.map(lambda s: len(json.loads(s))).max()) if len(sub) else 0
    hits = collections.Counter(); kcount = collections.defaultdict(list)
    t0 = time.time()
    for d in range(NDRAWS):
        pk, tr = NU.draw(rng, len(NU.TRUE_PK))
        rows = []
        with mp.Pool(int(os.environ.get('WORKERS', str(max(1, os.cpu_count() or 2)))), initializer=NU._pool_init,
                     initargs=((pk, tr), L.FOLDERS, L.FP2)) as pool:
            for res in pool.imap_unordered(L.one, cand, chunksize=2): rows += res
        seen = collections.defaultdict(int)
        for r in rows:
            seen[r['proposer']] = max(seen[r['proposer']], len(json.loads(r['tight'])))
        for sid in cand:
            if seen.get(sid, 0) > 0:
                hits[sid] += 1; kcount[sid].append(seen[sid])
        print('  draw %d/%d, %.1f min, channels clearing a FAKE chronology: %d of %d'
              % (d + 1, NDRAWS, (time.time() - t0) / 60, sum(1 for s in cand if seen.get(s, 0) > 0), len(cand)),
              flush=True)
    rows = []
    for sid in cand:
        rows.append(dict(channel=sid, true_peaks=true_k[sid], n_true_cfg=int(g.loc[sid, 'n_cfg']),
                         fake_clear=hits[sid], fake_rate=hits[sid] / float(NDRAWS),
                         fake_mean_peaks=float(np.mean(kcount[sid])) if kcount[sid] else 0.0))
    R = pd.DataFrame(rows).sort_values(['fake_rate', 'true_peaks'], ascending=[True, False])
    R.to_csv(os.path.join(OUT, 'channel_fdr.csv'), index=False)
    print('\n%-30s %6s %8s %10s %10s' % ('channel', 'peaks', 'configs', 'fake rate', 'fake peaks'))
    for _, r in R.iterrows():
        print('%-30s %6d %8d %9.0f%% %10.1f'
              % (r.channel[:30], r.true_peaks, r.n_true_cfg, 100 * r.fake_rate, r.fake_mean_peaks))
