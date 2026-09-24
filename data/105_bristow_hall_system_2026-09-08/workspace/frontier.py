"""The speed-hazard frontier, priced on the CORRECTED symmetric window.

Every Rule 21 verdict this route made today was priced on a window reaching one
month forward. On the true window two of the three objects admitted are still
free and one is not. This prints what each buys and what each costs, so the
choice is made on the numbers rather than on the order things were tried in."""
exec(open('eta5159_gate.py').read().split("PK5=('A','B','C','M','U')")[0])
PK5=('A','B','C','M','U'); TR3=('K','J','H')
import numpy as np, pandas as pd, io, contextlib
def leg_U2(line=0.50,smooth=1,look=52,pub=5):
    x=s.rolling(smooth).mean(); gap=x-x.rolling(look,min_periods=look).min().shift(1)
    c=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0.0: armed=True
    return c
PLU=dict(PL); PLU['U']=leg_U2()
UR=first_prints("UNRATE"); HO=first_prints("HOUST"); lh=np.log(HO)*100
def pair(hl): return pd.concat([(lh.rolling(12).max()-lh.rolling(2).mean())/hl,
    (UR-UR.rolling(12).min())/0.20],axis=1).min(axis=1).dropna()
V=[dict(name='vacancy',gap=vr,line=0.36,pub_day=30)]
PAY=dict(name='payroll3',gap=P3,line=0.3,pub_day=5)
E51=dict(name='eta5159',gap=B5,line=40.0,pub_day=30)
H35=dict(name='housing35',gap=pair(35),line=1.0,pub_day=18)
H30=dict(name='housing30',gap=pair(30),line=1.0,pub_day=18)
def rep(nm,second,expo):
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=second,horizon_months=6),'x','1948-06-01')
    lp,ep=r['lags_p'],r['errs_p']
    haz=0.0779*expo/100
    print(f"{nm}\n   exposure {expo:5.2f}%   hazard {haz*100:.3f}%/yr = one in {1/haz:3.0f} years"
          f"   |  peaks {len(lp)}/12 other {r['other']} | median {np.median(lp):.0f}d mean {np.mean(lp):.1f} worst {max(lp)}"
          f" in-month {sum(1 for l in lp if l<=0)} | exact {sum(1 for e in ep if e==0)}\n   {lp}")
rep("FREE      pair only",                      V,                    9.70)
rep("FREE      + payrolls",                     V+[PAY],              9.70)
rep("FREE      + payrolls + housing 35",        V+[PAY,H35],          9.70)
rep("x1.286    + ETA 5159 as well (v5 as shipped this morning)", V+[PAY,E51,H35], 12.47)
rep("x1.286    + housing 30 instead of 5159",   V+[PAY,H30],          12.47)
rep("x1.571    + both",                         V+[PAY,E51,H30],      15.24)
