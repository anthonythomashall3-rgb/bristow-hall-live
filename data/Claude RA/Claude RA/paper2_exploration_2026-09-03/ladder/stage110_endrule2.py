"""Stage 110: the breadth end rule, corrected.  'Retraced R% of the fall' is a RECOVERY
condition and fires months late.  The right analogue of the present rule is 'has stopped
setting new worsts': a series has TURNED when it has gone k releases without a new worst.
End when a quorum have turned; trough = the median month of the worsts."""
exec(open("stage109_endrule.py").read().split('def run(')[0])
import numpy as np, pandas as pd
STEP={"w":7,"m":30}
def run2(k=2, q=0.60, minser=6, mode="nonew"):
    rows=[]
    for (on,tr),cl in zip(EPS,CLOSE):
        i0=int(np.where(cal==pd.Timestamp(on))[0][0]); i1=int(np.where(cal==pd.Timestamp(cl))[0][0])
        avail=[kk for kk,(a,d) in SER.items() if np.isfinite(a[max(i0-380,0):i0]).sum()>60]
        worst={kk:(-np.inf if SER[kk][1]=="up" else np.inf) for kk in avail}
        wi={kk:i0 for kk in avail}; base={kk:np.nanmedian(SER[kk][0][max(i0-380,0):i0]) for kk in avail}
        endcall=None
        for i in range(i0,i1+1):
            n_t=0; n_a=0
            for kk in avail:
                a,d=SER[kk]; x=a[i]
                if not np.isfinite(x): continue
                n_a+=1
                if (d=="up" and x>worst[kk]) or (d=="dn" and x<worst[kk]): worst[kk]=x; wi[kk]=i
                fr=SER[kk][1]
                per=STEP["w" if kk.endswith("4wk") or "insured" in kk else "m"]
                if mode=="nonew":
                    if (i-wi[kk])>=k*per and wi[kk]>i0: n_t+=1
                else:
                    span=abs(worst[kk]-base[kk]); 
                    if span>0:
                        back=(worst[kk]-x) if d=="up" else (x-worst[kk])
                        if back>=k*span and wi[kk]>i0: n_t+=1
            if n_a>=minser and endcall is None and n_t/n_a>=q: endcall=i
        wm=[cal[wi[kk]] for kk in avail if wi[kk]>i0]
        trough=pd.Series(wm).median() if wm else pd.NaT
        rows.append(dict(end_call=str(cal[endcall].date()) if endcall else None,
                         trough=str(pd.Timestamp(trough).to_period("M")) if pd.notna(trough) else None,
                         nber_trough=tr))
    return rows
def sc(rows):
    el=[];te=[];miss=0
    for r in rows:
        if not r["end_call"]: miss+=1; continue
        t=pd.Timestamp(r["nber_trough"]); e=pd.Timestamp(r["end_call"])
        el.append((e.year-t.year)*12+(e.month-t.month))
        m=pd.Period(r["trough"],"M").to_timestamp(); te.append((m.year-t.year)*12+(m.month-t.month))
    return el,te,miss
print("v11 end rule: lags [1, 2, 0, 0, 2, 1, -1, 1, 1] sum|.|=9 ; troughs [0, 0, 0, -1, 1, 0, -2, 1, 0] sum|.|=5")
print("\n%-22s %-34s %-32s %s" % ("no new worst for k, quorum","end lags","trough errors","sum|lag|+sum|tr|"))
best=[]
for k in (1,2,3,4):
    for q in (0.50,0.60,0.70,0.80,0.90):
        rows=run2(k,q); el,te,miss=sc(rows)
        if miss or len(el)<9: continue
        tot=sum(abs(x) for x in el)+sum(abs(x) for x in te)
        best.append((tot,k,q,el,te))
        print("%-22s %-34s %-32s %d" % ("k=%d, %.0f%%"%(k,100*q), str(el), str(te), tot))
best.sort()
if best:
    tot,k,q,el,te=best[0]
    print("\nbest breadth rule: no new worst for %d releases, quorum %.0f%%" % (k,100*q))
    print("   end lags %s (sum %d) | trough errors %s (sum %d) | total %d  vs v11's 14"
          % (el,sum(abs(x) for x in el),te,sum(abs(x) for x in te),tot))
