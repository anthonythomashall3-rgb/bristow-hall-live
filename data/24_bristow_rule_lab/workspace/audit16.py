import pandas as pd, numpy as np, statistics
def rd(s):
    d=pd.read_csv(f'a15/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
sc=rd('SAHMCURRENT'); sr=rd('SAHMREALTIME')
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)
def eps(s,thr=0.50):
    out=[];cur=[]
    for d,v in s.items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    return out

print("SAHMREALTIME begins",sr.index[0].strftime('%Y-%m'),"-> covers recessions with troughs from 1961 on\n")
print("="*74)
print("A. BRISTOW RULE ON THE REAL-TIME RECORD (operational window)")
print("="*74)
E=eps(sr)
rows=[]
for pk,tr in zip(PK,TR):
    p=pd.Timestamp(pk+'-01'); t=pd.Timestamp(tr+'-01')
    if t < sr.index[0]: continue
    cand=[e for e in E if e[0]>=p and e[0]<=t+pd.DateOffset(months=12)]
    if not cand:
        rows.append((tr,'NO CROSSING',None)); continue
    e=cand[0]
    d=sr[e[0]:e[-1]+pd.DateOffset(months=12)].idxmax()
    rows.append((tr,d.strftime('%Y-%m'),md(d,t)))
print(f"{'trough':10s} {'real-time Bristow':>18s} {'gap':>5s}   {'current-vintage':>16s} {'gap':>5s}")
rt_gaps=[]; cv_gaps=[]
Ec=eps(sc)
for tr,d,g in rows:
    t=pd.Timestamp(tr+'-01'); pk=PK[TR.index(tr)]
    cc=[e for e in Ec if e[0]>=pd.Timestamp(pk+'-01') and e[0]<=t+pd.DateOffset(months=12)]
    cd=sc[cc[0][0]:cc[0][-1]+pd.DateOffset(months=12)].idxmax() if cc else None
    cg=md(cd,t) if cd is not None else None
    if g is not None: rt_gaps.append(g)
    if cg is not None: cv_gaps.append(cg)
    flag='' if (g is not None and abs(g)<=3) else '   <<'
    print(f"{tr:10s} {d:>18s} {str(g):>5s}   {cd.strftime('%Y-%m') if cd is not None else '-':>16s} {str(cg):>5s}{flag}")
n=len(rt_gaps)
print(f"\nreal-time: {sum(1 for x in rt_gaps if abs(x)<=3)}/{n} within three months of the NBER trough")
print(f"  gaps {sorted(rt_gaps)}  median |gap| {statistics.median([abs(x) for x in rt_gaps])}  max |gap| {max(abs(x) for x in rt_gaps)}")
print(f"current vintage, same recessions: {sum(1 for x in cv_gaps if abs(x)<=3)}/{len(cv_gaps)} within three months")

print("\n"+"="*74)
print("B. ONSET LAG ON THE REAL-TIME RECORD")
print("="*74)
def lags(series):
    out=[]
    for pk,tr in zip(PK,TR):
        p=pd.Timestamp(pk+'-01'); t=pd.Timestamp(tr+'-01')
        if t < series.index[0]: continue
        w=series[p:t+pd.DateOffset(months=6)]; x=w[w>=0.50]
        if len(x): out.append((tr,md(x.index[0],p)))
    return out
lr=lags(sr); lc=lags(sc)
print("real-time lags:",[(a,b) for a,b in lr])
print("  n",len(lr),"median",statistics.median([b for a,b in lr]),"mean",round(statistics.mean([b for a,b in lr]),1),
      "range",min(b for a,b in lr),"-",max(b for a,b in lr))
lc2=[(a,b) for a,b in lc if pd.Timestamp(a+'-01')>=sr.index[0]]
print("current vintage, same recessions:",lc2)
print("  median",statistics.median([b for a,b in lc2]),"mean",round(statistics.mean([b for a,b in lc2]),1))
print("\nApril 2024 onset requires a lag of 3 from the July 2024 crossing.")
print("  real-time median lag ->",(pd.Timestamp('2024-07-01')-pd.DateOffset(months=int(statistics.median([b for a,b in lr])))).strftime('%Y-%m'))

print("\n"+"="*74)
print("C. THE CONFIRMATION STEP: 'confirmed one release later when the first decline prints'")
print("="*74)
ok=0; tot=0
for pk,tr in zip(PK,TR):
    p=pd.Timestamp(pk+'-01'); t=pd.Timestamp(tr+'-01')
    if t < sr.index[0]: continue
    cand=[e for e in E if e[0]>=p and e[0]<=t+pd.DateOffset(months=12)]
    if not cand: continue
    e=cand[0]; w=sr[e[0]:e[-1]+pd.DateOffset(months=12)]
    peak=w.idxmax()
    nxt=w[w.index>peak]
    tot+=1
    if len(nxt)==0:
        print(f"  {tr}: peak {peak.strftime('%Y-%m')} -> no later month in window"); continue
    declines = float(nxt.iloc[0])<float(w[peak])
    # does the peak survive: is any later month >= the peak?
    later_ge = bool((nxt>=float(w[peak])).any())
    if declines and not later_ge: ok+=1
    print(f"  {tr}: peak {peak.strftime('%Y-%m')} next month {'declines' if declines else 'does NOT decline'}; "
          f"peak {'holds' if not later_ge else 'is later matched or exceeded'}")
print(f"\nconfirmation holds in {ok} of {tot} real-time episodes")
w24=sr['2024-07-01':'2025-09-01']
p24=w24.idxmax()
print(f"\n2024 real-time: peak {p24.strftime('%Y-%m')} = {float(w24[p24]):.2f}; next month {float(w24[w24.index>p24].iloc[0]):.2f} -> "
      f"{'declines' if float(w24[w24.index>p24].iloc[0])<float(w24[p24]) else 'does not decline'}")
