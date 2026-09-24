"""Taking what the other route found and did not stop at: the symmetric
confirmation window (their version 44's design correction) and the
housing-starts x unemployment-rate conjunctive pair, with this route's own
ETA 5159 object on top of both.

The window is the important one.  A claims call was given eighteen months in
which the second condition could confirm it, against six months behind -- so a
disturbance had twenty-two months of exposure, and every hazard figure computed
on a one-month forward reach understated it.  Symmetric is a design correction,
not a fitted number.
"""
exec(open('eta5159_gate.py').read().split("PK5=('A','B','C','M','U')")[0])
PK5=('A','B','C','M','U'); TR3=('K','J','H')
import numpy as np, pandas as pd, io, contextlib

UR=first_prints("UNRATE"); HO=first_prints("HOUST")
print(f"UNRATE first prints {UR.index[0]:%Y-%m} -> {UR.index[-1]:%Y-%m} ({len(UR)})")
print(f"HOUST  first prints {HO.index[0]:%Y-%m} -> {HO.index[-1]:%Y-%m} ({len(HO)})")
# housing: two-month mean this far in log points below its trailing 12-month maximum
lh=np.log(HO)*100
HG=lh.rolling(12).max().shift(0) - lh.rolling(2).mean()
# rate: this far above its trailing twelve-month minimum
RG=UR - UR.rolling(12).min()
PAIR=pd.concat([HG/30.0, RG/0.20],axis=1).min(axis=1).dropna()   # >=1 iff BOTH at their lines

def expose_pair():
    a,b,n=exposure(PAIR,1.0); return a,b,n
a,b,n=expose_pair()
print(f"\nhousing x rate pair: window exposure {a:.2f}% at the line, {b:.2f}% in window, {n} quiet months")
a2,b2,n2=exposure(B5,40.0)
print(f"ETA 5159 breadth   : window exposure {a2:.2f}% at the line, {b2:.2f}% in window, {n2} quiet months")

V=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
PAY=dict(name='payroll3',gap=P3,line=0.3,pub_day=5)
HR =dict(name='housing x rate',gap=PAIR,line=1.0,pub_day=18)
E51=dict(name='eta5159',gap=B5,line=40.0,pub_day=30)

def rep(nm,second,horizon=18):
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=second,horizon_months=horizon),'x','1948-06-01')
    lp,ep=r['lags_p'],r['errs_p']
    print(f"{nm}\n   peaks {len(lp)}/12 other {r['other']} | median {np.median(lp):.0f}d mean {np.mean(lp):.1f} worst {max(lp)} "
          f"| in-month {sum(1 for l in lp if l<=0)} <=31d {sum(1 for l in lp if l<=31)} | exact {sum(1 for e in ep if e==0)} mae {np.mean(np.abs(ep)):.2f}\n   {lp}")
    return lp
print()
rep("v2 shipped, window 18 (as frozen)", V+[PAY])
rep("v3, + ETA 5159, window 18", V+[PAY,E51])
rep("window 6 only (their design correction)", V+[PAY], 6)
rep("window 6 + housing x rate", V+[PAY,HR], 6)
rep("window 6 + ETA 5159", V+[PAY,E51], 6)
rep("window 6 + housing x rate + ETA 5159", V+[PAY,HR,E51], 6)
print("\nwindow sensitivity of the full set (their claim: bit-identical 4 to 36):")
for h in (4,6,9,12,18,24,36):
    lp=rep(f"  horizon {h}", V+[PAY,HR,E51], h)
