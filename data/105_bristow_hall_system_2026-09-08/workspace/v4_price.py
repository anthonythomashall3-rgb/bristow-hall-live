"""Price the housing x rate pair exactly, and reconcile against the other
route's claim of zero window exposure.  Rule 21 turns on this number."""
exec(open('eta5159_gate.py').read().split("PK5=('A','B','C','M','U')")[0])
import numpy as np, pandas as pd
UR=first_prints("UNRATE"); HO=first_prints("HOUST"); lh=np.log(HO)*100
def pair(hline,rline,shift):
    hg = lh.rolling(12).max().shift(shift) - lh.rolling(2).mean()
    rg = UR - UR.rolling(12).min().shift(shift)
    return pd.concat([hg/hline, rg/rline],axis=1).min(axis=1).dropna()
print(f"{'form':46}{'at line':>9}{'IN WINDOW':>11}{'quiet n':>9}")
for shift,tag in [(0,'trailing max/min including this month'),(1,"Sahm's own form, shift(1)")]:
    P=pair(30.0,0.20,shift); a,b,n=exposure(P,1.0)
    print(f"housing 30 x rate 0.20, {tag:26}{a:8.2f}%{b:10.2f}%{n:9d}")
    for hl,rl in [(30,0.25),(35,0.20),(30,0.30),(40,0.20)]:
        P2=pair(hl,rl,shift); a2,b2,n2=exposure(P2,1.0)
        print(f"   housing {hl} x rate {rl:<5}{'':22}{a2:8.2f}%{b2:10.2f}%{n2:9d}")

# union exposure of the whole confirming set, which is what Rule 21 actually prices
S=first_prints("UNRATE"); SG=S.rolling(3).mean()-S.rolling(12).min().shift(1)
def union(objs):
    idx=None
    for o,l in objs:
        h=(o.dropna()>=l)
        idx=h if idx is None else h.reindex(idx.index.union(h.index)).fillna(False)|idx.reindex(idx.index.union(h.index)).fillna(False)
    return exposure(idx.astype(float),1.0)
SETS={
 'pair (Sahm + vacancy)':[(SG,0.50),(vr,0.36)],
 '+ payrolls':[(SG,0.50),(vr,0.36),(P3,0.30)],
 '+ payrolls + ETA 5159':[(SG,0.50),(vr,0.36),(P3,0.30),(B5,40.0)],
 '+ payrolls + ETA 5159 + housing x rate (shift 0)':[(SG,0.50),(vr,0.36),(P3,0.30),(B5,40.0),(pair(30,.20,0),1.0)],
 '+ payrolls + ETA 5159 + housing x rate (shift 1)':[(SG,0.50),(vr,0.36),(P3,0.30),(B5,40.0),(pair(30,.20,1),1.0)],
}
print(f"\n{'confirming set':52}{'at line':>9}{'IN WINDOW':>11}{'quiet n':>9}")
for k,v in SETS.items():
    a,b,n=union(v); print(f"{k:52}{a:8.2f}%{b:10.2f}%{n:9d}")
