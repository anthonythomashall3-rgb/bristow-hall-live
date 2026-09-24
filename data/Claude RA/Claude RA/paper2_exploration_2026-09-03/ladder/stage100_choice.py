"""Stage 100: price the Sahm-form choice.  The 6-month/9-month form has 2.6x the margin
but re-dates three calls.  Unlike round 22's housing swap this is NOT free, so both sides
are put on one table for the authors to decide."""
exec(open("stage99_sahmsweep.py").read().split("out=[]")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
share=0.40
FIRST={"1969-12":"1970-01-01","1973-11":"1973-12-01","1980-01":"1980-02-01","1981-07":"1981-08-01",
       "1990-07":"1990-08-01","2001-03":"2001-04-01","2007-12":"2008-01-01","2020-02":"2020-03-01","2024-04":"2024-05-01"}
KEYS=list(FIRST)
def haz(v,thr,gated=True,floor=0.03):
    m=QC&(G if gated else np.ones(N,bool))&(CL>=floor)
    s=pd.Series(v[m],index=cal[m]).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return 0.0
    c,loc,sc=sst.genextreme.fit(am.values)
    ya=pd.Series(cal[QC&(G if gated else np.ones(N,bool))]).dt.year.nunique()
    return float(sst.genextreme.sf(thr,c,loc,sc))*(len(am)/max(ya,1))*(share if gated else 1-share)
def form(m_,L,th,k=1):
    mu=u.rolling(m_).mean(); gap=mu-mu.rolling(L).min().shift(1)
    g=pd.Series(gap.values,index=pd.to_datetime(rel.values)).dropna()
    a=(g>=th-1e-9)
    for j in range(1,k): a=a & g.shift(j).ge(th-1e-9)
    return np.asarray(D(a.fillna(False)),bool), g.reindex(cal).ffill().values.astype(float)
S312=Srel.reindex(cal).ffill().values.astype(float)
a69,v69=form(6,9,0.250)
rows=[]
for lab,arr,v,th in [("v10  Sahm 3m mean / 12m min >= 0.36",np.asarray(D(Srel>=0.36-1e-9),bool),S312,0.36),
                     ("alt  Sahm 6m mean /  9m min >= 0.25",a69,v69,0.250)]:
    d,l,e,f,n,armed=machine2(arr)
    q=v[QC&CO&G]; q=q[np.isfinite(q)]
    qm=float(np.max(q)); sdv=float(np.nanstd(q))
    hz=haz(v,th)
    dd=[(pd.Timestamp(str(x.date()))-pd.Timestamp(FIRST[KEYS[i]])).days for i,x in enumerate(d)]
    rows.append((lab,[str(x.date()) for x in d],l,dd,qm,th-qm,(th-qm)/sdv,hz,f,n,armed))
for lab,d,l,dd,qm,marg,msd,hz,f,n,armed in rows:
    print("\n%s" % lab)
    print("  onsets      %s" % d)
    print("  lags        %s" % l)
    print("  days from the recession's first day  %s" % dd)
    print("  quiet max %.3f | margin %.3f (%.2f sd) | fitted hazard %.5f/yr | false %s | no-inv %d/9 | quiet-armed %d"
          % (qm,marg,msd,hz,f if f else 0,n,armed))
h10={"Sahm":rows[0][7],"clause":0.00235,"bill":0.00180,"iur":0.0,"pay":0.0,"hou":0.0}
halt=dict(h10); halt["Sahm"]=rows[1][7]
u_=lambda dct: 1-np.prod([1-p for p in dct.values()])
print("\nunion hazard: v10 %.4f (1 in %.0f yr)  |  with the 6m/9m form %.4f (1 in %.0f yr)"
      % (u_(h10),1/u_(h10),u_(halt),1/max(u_(halt),1e-9)))
