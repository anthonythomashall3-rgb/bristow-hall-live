"""THE CONSENSUS SETTING - a selection every fold accepts (4 September 2026).

Neither the fastest-setting rule nor the safety-first tie-break makes the twelve folds pick the SAME setting: nine
or ten of twelve is the best either reaches.  But that is the wrong question to ask of a flat optimum.  What
matters is not whether every fold's ARGMAX coincides - with dozens of settings within a day of one another it
never will - but whether there is a setting that EVERY fold would accept.

So: for each fold, take the set of admissible settings whose kept-recession speed is within a stated tolerance of
that fold's best.  Intersect the twelve sets.  If the intersection is not empty, every one of the twelve folds
accepts every setting in it, and choosing the SAFEST member - the widest disturbance margin, which is Rule 21 -
is a selection no fold objects to.  That is a stronger claim than a modal vote and it is stated before it is run.

The tolerance is reported across a range so the result cannot be read as chosen, and the held-out lag of every
fold is printed beside it.

Output capped_pair_consensus.log.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
PK = [pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11',
                                '1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
log = open('/home/claude/lab/weekly/capped_pair_consensus.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
H = pd.read_csv('/home/claude/lab/weekly/capped_pair_fine.csv').reset_index(drop=True)
LAG=[f'lag_{p:%Y%m}' for p in PK]; ERR=[f'err_{p:%Y%m}' for p in PK]
H['sum_lag']=H[LAG].sum(axis=1); H['sum_err']=H[ERR].abs().sum(axis=1)
base = {p:v for p,v in zip(PK,[10,51,-11,-70,31,120,30,122,51,30,126,26])}
P(f'{len(H)} admissible settings under the symmetric window.')
for tol in (0, 5, 10, 20, 30):
    keep = None
    for p in PK:
        k=f'lag_{p:%Y%m}'; s1 = H.sum_lag - H[k]
        ok = set(H.index[s1 <= s1.min() + tol])
        keep = ok if keep is None else (keep & ok)
    P(f'\ntolerance {tol:3d} days: {len(keep)} settings accepted by ALL TWELVE folds')
    if not keep: P('    empty - no consensus at this tolerance'); continue
    sub = H.loc[sorted(keep)]
    r = sub.sort_values('marg', ascending=False).iloc[0]
    lags=[int(r[f'lag_{p:%Y%m}']) for p in PK]; errs=[int(r[f'err_{p:%Y%m}']) for p in PK]
    P(f'    the safest member: housing({int(r.kh)},{int(r.bh)}) >= {r.lh:.1f} log points AND '
      f'rate({int(r.ku)},{int(r.bu)}) >= {r.lu:.2f} points')
    P(f'      exposure {r.expo:.2f}%, the OR {r.comb:.2f}% (shipped 6.72 - UNCHANGED), margin {r.marg:+.2f} sd')
    P(f'      median {np.median(lags):.0f} d (was 30), worst {max(lags)} (was 126), within a month {sum(0<=v<=30 for v in lags)}/12, '
      f'mae {np.mean([abs(x) for x in errs]):.2f} (was 1.08), outside the thirteen {r.other}')
    P('      ' + '  '.join(f'{p:%Y-%m}:{v:+d}[{e:+d}]' + (f'(was {base[p]:+d})' if v!=base[p] else '') for p,v,e in zip(PK,lags,errs)))
    P(f'      the accepted set spans housing lines {sub.lh.min():.1f}-{sub.lh.max():.1f}, rate lines {sub.lu.min():.2f}-{sub.lu.max():.2f}, '
      f'margins {sub.marg.min():+.2f} to {sub.marg.max():+.2f} sd')
    same = all(len(set(sub[c])) == 1 for c in LAG)
    P(f'      every accepted setting gives the SAME twelve calls: {same}')
    if not same:
        for c in LAG:
            v = sorted(set(sub[c]))
            if len(v) > 1: P(f'        {c}: {v}')
log.close()
