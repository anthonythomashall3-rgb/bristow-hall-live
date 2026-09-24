"""Stage 109: the breadth end rule, built and swept.
A series has TURNED when its smoothed value has retraced R percent of the distance from
its worst reading in this episode back toward its pre-recession level.  The end is called
when a quorum of the available series has turned.  The trough is the MEDIAN month across
series of their worst reading -- a median, not one series' argmax, so revisions move it far
less."""
exec(open("stage108_endbreadth.py").read().split('print("series available')[0])
import numpy as np, pandas as pd
LAG={"w":5,"m":35}
SM ={"w":4,"m":3}
def prep():
    out={}
    for k,(s,f,d) in CAND.items():
        v=s.rolling(SM[f]).mean()
        v.index=v.index+pd.Timedelta(days=LAG[f])
        a=v.reindex(cal).ffill().values.astype(float)
        out[k]=(a,d)
    return out
SER=prep()
EPS=[("1969-10-06","1970-11-01"),("1973-10-25","1975-03-01"),("1980-01-03","1980-07-01"),
     ("1981-08-18","1982-11-01"),("1990-08-03","1991-03-01"),("2001-02-02","2001-11-01"),
     ("2008-01-04","2009-06-01"),("2020-02-28","2020-04-01"),("2024-05-03","2024-08-01")]
CLOSE=["1972-02-04","1976-05-07","1981-08-07","1983-10-07","1993-03-05","2003-02-07","2010-09-03","2021-07-02","2025-01-10"]
def run(R=0.20, q=0.60, minser=6):
    rows=[]
    for (on,tr),cl in zip(EPS,CLOSE):
        i0=int(np.where(cal==pd.Timestamp(on))[0][0]); i1=int(np.where(cal==pd.Timestamp(cl))[0][0])
        base={}; worst={}; wi={}
        avail=[k for k,(a,d) in SER.items() if np.isfinite(a[max(i0-380,0):i0]).sum()>60]
        for k in avail:
            a,d=SER[k]; pre=np.nanmedian(a[max(i0-380,0):i0])
            base[k]=pre; worst[k]=pre; wi[k]=i0
        endcall=None; turned_hist=[]
        for i in range(i0,i1+1):
            n_t=0; n_a=0
            for k in avail:
                a,d=SER[k]; x=a[i]
                if not np.isfinite(x): continue
                n_a+=1
                if (d=="up" and x>worst[k]) or (d=="dn" and x<worst[k]): worst[k]=x; wi[k]=i
                span=abs(worst[k]-base[k])
                if span<=0: continue
                back=(worst[k]-x) if d=="up" else (x-worst[k])
                if back>=R*span: n_t+=1
            if n_a>=minser:
                frac=n_t/n_a; turned_hist.append((i,frac))
                if endcall is None and frac>=q: endcall=i
        wm=[cal[wi[k]] for k in avail if wi[k]>i0]
        trough=pd.Series(wm).median() if wm else pd.NaT
        rows.append(dict(onset=on,nber_trough=tr,end_call=str(cal[endcall].date()) if endcall else None,
                         trough=str(pd.Timestamp(trough).to_period("M")) if pd.notna(trough) else None))
    return rows
def score(rows):
    el=[]; te=[]; miss=0
    for r in rows:
        if r["end_call"] is None: miss+=1; continue
        t=pd.Timestamp(r["nber_trough"]); e=pd.Timestamp(r["end_call"])
        el.append((e.year-t.year)*12+(e.month-t.month))
        if r["trough"]:
            m=pd.Period(r["trough"],"M").to_timestamp()
            te.append((m.year-t.year)*12+(m.month-t.month))
    return el,te,miss
print("current v11 end rule:  end lags [1, 2, 0, 0, 2, 1, -1, 1, 1]  trough errors [0, 0, 0, -1, 1, 0, -2, 1, 0]  (2 withdrawn calls in history)")
print("\n%-16s %-32s %-32s %s" % ("R / quorum","end lags (months after trough)","trough errors","missed")) 
best=[]
for R in (0.10,0.15,0.20,0.25,0.30,0.40):
    for q in (0.50,0.60,0.70,0.80):
        rows=run(R,q); el,te,miss=score(rows)
        if miss: continue
        sc=(sum(abs(x) for x in el), sum(abs(x) for x in te))
        best.append((sc[0]+sc[1],R,q,el,te))
        print("%-16s %-32s %-32s %d" % ("%.2f / %.0f%%"%(R,100*q), str(el), str(te), miss))
best.sort()
if best:
    tot,R,q,el,te=best[0]
    print("\nbest: retrace %.0f%%, quorum %.0f%%  -> end lags %s (sum |lag| %d)  trough errors %s (sum %d)"
          % (100*R,100*q,el,sum(abs(x) for x in el),te,sum(abs(x) for x in te)))
