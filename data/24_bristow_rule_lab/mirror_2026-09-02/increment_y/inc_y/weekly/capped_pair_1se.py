"""SELECTION WITH A SAFETY-FIRST TIE-BREAK (4 September 2026) - the standard 'one standard error' rule, and what
it does to the folds.

On the fine grid 2,569 settings are admissible and the twelve leave-one-out folds split nine to one to one to one.
They split because the fold score is SPEED ALONE, and speed is flat near its optimum: dozens of settings sit within
a day or two of each other, so which one wins a fold is decided by noise.

The remedy is the standard one in model selection and it is also what Rule 21 asks for.  Instead of taking the
single fastest setting, take every setting whose kept-fold speed is within a stated TOLERANCE of the best, and
among those choose the SAFEST - the one that clears the three disturbance calls by the widest margin.  Between two
clauses that date the record equally well, the one that stays further from a false alarm is the one to ship; that
is Rule 21 written as a selection rule rather than as a gate.  The tolerance is stated before the run and the
result is reported at several tolerances so it cannot be read as chosen.

Output capped_pair_1se.log.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from collections import Counter
PK = [pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11',
                                '1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
log = open('/home/claude/lab/weekly/capped_pair_1se.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
H = pd.read_csv('/home/claude/lab/weekly/capped_pair_fine.csv')
LAG=[f'lag_{p:%Y%m}' for p in PK]; ERR=[f'err_{p:%Y%m}' for p in PK]
H['sum_lag']=H[LAG].sum(axis=1); H['sum_err']=H[ERR].abs().sum(axis=1)
base = {p:v for p,v in zip(PK,[10,51,-11,-70,31,120,30,122,51,30,126,26])}
P(f'{len(H)} admissible settings; margins {H.marg.min():+.2f} to {H.marg.max():+.2f} sd; '
  f'exposure {H.expo.min():.2f} to {H.expo.max():.2f}%; the OR {H.comb.min():.2f} to {H.comb.max():.2f}% (shipped 6.72)')
for tol in (0, 10, 20, 30, 45, 60):
    picks=[]; held={}
    for p in PK:
        k=f'lag_{p:%Y%m}'; e=f'err_{p:%Y%m}'
        s1 = H.sum_lag - H[k]; s2 = H.sum_err - H[e].abs()
        good = H[(s1 <= s1.min() + tol) & (s2 <= s2.min() + 1)]
        if not len(good): good = H[s1 <= s1.min() + tol]
        r = good.sort_values('marg', ascending=False).iloc[0]
        picks.append((int(r.kh),int(r.bh),int(r.ku),int(r.bu),float(r.lh),float(r.lu)))
        held[p]=(int(r[k]), int(r[e]), float(r.marg))
    c=Counter(picks)
    P(f'\ntolerance {tol:3d} days over the eleven kept recessions: distinct fold choices {len(c)}'
      + ('   EVERY FOLD THE SAME' if len(c)==1 else ''))
    for g,n in c.most_common(4):
        P(f'    housing({g[0]},{g[1]}) >= {g[4]:.1f} AND rate({g[2]},{g[3]}) >= {g[5]:.2f}   in {n} of 12 folds')
    P('    held-out: ' + '  '.join(f'{p:%Y-%m}:{held[p][0]:+d}(was {base[p]:+d})' for p in PK))
    if len(c)==1:
        g=c.most_common(1)[0][0]
        r=H[(H.kh==g[0])&(H.bh==g[1])&(H.ku==g[2])&(H.bu==g[3])&(H.lh==g[4])&(np.round(H.lu,3)==round(g[5],3))].iloc[0]
        lags=[int(r[f'lag_{p:%Y%m}']) for p in PK]; errs=[int(r[f'err_{p:%Y%m}']) for p in PK]
        P(f'    -> exposure {r.expo:.2f}%, OR {r.comb:.2f}%, margin {r.marg:+.2f} sd; median {np.median(lags):.0f} d, '
          f'worst {max(lags)}, within a month {sum(0<=v<=30 for v in lags)}/12, mae {np.mean([abs(x) for x in errs]):.2f}, other {r.other}')
        P('    -> ' + '  '.join(f'{p:%Y-%m}:{v:+d}[{e:+d}]' + (f'(was {base[p]:+d})' if v!=base[p] else '') for p,v,e in zip(PK,lags,errs)))
log.close()
