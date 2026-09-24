"""Stage 181: combining the machine's own claims trough with the coincident panel.  The machine
already measures a trough -- the week the eight-week claims average peaks -- and it is weekly, so
it costs nothing to wait for.  On its own it names the right month five times in nine; the
coincident panel names it six.  Combined they name it eight.  This stage checks that the
combination is not an artefact of how the two are weighted, and tests it out of sample."""
exec(open("stage171_faster_dating.py").read().split('print("PEAK')[0])
import numpy as np, pandas as pd
ALL4=[n for n in ["payrolls","real income less transfers","industrial production","real manufacturing and trade sales"] if n in M]
FAST=[n for n in ALL4 if n!="real manufacturing and trade sales"]
CLAIMS=[pd.Period(x,"M") for x in ["1970-11","1975-03","1980-07","1982-10","1991-04","2001-11","2009-04","2020-05","2024-08"]]
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def panel_month(names,a,asof,back,fwd):
    o=[]
    for nm in names:
        d=turn(nm,a,asof,back,fwd,"min")
        if d is not None: o.append(d.to_period("M").ordinal)
    return None if not o else float(np.median(o))
def combos(names,months,back=300,fwd=30):
    out={}
    for lab,f in [("panel only",lambda p,c: p),
                  ("claims only",lambda p,c: float(c)),
                  ("half and half",lambda p,c: 0.5*p+0.5*c),
                  ("two thirds panel",lambda p,c: (2.0*p+c)/3.0),
                  ("two thirds claims",lambda p,c: (p+2.0*c)/3.0)]:
        mo=[]
        for i,a in enumerate(ENDC2):
            p=panel_month(names,a,a+pd.DateOffset(months=months),back,fwd)
            c=CLAIMS[i].ordinal
            if p is None: mo.append(None); continue
            v=f(p,c)
            mo.append((pd.Period(ordinal=int(round(v)),freq="M")-pd.Period(TRM[i],"M")).n)
        out[lab]=mo
    return out
for months,lab2 in [(9,"settled (nine months on)"),(1,"advance (one month after the end call)")]:
    for names,pn in [(ALL4,"the four"),(FAST,"the fast three")]:
        print("\nTROUGH, %s, %s"%(lab2,pn))
        print("%-20s %-9s %-9s %s"%("weighting","exact","<=1 mo","months from the NBER trough"))
        for k,v in combos(names,months).items():
            ok=[x for x in v if x is not None]
            print("%-20s %-9s %-9d %s"%(k,"%d of 9"%sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),v))
print("\nleave-one-out over the weighting and the panel (advance horizon)")
cache={}
for names,pn in [(ALL4,"four"),(FAST,"three")]:
    for k,v in combos(names,1).items(): cache[(pn,k)]=v
res=[]
for h in range(9):
    best=None
    for key,e in cache.items():
        o=[e[j] for j in range(9) if j!=h and e[j] is not None]
        if len(o)<8: continue
        sc=(sum(1 for x in o if x==0),sum(1 for x in o if abs(x)<=1),-float(np.mean(np.abs(o))))
        if best is None or sc>best[0]: best=(sc,key,e)
    res.append((best[2][h],best[1]))
    print("  %-9s held out -> %-6s chosen on the other eight: %s, %s"%(TRM[h],("%+d"%best[2][h]) if best[2][h] is not None else "-",best[1][0],best[1][1]))
ok=[e for e,_ in res if e is not None]
print("  held-out exact %d of 9, within one month %d of 9"%(sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1)))
