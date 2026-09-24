"""Stage 187: the American record before 1948.  The ninety-five per cent lower bound on the
detection rate is 0.05^(1/n) in the number of episodes, so it is seventy-nine per cent on
thirteen recessions and no improvement to the rule can raise it.  Only more episodes can.  The
NBER dated seventeen further American recessions between 1877 and 1945, and the NBER's own
macrohistory database -- pig iron from 1877, steel ingots from 1899, railway freight from 1907,
construction and department store sales from the 1910s -- is on FRED.  The rule is unchanged:
every line is that series' own quiet record plus a quarter of its own robust standard deviation."""
import os, glob, json
import numpy as np, pandas as pd
D="/root/fetch/nber/"
SEL=json.load(open(D+"selected.json")) if os.path.exists(D+"selected.json") else {}
NBER=[("1882-03","1885-05"),("1887-03","1888-04"),("1890-07","1891-05"),("1893-01","1894-06"),
      ("1895-12","1897-06"),("1899-06","1900-12"),("1902-09","1904-08"),("1907-05","1908-06"),
      ("1910-01","1912-01"),("1913-01","1914-12"),("1918-08","1919-03"),("1920-01","1921-07"),
      ("1923-05","1924-07"),("1926-10","1927-11"),("1929-08","1933-03"),("1937-05","1938-06"),
      ("1945-02","1945-10")]
def rd(p):
    s=pd.read_csv(p,parse_dates=["date"]).set_index("date")["value"]
    return pd.to_numeric(s,errors="coerce").dropna().sort_index()
S={}
for p in sorted(glob.glob(D+"*.csv")):
    sid=os.path.basename(p)[:-4]
    if sid=="selected": continue
    s=rd(p)
    if len(s)<240: continue
    S[sid]=s
print("series loaded: %d"%len(S))
IDX=pd.DatetimeIndex(pd.date_range("1877-01-01","1948-12-01",freq="MS"))
EPS=[(pd.Timestamp(a+"-01"),pd.Timestamp(b+"-01")) for a,b in NBER]
q=pd.Series(True,index=IDX)
for P,T in EPS: q &= ~((IDX>=P-pd.DateOffset(months=6))&(IDX<=T+pd.DateOffset(months=9)))
def chan(s):
    v=s.reindex(IDX,method="ffill")
    if (v.dropna()<=0).any(): d=-(v-v.shift(1))
    else: d=-(v/v.shift(1)-1)*100
    a=pd.concat([d,d.shift(1)],axis=1).min(axis=1)
    if (v.dropna()<=0).any(): b=-(v-v.shift(6))
    else: b=-(v/v.shift(6)-1)*100
    return {"1m":a,"6m":b}
CH={}
for sid,s in S.items():
    if s.index.min()>pd.Timestamp("1935-01-01"): continue
    for k,x in chan(s).items(): CH[sid+" "+k]=x
print("channels built: %d"%len(CH))
def run(delta,minobs=60):
    hit=pd.Series(False,index=IDX); used=0
    for k,x in CH.items():
        v=x[q].dropna()
        if len(v)<minobs: continue
        med=float(np.median(v)); mad=float(np.median(np.abs(v-med)))*1.4826
        if not np.isfinite(mad) or mad<=0: continue
        z=(x-med)/mad; rec=float(z[q].dropna().max())
        first=x.dropna().index.min()
        ok=pd.Series(IDX>=first+pd.DateOffset(years=5),index=IDX)
        hit=hit|(((z>=rec+delta)&ok).reindex(IDX).fillna(False)); used+=1
    hits=list(IDX[hit.values])
    det=[];lags=[]
    for P,T in EPS:
        w=[h for h in hits if P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=9)]
        det.append(bool(w)); lags.append((w[0].to_period("M")-P.to_period("M")).n if w else None)
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=250: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[str(a.date())[:7] for a,b in runs if not any(P-pd.DateOffset(months=6)<=a<=T+pd.DateOffset(months=9) for P,T in EPS)]
    return det,lags,fa,used,float(q.sum())/12.0
print("\n%-8s %-8s %-12s %-24s %s"%("margin","channels","detected","false alarms","lags in months from the peak"))
for delta in [0.25,0.5,1.0,1.5,2.0,3.0]:
    det,lags,fa,used,qy=run(delta)
    print("%-8.2f %-8d %-12s %-24s %s"%(delta,used,"%d of %d"%(sum(det),len(EPS)),
          "%d in %.0f quiet years"%(len(fa),qy),[l for l in lags]))
    if len(fa)<=8 and fa: print("         false: %s"%fa)
