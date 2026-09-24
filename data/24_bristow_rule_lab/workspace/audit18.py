import pandas as pd
def rd(s):
    d=pd.read_csv(f'a15/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
sc=rd('SAHMCURRENT'); sr=rd('SAHMREALTIME'); rec=rd('USREC')
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)
trs=[pd.Timestamp(x+'-01') for x in TR]; pks=[pd.Timestamp(x+'-01') for x in PK]
def analyse(s,lab):
    inr=rec.reindex(s.index).fillna(0)
    n_all=len(s); n_rec=int((inr==1).sum()); n_non=n_all-n_rec
    cross=(s>=0.50)
    n_cross_non=int((cross&(inr==0)).sum())
    fl=cross&(inr==0); eps=[];cur=[]
    for d,f in fl.items():
        if f: cur.append(d)
        elif cur: eps.append(cur); cur=[]
    if cur: eps.append(cur)
    tails=[e for e in eps if any(0<=md(e[0],t)<=1 for t in trs)]
    warn=[e for e in eps if e not in tails and any(0<=md(p,e[-1])<=5 for p in pks)]
    stand=[e for e in eps if e not in tails and e not in warn]
    n_stand_months=sum(len(e) for e in stand)
    print(f"--- {lab} ---")
    print(f"  months in sample                     {n_all}   ({s.index[0]:%Y-%m} to {s.index[-1]:%Y-%m})")
    print(f"  months NBER-dated as recession       {n_rec}")
    print(f"  months outside a dated recession     {n_non}")
    print(f"  of those, at or above 0.50           {n_cross_non}   ({100*n_cross_non/n_non:.1f}% of non-recession months)")
    print(f"     of which lagging tails            {sum(len(e) for e in tails)}")
    print(f"     of which early warnings           {sum(len(e) for e in warn)}")
    print(f"     STANDALONE                        {n_stand_months}   ({100*n_stand_months/n_non:.2f}% of non-recession months)")
    print(f"  standalone episodes                  {len(stand)}  {[(e[0].strftime('%Y-%m'),len(e)) for e in stand]}")
    print(f"  crossing episodes in total           {len(eps)+len([1 for p,t in zip(pks,trs) if ((s>=0.50)&(rec.reindex(s.index).fillna(0)==1)).any()])-0}")
    # episode-level: of all distinct crossing episodes anywhere, what share are standalone
    allfl=cross; ae=[];cur=[]
    for d,f in allfl.items():
        if f: cur.append(d)
        elif cur: ae.append(cur); cur=[]
    if cur: ae.append(cur)
    print(f"  all crossing episodes (any state)    {len(ae)}; standalone share {len(stand)}/{len(ae)} = {100*len(stand)/len(ae):.0f}%")
    # multi-month standalone only
    ms=[e for e in stand if len(e)>1]
    print(f"  standalone episodes longer than one month: {len(ms)}  {[(e[0].strftime('%Y-%m'),len(e)) for e in ms]}")
    print(f"  base rate of a standalone month      1 in {n_non//max(n_stand_months,1)} non-recession months\n")
analyse(sc,'current vintage (SAHMCURRENT, 1949-2026)')
analyse(sr,'real-time record (SAHMREALTIME, 1959-2026)')
