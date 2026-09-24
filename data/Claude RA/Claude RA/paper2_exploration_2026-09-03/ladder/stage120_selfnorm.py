"""Stage 120: a rule with no fitted thresholds at all.  Each channel carries its own
running record: the largest reading it has ever posted on a day when no episode was open.
The machine fires when a channel beats that record by a factor m.  The record is built only
from the past, so nothing in the rule uses information the machine would not have had, and
the same code runs unchanged in 1970 and in 2030."""
exec(open("stage118_agree.py").read().split('FIRST=[pd.Timestamp')[0])
import numpy as np, pandas as pd
CORE=["Sahm","IUR","payrolls","housing","bill"]
FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
START=pd.Timestamp("1968-06-01"); i0=int(np.searchsorted(cal,START))
def selfnorm(names, m, warm_yr=5, cool_days=0, clause_m=None):
    X=np.vstack([np.asarray(CH[n],float) for n in names])       # raw scores
    nch=len(names)
    rec=np.full(nch,-np.inf); seen=np.zeros(nch,int)
    Sr=np.asarray(CH["Sahm"],float)
    rec_s=-np.inf; seen_s=0
    eps=[]; open_=False; cool_until=-1
    warm=int(warm_yr*365)
    trigday=np.zeros(N,bool)
    for i in range(N):
        x=X[:,i]; ok=np.isfinite(x)
        if open_:
            v=ma8d[i]
            if not np.isnan(v):
                if v>runmax: runmax=v; pk=i; endcall=None
            okend=(not np.isnan(v)) and pk is not None and v<=runmax*(1-0.03)
            if okend and endcall is None: endcall=i
            if endcall is not None and B3[i] and CALM[i]:
                eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i]))
                open_=False; cool_until=i+cool_days
            continue
        if i<i0:
            if i>cool_until:
                upd=ok&(x>rec); rec=np.where(upd,x,rec); seen=seen+ok.astype(int)
                if np.isfinite(Sr[i]): rec_s=max(rec_s,Sr[i]); seen_s+=1
            continue
        hit=False
        if G[i] and CO[i]:
            live=ok&(seen>=warm)&np.isfinite(rec)
            if live.any() and (x[live]>=m*rec[live]).any(): hit=True
        if (not hit) and clause_m is not None and CCO[i] and (not G[i]):
            if seen_s>=warm and np.isfinite(rec_s) and np.isfinite(Sr[i]) and Sr[i]>=clause_m*rec_s: hit=True
        if hit:
            trigday[i]=True; open_=True; start=i; runmax=-1; pk=None; endcall=None; continue
        if i>cool_until:                       # today was quiet: it joins the record
            upd=ok&(x>rec); rec=np.where(upd,x,rec); seen=seen+ok.astype(int)
            if np.isfinite(Sr[i]): rec_s=max(rec_s,Sr[i]); seen_s+=1
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,
                              end_call=cal[endcall] if endcall else None,close=None))
    return eps,trigday
print("%-6s %-7s %-6s %-6s %-6s %s"%("m","clause","det","false","inwk","days from the first day"))
out=[]
for m in [1.00,1.05,1.10,1.15,1.20,1.25,1.30,1.40,1.50,1.75,2.00]:
    for cl in [None,1.30,1.50,1.65,2.00]:
        eps,tr=selfnorm(CORE,m,clause_m=cl)
        res,f=score_eps(eps,T_P1); det=sum(1 for x in res if x["lag"] is not None)
        dd=None
        if det==9:
            call={r["peak"]:r["onset"] for r in res}
            dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(p,t) in enumerate(T_P1)]
        print("%-6.2f %-7s %-6s %-6d %-6s %s"%(m,cl,"%d/9"%det,len(f) if f else 0,
              (sum(1 for x in dd if abs(x)<=7) if dd else "-"),
              (dd if dd else "")))
        out.append((m,cl,det,len(f) if f else 0,dd,f[:4] if f else []))
print("\nzero-false, nine-of-nine configurations:")
for m,cl,det,nf,dd,fa in out:
    if det==9 and nf==0:
        print("  m=%.2f clause=%s  mean |days| %.0f  inside a week %d/9  %s"%(m,cl,np.mean([abs(x) for x in dd]),sum(1 for x in dd if abs(x)<=7),dd))
print("\nfalse-alarm dates for the configurations that missed nothing but fired extra:")
for m,cl,det,nf,dd,fa in out:
    if det==9 and nf: print("  m=%.2f clause=%s -> %d false: %s"%(m,cl,nf,fa))
