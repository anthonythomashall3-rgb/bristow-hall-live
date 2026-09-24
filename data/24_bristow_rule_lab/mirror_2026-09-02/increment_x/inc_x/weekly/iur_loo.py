"""Leg U's form and line, chosen leave-one-recession-out (4 September 2026).
Grid: the insured unemployment rate's `smooth`-week mean, `line` points above its 52-week minimum (FRED IURSA, 1971-).
Fold rule: on the eleven remaining recessions, prefer no own quiet-period call, then the fastest median lag, then the
smallest worst lag, then the most exact dates; read the held-out recession at the fold's choice.  Output iur_loo.log."""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/weekly')
import numpy as np, pandas as pd, bristow_rule_v3 as B, american_chronology as AC
PK,TR=AC.PK,AC.TR
iur=pd.read_csv('/home/claude/archive/data/fred/IURSA.csv'); iur.columns=['d','v']; iur=iur.set_index(pd.to_datetime(iur['d']))['v'].astype(float)
PL,TL=AC.legs(safe=True,with_S=True); g=AC.sahm_rt(); vr=AC.vacancy_gap_rt(2,6)
SEC=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
def leg_U(line,smooth,back=52,quiet=26,pub=5):
    m=iur.rolling(smooth).mean(); gap=(m-m.rolling(back,min_periods=26).min()).dropna()
    out=[];below=0
    for t,v in gap.items():
        if v>=line:
            if below>=quiet: out.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1)))
            below=0
        else: below+=1
    return out
def qcount(calls): return sum(1 for p,_ in calls if not any(a-pd.DateOffset(months=9)<=p<=b+pd.DateOffset(months=18) for a,b in zip(PK,TR)))
GRID=[(sm,ln) for sm in (1,2,3,4,8) for ln in (0.30,0.40,0.50,0.60,0.70)]
res={}
log=open('iur_loo.log','w')
def P(*a): print(*a); print(*a,file=log)
for sm,ln in GRID:
    calls=leg_U(ln,sm)
    turns=B.american_chronology({**PL,'U':calls},TL,sahm=g,second=SEC)
    rows={}; other=[]
    for t in [x for x in turns if x['kind']=='peak']:
        c=[i for i,(a,b) in enumerate(zip(PK,TR)) if a-pd.DateOffset(months=6)<=t['date']<=b]
        if c: rows[PK[c[0]]]=((t['published']-AC.month_end(PK[c[0]])).days, AC.md(t['date'],PK[c[0]]))
        else: other.append(t['published'])
    res[(sm,ln)]=(qcount(calls),rows,other)
P('LEAVE-ONE-RECESSION-OUT over the (smoothing, line) grid')
picks=[]
for p in PK:
    best=None
    for k,(q,rows,other) in res.items():
        rr={a:b for a,b in rows.items() if a!=p}
        if len(rr)<11: continue
        lags=[v[0] for v in rr.values()]; errs=[v[1] for v in rr.values()]
        key=(q+len([o for o in other if not any(a-pd.DateOffset(months=9)<=o<=b+pd.DateOffset(months=18) for a,b in zip(PK,TR))]),
             np.median(lags), max(lags), -sum(1 for e in errs if e==0), k[0])
        if best is None or key<best[0]: best=(key,k)
    k=best[1]; picks.append(k)
    r=res[k][1].get(p)
    P(f'  leave out {p:%Y-%m}: picks smoothing {k[0]}w line {k[1]:.2f}; held-out lag {r[0]:+d} d, date {r[1]:+d}' if r else f'  leave out {p:%Y-%m}: picks {k}; NOT called')
P(f'  every fold the same: {len(set(picks))==1} {set(picks)}')
k=picks[0]; q,rows,other=res[k]
lags=[v[0] for v in rows.values()]; errs=[v[1] for v in rows.values()]
P(f"\nTHE FOLDS' CHOICE: leg U = the insured unemployment rate's {k[0]}-week mean {k[1]:.2f} points above its 52-week minimum")
P(f'  peaks {len(rows)}/12, median {np.median(lags):.0f} d, within a month {sum(l<=30 for l in lags)}, worst {max(lags)}, '
  f'dates exact {sum(e==0 for e in errs)}, within one {sum(abs(e)<=1 for e in errs)}, mae {np.mean([abs(e) for e in errs]):.2f}; '
  f"the leg's own quiet-period calls {q}; other route calls {[o.strftime('%Y-%m-%d') for o in other]}")
for p,(l,e) in rows.items(): P(f'   {p:%Y-%m}  lag {l:+5d} d  date {e:+d}')
log.close()
