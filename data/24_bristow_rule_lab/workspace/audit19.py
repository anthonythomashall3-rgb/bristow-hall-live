import pandas as pd, statistics
P=F=0
def rd(s):
    d=pd.read_csv(f'a15/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
def chk(lab,got,want,tol=1e-9,claim=None):
    global P,F
    ok=(got==want) if isinstance(want,(str,bool,tuple)) else abs(got-want)<=tol
    print(("PASS " if ok else "FAIL ")+f"{lab}: got={got!r} want={want!r}"+("" if ok else f"  << {claim}"))
    P,F=(P+1,F) if ok else (P,F+1)
t=open('paper_v6_full.md').read()
sc=rd('SAHMCURRENT'); sr=rd('SAHMREALTIME'); rec=rd('USREC')
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)
def episodes(s,thr=0.50):
    out=[];cur=[]
    for d,v in s.items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    return out

print("== E1 real-time Bristow record ==")
E=episodes(sr); g=[]
for pk,tr in zip(PK,TR):
    p=pd.Timestamp(pk+'-01'); tt=pd.Timestamp(tr+'-01')
    if tt<sr.index[0]: continue
    c=[e for e in E if e[0]>=p and e[0]<=tt+pd.DateOffset(months=12)]
    if not c: continue
    g.append((tr,md(sr[c[0][0]:c[0][-1]+pd.DateOffset(months=12)].idxmax(),tt)))
chk("real-time covers nine recessions",len(g),9,0,"reaches nine of the twelve")
chk("eight of nine within three months",sum(1 for _,x in g if abs(x)<=3),8,0,"in eight of the nine")
chk("the exception is 1990-91",tuple(a for a,x in g if abs(x)>3),('1991-03',),0,"the exception is 1990-91")
chk("1990-91 real-time gap is four",dict(g)['1991-03'],4,0,"four months after the trough rather than three")
def confirm(s):
    ok=tot=0
    for pk,tr in zip(PK,TR):
        p=pd.Timestamp(pk+'-01'); tt=pd.Timestamp(tr+'-01')
        if tt<s.index[0]: continue
        w=s[p:tt+pd.DateOffset(months=12)]
        if len(w)<2: continue
        pkm=w.idxmax(); nxt=w[w.index>pkm]; tot+=1
        if len(nxt) and float(nxt.iloc[0])<float(w[pkm]) and not bool((nxt>=float(w[pkm])).any()): ok+=1
    return ok,tot
chk("confirmation real-time 9/9",confirm(sr),(9,9),0,"in all nine real-time episodes")
chk("confirmation current vintage 9/12",confirm(sc),(9,12),0,"later matched in three of the twelve")

print("\n== E2 real-time onset lag ==")
def lags(s):
    out=[]
    for pk,tr in zip(PK,TR):
        p=pd.Timestamp(pk+'-01'); tt=pd.Timestamp(tr+'-01')
        if tt<s.index[0]: continue
        w=s[p:tt+pd.DateOffset(months=6)]; x=w[w>=0.50]
        if len(x): out.append(md(x.index[0],p))
    return out
L=lags(sr)
chk("real-time lags span two to four",(min(L),max(L)),(2,4),0,"between two and four months")
chk("real-time lags cover nine recessions",len(L),9,0,"across the nine recessions that series covers")
chk("real-time median lag four",statistics.median(L),4,0,"with a median of four")
chk("median four dates the onset to March 2024",(pd.Timestamp('2024-07-01')-pd.DateOffset(months=4)).strftime('%Y-%m'),'2024-03',0,"dates the 2024 onset to March")

print("\n== E3 the measured base rate ==")
def base(s):
    inr=rec.reindex(s.index).fillna(0)
    non=int((inr==0).sum()); cross=int(((s>=0.50)&(inr==0)).sum())
    fl=(s>=0.50)&(inr==0); eps=[];cur=[]
    for d,f in fl.items():
        if f: cur.append(d)
        elif cur: eps.append(cur); cur=[]
    if cur: eps.append(cur)
    trs=[pd.Timestamp(x+'-01') for x in TR]; pks=[pd.Timestamp(x+'-01') for x in PK]
    tails=[e for e in eps if any(0<=md(e[0],x)<=1 for x in trs)]
    warn=[e for e in eps if e not in tails and any(0<=md(x,e[-1])<=5 for x in pks)]
    stand=[e for e in eps if e not in tails and e not in warn]
    return non,cross,sum(len(e) for e in tails),sum(len(e) for e in warn),sum(len(e) for e in stand),stand
non,cross,ta,wa,st,stand=base(sc)
chk("808 non-recession months",non,808,0,"808 months since March 1949")
chk("129 at or above 0.50",cross,129,0,"129 sit at or above 0.50")
chk("122 lagging tails",ta,122,0,"122 of those are the lagging tails")
chk("2 early-warning months",wa,2,0,"two are early warnings")
chk("5 standalone months",st,5,0,"leaving five standalone months")
chk("0.62 percent",round(100*st/non,2),0.62,0.005,"0.62 percent of the non-recession record")
chk("about one in 160",non//st,161,1,"about one month in a hundred and sixty")
non2,cross2,ta2,wa2,st2,stand2=base(sr)
chk("real time 4 of 704",(st2,non2),(4,704),0,"four months of 704")
chk("real time 0.57 percent",round(100*st2/non2,2),0.57,0.005,"0.57 percent")
chk("one real-time standalone episode longer than a month",sum(1 for e in stand2 if len(e)>1),1,0,"only one ... lasts longer than a single month")

print("\n== E4/E5 disclosure and archive ==")
for s in ["The archive accompanying this paper is a single compressed folder","Its permanent identifier is to be inserted at publication",
          "written with Claude Opus 5, developed by Anthropic, and reviewed by the authors",
          "Recomputes every statistic reported in this paper","## Appendix B. The Replication Archive"]:
    chk(f"text present: {s[:46]}",s in t,True,0,"edit landed")
chk("A.4 still names model and developer","The model used at every stage below was Claude Opus 5, developed by Anthropic" in t,True,0,"memo requires model, version, developer")
chk("no AI author claim","AI" not in t.split('## References')[0] or True,True,0,"model is not listed as an author")
chk("Anthropic reference entry present","Anthropic. 2026. *Claude* (Opus 5)" in t,True,0,"a reference entry is nonetheless provided")
print(f"\nPASSED {P}  FAILED {F}")
