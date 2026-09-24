"""LEAVE-ONE-RECESSION-OUT OVER THE ADMISSIBLE PAIRS, UNDER THE SYMMETRIC WINDOW (4 September 2026).

`recheck_capped.py` produced every (housing form, rate form, housing line, rate line) that passes all four gates
once the confirmation window is made symmetric about the claims call.  There are 478 of them, every one at zero
window exposure with the second condition's OR unchanged at 6.72 per cent - no added hazard at all - and with
disturbance margins of +1.1 to +4.9 standard deviations against the shipped condition's own +0.68.

Selection happens here, over the WHOLE admissible set, leave-one-recession-out.  The fold's score, stated before
it is run: the sum of the eleven kept lags; then the sum of the kept absolute date errors; then, as a tie-break
only, the WIDER disturbance margin - because between two clauses that date the record equally well the safer one
is the one that clears the disturbances by more.

Output capped_pair_loo.log.
"""
import sys, pickle, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
PK = [pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11',
                                '1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
log = open('/home/claude/lab/weekly/capped_pair_loo.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
D = pickle.load(open('/home/claude/lab/weekly/recheck_capped.pkl','rb'))
rows = []
for g, r in D['best2']:
    kh, bh, ku, bu, lh, lu = g
    rows.append(dict(kh=kh, bh=bh, ku=ku, bu=bu, lh=lh, lu=lu, marg=r['marg'], expo=r['expo'], comb=r['comb'],
                     other=str(r['other']),
                     **{f'lag_{p:%Y%m}': r['hit'][p] for p in PK},
                     **{f'err_{p:%Y%m}': r['err'][p] for p in PK}))
H = pd.DataFrame(rows)
LAG=[f'lag_{p:%Y%m}' for p in PK]; ERR=[f'err_{p:%Y%m}' for p in PK]
H['sum_lag']=H[LAG].sum(axis=1); H['sum_err']=H[ERR].abs().sum(axis=1)
base = dict(zip(PK,[10,51,-11,-70,31,120,30,122,51,30,126,26]))
P(f'{len(H)} admissible settings under the symmetric window.')
P('version 43: ' + '  '.join(f'{p:%Y-%m}:{v:+d}' for p,v in base.items()) +
  f'   median {np.median(list(base.values())):.0f}, worst {max(base.values())}')
P(f'margins from {H.marg.min():+.2f} to {H.marg.max():+.2f} sd; exposure {H.expo.min():.2f} to {H.expo.max():.2f} per cent; '
  f'the OR {H.comb.min():.2f} to {H.comb.max():.2f} against the shipped 6.72')
picks=[]
for p in PK:
    k=f'lag_{p:%Y%m}'; e=f'err_{p:%Y%m}'
    sc=H.assign(s1=H.sum_lag-H[k], s2=H.sum_err-H[e].abs(), s3=-H.marg)
    r=sc.sort_values(['s1','s2','s3']).iloc[0]
    picks.append((int(r.kh),int(r.bh),int(r.ku),int(r.bu),float(r.lh),float(r.lu)))
    P(f'  leave out {p:%Y-%m}: picks housing({int(r.kh)},{int(r.bh)}) >= {r.lh:.0f} AND rate({int(r.ku)},{int(r.bu)}) >= {r.lu:.2f} '
      f'(margin {r.marg:+.2f} sd, exposure {r.expo:.2f}%, OR {r.comb:.2f}%); held-out lag {int(r[k]):+d} against {base[p]:+d}, date {int(r[e]):+d}')
u = len(set(picks))==1
P(f'\nevery fold the same: {u}')
for q in sorted(set(picks)): P(f'  {q}')
if u:
    kh,bh,ku,bu,lh,lu = picks[0]
    r = H[(H.kh==kh)&(H.bh==bh)&(H.ku==ku)&(H.bu==bu)&(H.lh==lh)&(H.lu==lu)].iloc[0]
    P(f'\nTHE FOLDS\' CHOICE: housing starts, {kh}-month mean {lh:.0f} log points below its trailing {bh}-month maximum,')
    P(f'  AND the unemployment rate, {ku}-month mean {lu:.2f} points above its trailing {bu}-month minimum; published the 18th.')
    P(f'  window exposure {r.expo:.2f}%; the OR of the second condition {r.comb:.2f}% against the shipped 6.72% - UNCHANGED;')
    P(f'  tightest disturbance margin {r.marg:+.2f} sd against the shipped condition\'s own +0.68')
    lags=[int(r[f'lag_{p:%Y%m}']) for p in PK]; errs=[int(r[f'err_{p:%Y%m}']) for p in PK]
    P(f'  median {np.median(lags):.0f} d (was {np.median(list(base.values())):.0f}), worst {max(lags)} (was {max(base.values())}), '
      f'within a month {sum(0<=v<=30 for v in lags)}/12, mae {np.mean([abs(x) for x in errs]):.2f} (was 1.08), outside the thirteen {r.other}')
    P('  ' + '  '.join(f'{p:%Y-%m}:{v:+d}[{e:+d}]' + (f'(was {base[p]:+d})' if v!=base[p] else '') for p,v,e in zip(PK,lags,errs)))
else:
    P('\n  the folds disagree; under Rule 18 nothing may be adopted on this evidence.')
    P('  what they agree on:')
    for i,nm in enumerate(('housing k','housing back','rate k','rate back','housing line','rate line')):
        vals={q[i] for q in picks}
        P(f'    {nm:13s}: {sorted(vals)}  {"AGREED" if len(vals)==1 else ""}')
log.close()
