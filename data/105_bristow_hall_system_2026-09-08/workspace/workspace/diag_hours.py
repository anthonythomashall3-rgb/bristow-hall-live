exec(open('third.py').read().split('V=[dict(name=')[0])
import numpy as np, io, contextlib, pandas as pd
V=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
BASE=V+[dict(name='payroll3',gap=P3,line=0.3,pub_day=5)]
def turns(second,label):
    t=B.american_chronology({k:PLU[k] for k in ('A','B','C','M','U')},{k:TLG[k] for k in ('K','J','H')},sahm=g,second=second)
    pk=[x for x in t if x['kind']=='peak' and x['published']>=pd.Timestamp('1948-06-01')]
    print(f"--- {label}: {len(pk)} peak calls")
    for x in pk: print(f"    {x['published']:%Y-%m-%d} by {x['leg']:2s} dated {x['date']:%Y-%m}")
turns(BASE,"base (pair + payrolls)")
for line in (2.5,3.0,3.5,4.0):
    AWl=(first_prints("AWHMAN").rolling(6).max()/first_prints("AWHMAN")-1)*100
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLU[k] for k in ('A','B','C','M','U')},{k:TLG[k] for k in ('K','J','H')},
                sahm=g,second=BASE+[dict(name='hours',gap=AWl,line=line,pub_day=5)]),'x','1948-06-01')
    lp=r['lags_p']
    print(f"hours line {line}: peaks {len(lp)}/12 other {r['other']} median {np.median(lp):.0f} worst {max(lp)} lags {lp}")
