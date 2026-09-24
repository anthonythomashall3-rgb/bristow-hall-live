"""Stage 174: is the fast panel a real gain or a selection?  Stage 173 found that dropping the
slowest-publishing series makes the advance date both sooner and more accurate.  That is a subset
search, and subset searches have already failed leave-one-out once in this programme.  Here the
panel and the window are chosen nine times over, each on the other eight episodes, and the
held-out episode is dated by a configuration that never saw it."""
exec(open("stage171_faster_dating.py").read().split('print("PEAK')[0])
import numpy as np, pandas as pd, itertools
LAG={"payrolls":7,"real income less transfers":30,"industrial production":17,
     "real manufacturing and trade sales":47}
LAG={k:v for k,v in LAG.items() if k in M}
def med_sub(names,anchor,asof,back,fwd,kind,how):
    o=[]
    for nm in names:
        d=turn(nm,anchor,asof,back,fwd,kind)
        if d is not None: o.append(d.to_period("M").ordinal)
    if not o: return None
    x=float(np.median(o))
    v=int(np.floor(x)) if how=="earlier" else (int(np.ceil(x)) if how=="later" else int(round(x)))
    return pd.Period(ordinal=v,freq="M")
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def build(anch,ref,kind,windows,months):
    cache={}
    for r in range(1,5):
      for names in itertools.combinations(LAG,r):
        for back,fwd in windows:
          for how in ["nearest","earlier"]:
            errs=[]
            for i,a in enumerate(anch):
                d=med_sub(names,a,a+pd.DateOffset(months=months),back,fwd,kind,how)
                errs.append(None if d is None else (d-pd.Period(ref[i],"M")).n)
            cache[(names,back,fwd,how)]=errs
    return cache
def loo(cache):
    out=[]
    for h in range(9):
        best=None
        for key,e in cache.items():
            o=[e[j] for j in range(9) if j!=h and e[j] is not None]
            if len(o)<8: continue
            sc=(sum(1 for x in o if x==0),sum(1 for x in o if abs(x)<=1),-float(np.mean(np.abs(o))),-len(key[0]))
            if best is None or sc>best[0]: best=(sc,key,e)
        out.append((best[2][h],best[1]) if best else (None,None))
    return out
PW=[(180,30),(180,60),(240,30),(180,180)]
TW=[(300,30),(300,60),(365,30),(420,120)]
cp=build(ALARM,PKM,"max",PW,2); ct=build(ENDC2,TRM,"min",TW,1)
lp=loo(cp); lt=loo(ct)
print("leave-one-out, advance peak (two months after the alarm)")
for i,(e,key) in enumerate(lp):
    print("  %-9s held-out error %-6s chosen on the other eight: %s window %d/%d %s"%(
        PKM[i],("%+d"%e) if e is not None else "-"," + ".join(n[:14] for n in key[0]),key[1],key[2],key[3]))
ok=[e for e,_ in lp if e is not None]
print("  exact %d of 9, within one month %d of 9"%(sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1)))
print("\nleave-one-out, advance trough (one month after the end call)")
for i,(e,key) in enumerate(lt):
    print("  %-9s held-out error %-6s chosen on the other eight: %s window %d/%d %s"%(
        TRM[i],("%+d"%e) if e is not None else "-"," + ".join(n[:14] for n in key[0]),key[1],key[2],key[3]))
ok=[e for e,_ in lt if e is not None]
print("  exact %d of 9, within one month %d of 9"%(sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1)))
print("\nfixed a-priori alternative: the three of the four published within thirty days")
FAST=tuple(n for n in LAG if LAG[n]<=30)
for lab,cache,key in [("peak, 180/30 nearest",cp,(FAST,180,30,"nearest")),
                      ("peak, 180/30 earlier",cp,(FAST,180,30,"earlier")),
                      ("trough, 300/30 nearest",ct,(FAST,300,30,"nearest")),
                      ("trough, 300/30 earlier",ct,(FAST,300,30,"earlier"))]:
    e=cache.get(key)
    if e: print("  %-24s exact %d of 9, within one month %d  %s"%(lab,sum(1 for x in e if x==0),
        sum(1 for x in e if x is not None and abs(x)<=1),e))
