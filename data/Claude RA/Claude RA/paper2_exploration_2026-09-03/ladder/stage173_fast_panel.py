"""Stage 173: the advance date waits on its slowest member.  Payrolls print seven days after the
month ends and industrial production seventeen; real income takes thirty and manufacturing and
trade sales forty-seven.  A panel that drops the slow members can be read three weeks sooner.
This stage prices that: every subset of the four, scored on accuracy AND on the day the answer
becomes available."""
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
def score(names,anch,ref,kind,back,fwd,how,months):
    n=0; errs=[]
    for i,a in enumerate(anch):
        d=med_sub(names,a,a+pd.DateOffset(months=months),back,fwd,kind,how)
        e=None if d is None else (d-pd.Period(ref[i],"M")).n
        errs.append(e); n+=int(e==0)
    return n,sum(1 for e in errs if e is not None and abs(e)<=1),errs
print("ADVANCE PEAK — every panel, at two and three months after the alarm")
print("%-46s %-6s %-9s %-9s %s"%("panel","slowest","2 months","3 months","errors at 2 months"))
rows=[]
for r in range(1,5):
  for names in itertools.combinations(LAG,r):
    slow=max(LAG[n] for n in names)
    for back,fwd in [(180,30),(180,60),(240,30)]:
      for how in ["nearest","earlier"]:
        e2=score(names,ALARM,PKM,"max",back,fwd,how,2)
        e3=score(names,ALARM,PKM,"max",back,fwd,how,3)
        rows.append((e2[0],-slow,names,back,fwd,how,e2,e3))
rows.sort(reverse=True)
seen=set()
for ex,negslow,names,back,fwd,how,e2,e3 in rows:
    k=(tuple(names),)
    if k in seen: continue
    seen.add(k)
    print("%-46s %-6d %-9s %-9s %s"%(" + ".join(n[:16] for n in names),-negslow,
          "%d of 9"%e2[0],"%d of 9"%e3[0],e2[2]))
    if len(seen)>=12: break
print("\nADVANCE TROUGH — every panel, one and two months after the end call")
print("%-46s %-6s %-9s %-9s %s"%("panel","slowest","1 month","2 months","errors at one month"))
rows2=[]
for r in range(1,5):
  for names in itertools.combinations(LAG,r):
    slow=max(LAG[n] for n in names)
    for back,fwd in [(300,30),(300,60),(365,30)]:
      for how in ["nearest","earlier"]:
        e1=score(names,ENDC2,TRM,"min",back,fwd,how,1)
        e2=score(names,ENDC2,TRM,"min",back,fwd,how,2)
        rows2.append((e1[0],-slow,names,back,fwd,how,e1,e2))
rows2.sort(reverse=True)
seen=set()
for ex,negslow,names,back,fwd,how,e1,e2 in rows2:
    k=(tuple(names),)
    if k in seen: continue
    seen.add(k)
    print("%-46s %-6d %-9s %-9s %s"%(" + ".join(n[:16] for n in names),-negslow,
          "%d of 9"%e1[0],"%d of 9"%e2[0],e1[2]))
    if len(seen)>=12: break
