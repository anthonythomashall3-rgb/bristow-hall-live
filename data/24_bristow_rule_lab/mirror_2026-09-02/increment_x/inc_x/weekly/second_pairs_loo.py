"""LEAVE-ONE-RECESSION-OUT OVER THE CONJUNCTIVE SECOND CONDITION (4 September 2026) - Rule 18 on the pairs.

`second_pairs_all.py` produced EVERY setting that passes the four gates of memo 8aa - window exposure at or below
5.8 per cent; the OR of the whole second condition no higher than the shipped 6.72; every one of the three
disturbance calls cleared by at least +0.46 standard deviations, the margin the shipped condition itself carries,
measured on FIRST PRINTS on the tool's own window; all twelve called and no episode outside the thirteen - with
each setting's lag and date error at every peak recorded.  Selection happens HERE, and over the whole admissible
set, not over the settings that do what one hopes.

The fold's score, stated before it is run: the sum of the eleven KEPT lags, then the sum of the kept absolute
date errors, then (as a tie-break only) the wider disturbance margin.  The held-out peak is then read.

Output second_pairs_loo.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
PK = [pd.Timestamp(x) for x in ('1948-11', '1953-07', '1957-08', '1960-04', '1969-12', '1973-11',
                                '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02')]
log = open('/home/claude/lab/weekly/second_pairs_loo.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
H = pd.read_csv('/home/claude/lab/weekly/second_pairs_all.csv')
LAG = [f'lag_{p:%Y%m}' for p in PK]; ERR = [f'err_{p:%Y%m}' for p in PK]
P(f'{len(H)} admissible settings, on {H.groupby(["a","c"]).ngroups} distinct pairs of objects.')
base = dict(zip(PK, [10, 51, -11, -70, 31, 120, 30, 122, 51, 30, 126, 26]))
P('version 43: ' + '  '.join(f'{p:%Y-%m}:{v:+d}' for p, v in base.items()) +
  f'   median {np.median(list(base.values())):.0f}, worst {max(base.values())}')
H['sum_lag'] = H[LAG].sum(axis=1); H['sum_err'] = H[ERR].abs().sum(axis=1)
picks = []
for i, p in enumerate(PK):
    k = f'lag_{p:%Y%m}'; e = f'err_{p:%Y%m}'
    sc = H.assign(s1=H.sum_lag - H[k], s2=H.sum_err - H[e].abs(), s3=-H.marg)
    r = sc.sort_values(['s1', 's2', 's3']).iloc[0]
    picks.append((r.a, r.la, r.c, r.lc))
    P(f'  leave out {p:%Y-%m}: picks {r.a} >= {r.la:.3f} AND {r.c} >= {r.lc:.3f} '
      f'(exposure {r.expo:.1f}%, OR {r.comb:.2f}%, margin {r.marg:+.2f} sd); '
      f'held-out lag {int(r[k]):+d} against {base[p]:+d}, date {int(r[e]):+d}')
P(f'\nevery fold the same: {len(set(picks)) == 1}')
for q in set(picks): P(f'  {q}')
if len(set(picks)) == 1:
    a, la, c, lc = picks[0]
    r = H[(H.a == a) & (H.la == la) & (H.c == c) & (H.lc == lc)].iloc[0]
    P(f'\nTHE FOLDS\' CHOICE: {a} >= {la:.3f}  AND  {c} >= {lc:.3f}, published day {int(r.pub)}')
    P(f'  window exposure {r.expo:.1f}%; the OR of the second condition {r.comb:.2f}% (the shipped pair alone is 6.72%);')
    P(f'  tightest disturbance margin {r.marg:+.2f} sd (the shipped condition\'s own is +0.46)')
    P(f'  median {r.med:.0f} d (was 30), worst {int(r.worst)} (was 126), within a month {int(r.inm)}/12 (was 4), '
      f'mae {r.mae:.2f} (was 1.08), outside the thirteen {r.other}')
    P('  ' + '  '.join(f'{p:%Y-%m}:{int(r[f"lag_{p:%Y%m}"]):+d}[{int(r[f"err_{p:%Y%m}"]):+d}]'
                       + (f'(was {base[p]:+d})' if int(r[f'lag_{p:%Y%m}']) != base[p] else '') for p in PK))
log.close()
