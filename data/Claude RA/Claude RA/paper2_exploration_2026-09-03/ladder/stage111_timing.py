"""Stage 111: a breadth of fifteen series is worse than claims alone because the series
bottom at very different times.  Measure each one's timing against the NBER trough, then
build the breadth from the coincident subset only."""
exec(open("stage110_endrule2.py").read().split('def run2(')[0])
import numpy as np, pandas as pd
print("%-26s %s" % ("series","month of its worst reading, less the NBER trough month, per recession"))
tim={}
for kk,(a,d) in sorted(SER.items()):
    errs=[]
    for (on,tr),cl in zip(EPS,CLOSE):
        i0=int(np.where(cal==pd.Timestamp(on))[0][0]); i1=int(np.where(cal==pd.Timestamp(cl))[0][0])
        w=a[i0:i1+1]
        if np.isfinite(w).sum()<30: errs.append(None); continue
        j=(np.nanargmax(w) if d=="up" else np.nanargmin(w))+i0
        t=pd.Timestamp(tr); m=cal[j]
        errs.append((m.year-t.year)*12+(m.month-t.month))
    ok=[e for e in errs if e is not None]
    tim[kk]=(np.median(np.abs(ok)) if ok else 99, errs)
    print("%-26s %s   median |error| %.1f" % (kk,errs,tim[kk][0]))
good=[k for k,(m,e) in tim.items() if m<=1.5]
print("\ncoincident subset (median |error| <= 1.5 months): %s" % good)
def run3(sub,k=2,q=0.60,minser=3):
    out=[]
    for (on,tr),cl in zip(EPS,CLOSE):
        i0=int(np.where(cal==pd.Timestamp(on))[0][0]); i1=int(np.where(cal==pd.Timestamp(cl))[0][0])
        avail=[kk for kk in sub if np.isfinite(SER[kk][0][max(i0-380,0):i0]).sum()>60]
        worst={kk:(-np.inf if SER[kk][1]=="up" else np.inf) for kk in avail}; wi={kk:i0 for kk in avail}
        ec=None
        for i in range(i0,i1+1):
            nt=na=0
            for kk in avail:
                a,d=SER[kk]; x=a[i]
                if not np.isfinite(x): continue
                na+=1
                if (d=="up" and x>worst[kk]) or (d=="dn" and x<worst[kk]): worst[kk]=x; wi[kk]=i
                per=7 if ("claims" in kk or "insured" in kk) else 30
                if (i-wi[kk])>=k*per and wi[kk]>i0: nt+=1
            if na>=minser and ec is None and nt/na>=q: ec=i
        wm=[cal[wi[kk]] for kk in avail if wi[kk]>i0]
        trough=pd.Series(wm).median() if wm else pd.NaT
        out.append((str(cal[ec].date()) if ec else None, str(pd.Timestamp(trough).to_period("M")) if pd.notna(trough) else None, tr))
    return out
def sc3(rows):
    el=[];te=[]
    for e,t,nb in rows:
        if not e: return None,None
        T=pd.Timestamp(nb); E=pd.Timestamp(e)
        el.append((E.year-T.year)*12+(E.month-T.month))
        m=pd.Period(t,"M").to_timestamp(); te.append((m.year-T.year)*12+(m.month-T.month))
    return el,te
print("\n%-24s %-32s %-30s %s" % ("subset breadth","end lags","trough errors","total |error|"))
res=[]
for k in (1,2,3):
    for q in (0.50,0.60,0.75,1.00):
        el,te=sc3(run3(good,k,q))
        if el is None: continue
        tot=sum(abs(x) for x in el)+sum(abs(x) for x in te)
        res.append((tot,k,q,el,te)); print("%-24s %-32s %-30s %d" % ("k=%d q=%.0f%%"%(k,100*q),str(el),str(te),tot))
res.sort()
print("\nv11 for comparison: end lags [1,2,0,0,2,1,-1,1,1] + troughs [0,0,0,-1,1,0,-2,1,0] = 14")
