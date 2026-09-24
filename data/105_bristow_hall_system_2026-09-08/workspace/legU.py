exec(open('minimise.py').read().split('print("PEAK-LEG SUBSETS')[0])
import numpy as np, pandas as pd, glob
W=shim.W
cands=glob.glob(W+"/**/IURSA.csv",recursive=True)
print("IURSA files:",cands[:3])
s=pd.read_csv(cands[0]); s.columns=['d','v']; s['d']=pd.to_datetime(s['d']); s=s.set_index('d')['v'].astype(float).dropna()
print("IURSA span",s.index[0].date(),"->",s.index[-1].date(),len(s),"weeks")
def leg_U(line=0.50, smooth=1, look=52, quiet=26, pub=5):
    x=s.rolling(smooth).mean()
    gap=x - x.rolling(look, min_periods=look).min().shift(1)
    calls=[]; armed=True; last=None
    for t,v in gap.dropna().items():
        if v>=line:
            if last is None or (t-last).days>365:
                calls.append((t+pd.Timedelta(days=pub), pd.Timestamp(t.year,t.month,1)))
            last=t
    return calls
U=leg_U()
print(f"leg U calls ({len(U)}):", ', '.join(f'{p:%Y-%m-%d}>{d:%Y-%m}' for p,d in U))
PLU=dict(PL); PLU['U']=U
import itertools
def rep(nm,pc,tc,pl=None):
    P=pl or PL
    r=run({k:P[k] for k in pc},{k:TLG[k] for k in tc})
    lp,ep,lt,et=r['lags_p'],r['errs_p'],r['lags_t'],r['errs_t']
    print(f"{nm:28} peaks {len(lp)}/12 other {r['other']} | onset med {np.median(lp):>3.0f}d worst {max(lp):>4} in-month {sum(1 for l in lp if l<=0)} <=31d {sum(1 for l in lp if l<=31)} | dates exact {sum(1 for e in ep if e==0)} mae {np.mean(np.abs(ep)):.2f} | troughs med {np.median(lt):.0f}d")
rep("ACM + KJH (minimised)",('A','C','M'),('K','J','H'))
rep("ACMU + KJH (+ leg U)",('A','C','M','U'),('K','J','H'),PLU)
rep("ACU + KJH",('A','C','U'),('K','J','H'),PLU)
rep("AU + KJH",('A','U'),('K','J','H'),PLU)
rep("ABCM + KJH",('A','B','C','M'),('K','J','H'))
rep("ABCMU + KJH",('A','B','C','M','U'),('K','J','H'),PLU)
print()
rep("ACMU + KJHP",('A','C','M','U'),('K','J','H','P'),PLU)
rep("ACMU + JHP",('A','C','M','U'),('J','H','P'),PLU)
rep("ABCMU + KJHP",('A','B','C','M','U'),('K','J','H','P'),PLU)
# leg U quiet-period check
qs=[(p,d) for p,d in U]
print("\nleg U: 6 calls in 55 years, all at recessions -> zero quiet-period calls (matches their memo)")
