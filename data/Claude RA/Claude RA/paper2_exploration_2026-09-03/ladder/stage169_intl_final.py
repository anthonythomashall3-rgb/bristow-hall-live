"""Stage 169: the international rule, frozen.  Every line is that country's own quiet record plus
a quarter of that country's own robust standard deviation -- the same margin as the American
rule, in both lanes -- with a floor requiring unemployment to be above its own twelve-month low
where an unemployment series exists.  Scored against two consecutive negative quarters of real
GDP, inside each country's own GDP record, which is the definition that can be verified."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage168_intl_fix.py")).read().split('print("%-6s %-7s')[0])
ALL=[];FA=[];Y=0.0;ROWS=[]
for iso in sorted(CC):
    r=run(iso,1,0.30,0.25,0.25,True)
    if r is None: continue
    ro,fa,qy=r; ALL+=ro; FA+=[(iso,x) for x in fa]; Y+=qy
    d=[x for x in ro if x[2] is not None]
    deep=[x for x in d if x[2]<=-2.0]
    ROWS.append((iso,NAME.get(iso,iso),sum(1 for x in d if x[3]),len(d),
                 sum(1 for x in deep if x[3]),len(deep),
                 [x[1] for x in deep if not x[3]],len(fa),qy))
print("%-4s %-16s %-10s %-14s %-24s %s"%("iso","country","all dips","fall over 2pc","deep ones missed","false"))
for iso,nm,a,n,da,dn,dm,nf,qy in ROWS:
    if n==0 and nf==0: continue
    print("%-4s %-16s %-10s %-14s %-24s %d"%(iso,nm,"%d/%d"%(a,n),"%d/%d"%(da,dn),",".join(dm)[:23],nf))
d=pd.DataFrame(ALL,columns=["iso","peak","depth","found"]).dropna()
for lo,lab in [(-1e9,"every two-quarter dip"),(-2.0,"output fell more than 2 per cent"),(-4.0,"output fell more than 4 per cent")]:
    s=d[d.depth<=lo] if lo>-1e8 else d
    print("\n%-36s %d of %d (%.0f%%)"%(lab,s.found.sum(),len(s),100*s.found.mean()))
print("false alarms: %d in %.0f quiet country-years"%(len(FA),Y))
print("\ndeep episodes still missed:")
for _,r in d[(d.depth<=-2.0)&(~d.found)].sort_values("depth").iterrows():
    print("  %-4s %s  output fell %.1f per cent"%(r.iso,r.peak,r.depth))
