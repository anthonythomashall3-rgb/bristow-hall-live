import pandas as pd, statistics
def rd(s):
    d=pd.read_csv(f'a15/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
sc=rd('SAHMCURRENT'); sr=rd('SAHMREALTIME')
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)
def episodes(s,thr=0.50,merge=0):
    raw=[];cur=[]
    for d,v in s.items():
        if v>=thr: cur.append(d)
        elif cur: raw.append(cur); cur=[]
    if cur: raw.append(cur)
    if merge<=0: return raw
    out=[]
    for e in raw:
        if out and md(e[0],out[-1][-1])<=merge: out[-1]=out[-1]+e
        else: out.append(list(e))
    return out
def run(series,merge,label):
    E=episodes(series,merge=merge); gaps=[]
    for pk,tr in zip(PK,TR):
        p=pd.Timestamp(pk+'-01'); t=pd.Timestamp(tr+'-01')
        if t < series.index[0]: continue
        cand=[e for e in E if e[0]>=p and e[0]<=t+pd.DateOffset(months=12)]
        if not cand: continue
        e=cand[0]
        d=series[e[0]:e[-1]+pd.DateOffset(months=12)].idxmax()
        gaps.append((tr,md(d,t),d.strftime('%Y-%m')))
    n=len(gaps); ok=sum(1 for _,g,_ in gaps if abs(g)<=3)
    worst=max(abs(g) for _,g,_ in gaps)
    print(f"  {label:38s} merge<={merge}: {ok}/{n} within 3, worst |gap| {worst}   {[(a,g) for a,g,_ in gaps]}")
    return ok,n,worst
print("Bristow Rule, operational window, varying the episode-merge tolerance")
print("(a gap of k months or fewer between crossing runs is treated as one episode)\n")
for m in (0,1,2,3,4,6):
    run(sc,m,"current vintage, all twelve")
print()
for m in (0,1,2,3,4,6):
    run(sr,m,"real time, nine from 1961")
print("\nNBER-anchored window, for reference:")
for series,lab in [(sc,'current vintage'),(sr,'real time')]:
    gaps=[]
    for pk,tr in zip(PK,TR):
        p=pd.Timestamp(pk+'-01'); t=pd.Timestamp(tr+'-01')
        if t<series.index[0]: continue
        w=series[p:t+pd.DateOffset(months=12)]
        if len(w)==0: continue
        gaps.append((tr,md(w.idxmax(),t)))
    print(f"  {lab:20s} {sum(1 for _,g in gaps if abs(g)<=3)}/{len(gaps)} within 3, worst {max(abs(g) for _,g in gaps)}   {gaps}")
