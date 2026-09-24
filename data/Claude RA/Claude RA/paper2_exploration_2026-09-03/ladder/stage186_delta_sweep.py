"""Stage 186: with nine hundred quiet country-years and no false alarm, the rule is too tight.
The margin was set on American data where there are only forty-five quiet years to spend.  This
sweeps it downward across the whole international panel and prices the trade in the only currency
that matters -- episodes detected against false alarms raised -- and reports the exact binomial
bounds each setting supports."""
import os, sys, io, contextlib
import numpy as np, pandas as pd
from scipy import stats as sst
sys.argv=[""]
src=open("stage185_intl_wide2.py").read().split("ALL=[];FA=[]")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
def sweep(delta,floor=0.30):
    ALL=[];FA=[];Y=0.0
    for iso in sorted(CH):
        r=build(iso,delta=delta,floor=floor)
        if r is None: continue
        rows,fa,qy,nch=r; ALL+=rows; FA+=fa; Y+=qy
    d=pd.DataFrame(ALL,columns=["iso","peak","depth","found"]).dropna()
    return d,len(FA),Y
def lower(k,n):
    return 0.0 if k==0 else sst.beta.ppf(0.05,k,n-k+1) if k<n else 0.05**(1.0/n)
def upper_rate(f,y):
    return (1-0.05**(1.0/y)) if f==0 else sst.chi2.ppf(0.95,2*(f+1))/(2*y)
print("%-7s %-7s %-22s %-22s %-22s %-26s %s"%("margin","floor","all dips","fell over 2pc","fell over 4pc","false alarms","95% lower bound, deep"))
for delta in [0.25,0.10,0.00,-0.10,-0.25,-0.50]:
  for floor in [0.30]:
    d,F,Y=sweep(delta,floor)
    d2=d[d.depth<=-2.0]; d4=d[d.depth<=-4.0]
    lb4=lower(int(d4.found.sum()),len(d4))
    print("%-7.2f %-7.2f %-22s %-22s %-22s %-26s %.3f"%(delta,floor,
        "%d of %d (%.0f%%)"%(d.found.sum(),len(d),100*d.found.mean()),
        "%d of %d (%.0f%%)"%(d2.found.sum(),len(d2),100*d2.found.mean()),
        "%d of %d (%.0f%%)"%(d4.found.sum(),len(d4),100*d4.found.mean()),
        "%d in %.0f (<= %.4f/yr)"%(F,Y,upper_rate(F,Y)),lb4))
