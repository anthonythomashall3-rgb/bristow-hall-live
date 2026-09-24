"""Route v7 -- ETA 5159's speed, bought with ONE conjunctive pair, for nothing.

The pair: average weekly hours in manufacturing 2.0 per cent or more below their
trailing twelve-month maximum, AND nondurable-goods employment down 1.20 per cent
over three months, in the same month, on first prints.

Factory hours was refused twice on its own at 10.62 per cent exposure. Inside a
pair it is free: the pair fires only where both stand at their lines, so hours is
the fast object and the employment fall is the gate that keeps it out of every
inventory correction.
"""
exec(open('hazard_v5.py').read().split('print("CONTROL')[0])
import io, contextlib
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l
f3 =lambda v,l:(-(v/v.shift(3)-1)*100)/l
PR =lambda a,b: pd.concat([a,b],axis=1).min(axis=1).dropna()
P1=PR(f12(AWH,2.0),f3(ND,1.20))
h=lambda o,l:(o.dropna()>=l).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
H1=h(P1,1.0)
c1,_=win_expo([S,V],7,1); c2,_=win_expo([S,V,P3h,A],7,1)
L=[]
import sys
class T:
    def write(self,x): sys.__stdout__.write(x); L.append(x)
    def flush(self): pass
sys.stdout=T()
print("ROUTE v7 -- FROZEN RECORD, 4 September 2026"); print("="*72); print()
print(f"control   shipped pair {c1:.2f}% (published 7.39)   with factory hours {c2:.2f}% (published 12.47)")
print()
print(f"{'confirming set':46}{'expo (6,4)':>12}{'hazard/yr':>11}{'one in':>9}")
for nm,parts in [("v6  Sahm + vacancy + payrolls + housing 35",[S,V,P3h,H]),
                 ("v7  + hours 2.0 x nondurable employment 1.20",[S,V,P3h,H,H1]),
                 ("    for comparison: + ETA 5159 (declined)",[S,V,P3h,H,E5]),
                 ("    for comparison: + factory hours ALONE",[S,V,P3h,H,A])]:
    e,_=win_expo(parts,7,5); hz=0.0779*e/100
    print(f"{nm:46}{e:11.2f}%{hz*100:10.3f}%{1/hz:9.0f}")
sys.stdout=sys.__stdout__
open('FROZEN_RECORD_v7_expo.txt','w').write(''.join(L))
print(''.join(L)[-1200:] if False else '')
