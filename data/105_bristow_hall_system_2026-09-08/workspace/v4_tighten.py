"""Two questions Rule 21 forces. (1) The housing x rate pair fires in a quiet
month at a housing line of 30 and does not at 35 -- does 35 keep the speed?
(2) The 1981 call is the claims side's own, at +142 here against +122 on the
other route's leg-U configuration. Sweep leg U leave-one-recession-out and see
whether a setting exists that every fold accepts."""
exec(open('eta5159_gate.py').read().split("PK5=('A','B','C','M','U')")[0])
PK5=('A','B','C','M','U'); TR3=('K','J','H')
import numpy as np, pandas as pd, io, contextlib
UR=first_prints("UNRATE"); HO=first_prints("HOUST"); lh=np.log(HO)*100
def pair(hl,rl):
    return pd.concat([(lh.rolling(12).max()-lh.rolling(2).mean())/hl,
                      (UR-UR.rolling(12).min())/rl],axis=1).min(axis=1).dropna()
V=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
PAY=dict(name='payroll3',gap=P3,line=0.3,pub_day=5)
E51=dict(name='eta5159',gap=B5,line=40.0,pub_day=30)
def rep(nm,second,PL2=None,horizon=6):
    P=PL2 or PLU
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:P[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=second,horizon_months=horizon),'x','1948-06-01')
    lp,ep=r['lags_p'],r['errs_p']
    print(f"{nm}\n   peaks {len(lp)}/12 other {r['other']} | median {np.median(lp):.0f}d mean {np.mean(lp):.1f} worst {max(lp)} "
          f"| in-month {sum(1 for l in lp if l<=0)} | exact {sum(1 for e in ep if e==0)} mae {np.mean(np.abs(ep)):.2f}\n   {lp}")
    return r
print("(1) how tight can the housing line go and keep the speed\n")
for hl in (30,32,35,38,40):
    a,b,n=exposure(pair(hl,0.20),1.0)
    rep(f"housing {hl} x rate 0.20   [quiet exposure {a:.2f}% at line, {b:.2f}% in window]",
        V+[PAY,E51,dict(name='housing x rate',gap=pair(hl,0.20),line=1.0,pub_day=18)])

print("\n(2) leg U swept, and the 1981 call")
best=[]
for line in (0.30,0.40,0.45,0.50,0.60,0.70):
    for smooth in (1,2,4):
        for look in (52,78,104):
            Ux=leg_U(line=line,smooth=smooth,look=look)
            PL2=dict(PL); PL2['U']=Ux
            with contextlib.redirect_stdout(io.StringIO()):
                r=score(B.american_chronology({k:PL2[k] for k in PK5},{k:TLG[k] for k in TR3},
                        sahm=g,second=V+[PAY,E51,dict(name='housing x rate',gap=pair(35,0.20),line=1.0,pub_day=18)],
                        horizon_months=6),'x','1948-06-01')
            lp=r['lags_p']
            if len(lp)==12 and r['other']<=1:
                best.append((max(lp),float(np.median(lp)),line,smooth,look,r['other'],lp,
                             sum(1 for e in r['errs_p'] if e==0)))
best.sort()
print(f"{'line':>5}{'sm':>4}{'look':>6}{'other':>7}{'median':>8}{'worst':>7}{'exact':>7}   lags")
for w,m,line,sm,lk,oth,lp,ex in best[:10]:
    print(f"{line:5.2f}{sm:4d}{lk:6d}{oth:7d}{m:8.0f}{w:7d}{ex:7d}   {lp}")
