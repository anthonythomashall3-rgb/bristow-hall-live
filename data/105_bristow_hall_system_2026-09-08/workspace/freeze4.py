"""Route v4 -- frozen.  The symmetric confirmation window and the housing x rate
pair taken from the other route's version 44, this route's ETA 5159 object on
top, and the housing line set where Rule 21 allows it rather than where the
speed is best."""
exec(open('eta5159_gate.py').read().split("PK5=('A','B','C','M','U')")[0])
PK5=('A','B','C','M','U'); TR3=('K','J','H')
import numpy as np, pandas as pd, io, contextlib, hashlib, glob
UR=first_prints("UNRATE"); HO=first_prints("HOUST"); lh=np.log(HO)*100
S=first_prints("UNRATE"); SG=S.rolling(3).mean()-S.rolling(12).min().shift(1)
def pair(hl,rl=0.20):
    return pd.concat([(lh.rolling(12).max()-lh.rolling(2).mean())/hl,
                      (UR-UR.rolling(12).min())/rl],axis=1).min(axis=1).dropna()
def union(objs):
    idx=None
    for o,l in objs:
        h=(o.dropna()>=l)
        idx=h if idx is None else (h.reindex(idx.index.union(h.index)).fillna(False)|idx.reindex(idx.index.union(h.index)).fillna(False))
    return exposure(idx.astype(float),1.0)
BASE=[(SG,0.50),(vr,0.36),(P3,0.30),(B5,40.0)]
V=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
PAY=dict(name='payroll3',gap=P3,line=0.3,pub_day=5)
E51=dict(name='eta5159',gap=B5,line=40.0,pub_day=30)
def rep(second,horizon=6):
    with contextlib.redirect_stdout(io.StringIO()):
        return score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=second,horizon_months=horizon),'x','1948-06-01')
L=[]; P=L.append
P("ROUTE v4 -- FROZEN RECORD, 4 September 2026"); P("="*78); P("")
P("The confirming set, and what each object costs in quiet-month exposure")
P(f"{'  confirming set':56}{'at line':>9}{'in window':>11}{'quiet n':>9}")
for nm,objs in [('  Sahm 0.50 + vacancy 0.36',BASE[:2]),
                ('  + payrolls 3-month 0.30%',BASE[:3]),
                ('  + ETA 5159 breadth 40%',BASE),
                ('  + housing 35 x rate 0.20',BASE+[(pair(35),1.0)]),
                ('  + housing 30 x rate 0.20  (NOT adopted)',BASE+[(pair(30),1.0)])]:
    a,b,n=union(objs); P(f"{nm:56}{a:8.2f}%{b:10.2f}%{n:9d}")
P("")
rows=[("v2, as frozen this morning (window 18)",V+[PAY],18),
      ("v3, + ETA 5159 (window 18)",V+[PAY,E51],18),
      ("v4, + symmetric window + housing 35 x rate 0.20",
       V+[PAY,E51,dict(name='housing x rate',gap=pair(35),line=1.0,pub_day=18)],6),
      ("   the same at housing 30 -- FASTER, NOT ADOPTED",
       V+[PAY,E51,dict(name='housing x rate',gap=pair(30),line=1.0,pub_day=18)],6)]
P("The record, 1948-2026")
for nm,sec,h in rows:
    r=rep(sec,h); lp,ep,lt=r['lags_p'],r['errs_p'],r['lags_t']
    P(f"  {nm}")
    P(f"     peaks {len(lp)}/12, {r['other']} further call | median {np.median(lp):.0f} d, mean {np.mean(lp):.1f}, worst {max(lp)}"
      f" | inside the peak month {sum(1 for l in lp if l<=0)}, within a month {sum(1 for l in lp if l<=31)}")
    P(f"     dates exact {sum(1 for e in ep if e==0)}/12, mean error {np.mean(np.abs(ep)):.2f} months | troughs {len(lt)}/12, median {np.median(lt):.0f} d")
    P(f"     {lp}")
P("")
P("Risk")
P("  false alarms   ZERO, observed. Thirteen American onset calls, thirteen recessions.")
P("                 The ETA 5159 object separately: seven episodes in 655 months of the")
P("                 Department's complete state file, and the seven are the seven recessions.")
P("                 Any 'one in N years' figure is a modelled CEILING on the hazard, not a")
P("                 rate. The 0.035-0.25 per cent a year (one in 400 to 2,889) this route")
P("                 printed until today is WITHDRAWN: it was computed on a one-month forward")
P("                 reach while the confirmation window ran eighteen months forward. The")
P("                 window is now symmetric at six months either side, which is what the")
P("                 other route established, and the ceiling must be recomputed on it before")
P("                 any figure is printed. Until then the only number this route states is")
P("                 the observed count, which is zero.")
P("  detection      13 of 13 since 1948; Clopper-Pearson lower bound 79 per cent.")
P("")
P("What was refused, and the number that refused it")
a30,b30,_=union(BASE+[(pair(30),1.0)]); a35,b35,_=union(BASE+[(pair(35),1.0)]); ab,bb,_=union(BASE)
P(f"  housing 30 x rate 0.20 is faster -- median 18 days against 28, December 2007 at -3 days")
P(f"  against +49 -- and it is the only line at which the 2007 gain exists. It also fires in a")
P(f"  quiet month: union exposure {bb:.2f} -> {b30:.2f} per cent, a hazard multiplier of {b30/bb:.3f}.")
P(f"  At 35 the object never reaches its line in a quiet month and the union goes {bb:.2f} -> {b35:.2f}.")
P(f"  Rule 21 says choose nothing that raises the false-alarm risk, so 35 is adopted and 30 is")
P(f"  priced and left to Anthony. This is the factory-hours decision again at a smaller number.")
P("")
P("  leg U was swept and NOT changed. The other route reaches July 1981 at +122 days on its own")
P("  leg-U configuration where this one reaches +142. Sweeping the line, the smoothing and the")
P("  lookback finds settings with a better worst call (0.60/2/52 gives 125) and settings with a")
P("  better median (0.30 gives 18) -- and the fast ones call July 1990 two hundred days early,")
P("  which is not detection. The 0.50 line was chosen leave-one-recession-out and was unanimous")
P("  in all twelve folds. Changing it now on a full-record worst-lag argument is exactly the")
P("  decision this route refuses to make. It stays.")
out="\n".join(L); print(out); open('FROZEN_RECORD_v4.txt','w').write(out+"\n")
h=hashlib.sha256()
for f in sorted(glob.glob('*.py')): h.update(open(f,'rb').read())
print(f"\nSHA-256 of the route's code: {h.hexdigest()}")
