import pandas as pd, random
P=F=0
def rd(s):
    d=pd.read_csv(f'a20/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
def chk(lab,got,want,tol=1e-9,claim=None):
    global P,F
    ok=(got==want) if isinstance(want,(str,bool,tuple)) else abs(got-want)<=tol
    print(("PASS " if ok else "FAIL ")+f"{lab}: got={got!r} want={want!r}"+("" if ok else f"  << {claim}"))
    P,F=(P+1,F) if ok else (P,F+1)
sc=rd('SAHMCURRENT'); md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
def eps(s,thr=0.50):
    out=[];cur=[]
    for d,v in s.items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    return out
E=eps(sc); W=[]
for pk,tr in zip(PK,TR):
    p=pd.Timestamp(pk+'-01'); t=pd.Timestamp(tr+'-01')
    c=[e for e in E if e[0]>=p and e[0]<=t+pd.DateOffset(months=12)]
    W.append((t,sc[c[0][0]:c[0][-1]+pd.DateOffset(months=12)]))
lens=[len(w) for _,w in W]
chk("window lengths span 24 to 40",(min(lens),max(lens)),(24,40),0,"between twenty-four and forty months")
within=[sum(1 for d in w.index if abs(md(d,t))<=3) for t,w in W]
chk("at most seven months inside the tolerance",max(within),7,0,"at most seven lie within three months")
probs=[a/b for a,b in zip(within,lens)]
chk("mean per-window chance ~23%",round(100*sum(probs)/len(probs)),23,0,"about twenty-three percent")
pall=1.0
for x in probs: pall*=x
chk("joint chance ~1 in 60 million",round(1/pall/1e6),59,1,"roughly one in sixty million")
worst=0
for k in (-24,-18,-12,-6,6,12,18,24):
    worst=max(worst,sum(1 for t,w in W if abs(md(w.idxmax(),t+pd.DateOffset(months=k)))<=3))
chk("displaced troughs return at most one hit",worst,1,0,"at most one hit in twelve")
def sahm(u):
    ub=u.rolling(3).mean(); return (ub-ub.shift(1).rolling(12).min()).dropna()
u=rd('M0892AUSM156SNBR'); s=sahm(u)
chk("pre-1948 unemployment starts April 1929",u.index[0].strftime('%Y-%m'),'1929-04',0,"available from April 1929")
def bris(s,pk,tr):
    p=pd.Timestamp(pk); t=pd.Timestamp(tr); Ee=eps(s)
    c=[e for e in Ee if e[0]>=p and e[0]<=t+pd.DateOffset(months=12)]
    w=s[c[0][0]:c[0][-1]+pd.DateOffset(months=12)]
    return md(w.idxmax(),t)
chk("1937-38 gap is +1",bris(s,'1937-05-01','1938-06-01'),1,0,"one month after the trough")
chk("1929-33 gap is -8",bris(s,'1929-08-01','1933-03-01'),-8,0,"eight months before it")
chk("1929-33 ran 43 months",md(pd.Timestamp('1933-03-01'),pd.Timestamp('1929-08-01')),43,0,"forty-three months")
t=open('paper_v6_full.md').read()
for x in ["between twenty-four and forty months","roughly one in sixty million","at most one hit in twelve",
          "in 1937–38 the rule places the peak one month after the trough","forty-three months against a twelve-month lookback",
          "nothing in this paper tests it beyond them"]:
    chk(f"text: {x[:44]}",x in t,True,0,"edit landed")
print(f"\nPASSED {P}  FAILED {F}")
