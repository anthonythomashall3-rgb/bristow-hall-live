import pandas as pd, numpy as np, re
P=F=0
def rd(s):
    d=pd.read_csv(f'a10/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
def chk(lab,got,want,tol=1e-9,claim=None):
    global P,F
    ok=(got==want) if isinstance(want,(str,bool,tuple)) else abs(got-want)<=tol
    print(("PASS " if ok else "FAIL ")+f"{lab}: got={got!r} want={want!r}"+("" if ok else f"  << {claim}"))
    P,F=(P+1,F) if ok else (P,F+1)

t=open('paper_v6_full.md').read()
abst=t.split('## Abstract')[1].split('\n---')[0]
concl=t.split('## 10. Conclusion')[1].split('\n---')[0]
u=rd('UNRATE'); sc=rd('SAHMCURRENT'); sr=rd('SAHMREALTIME'); rec=rd('USREC')
jo=rd('JTSJOL'); cp=rd('CPIAUCNS')
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)

print("== abstract/conclusion restatements against the data ==")
chk("Sahm crossed Jul 2024 both vintages",(round(float(sc['2024-07-01']),2)>=0.50,round(float(sr['2024-07-01']),2)>=0.50),(True,True),0,"crossed its threshold in July 2024")
chk("peak Aug 2024 = 0.57 both",(round(float(sc['2024-08-01']),2),round(float(sr['2024-08-01']),2)),(0.57,0.57),0,"peaked that August at 0.57 ... alike")
chk("openings -39%",round(100*(float(jo['2024-08-01'])/float(jo['2022-03-01'])-1)),-39,0,"job openings fell 39 percent")
chk("episode length Apr->Aug 2024 = 4 months",md(pd.Timestamp('2024-08-01'),pd.Timestamp('2024-04-01')),4,0,"four months")
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
dur=[md(pd.Timestamp(TR[i]+'-01'),pd.Timestamp(PK[i]+'-01')) for i in range(12)]
chk("4 months briefer than all but 2020",tuple(sorted(d for d in dur if d<4)),(2,),0,"briefer than any postwar predecessor except the pandemic's")
peaks=[]
for p,tr in zip(PK,TR):
    w=sc[pd.Timestamp(p+'-01'):pd.Timestamp(tr+'-01')+pd.DateOffset(months=12)]
    if len(w): peaks.append(float(w.max()))
chk("mildest: 0.57 < smallest in-recession peak 1.50",(round(float(sc['2024-08-01']),2),round(min(peaks),2)),(0.57,1.50),0,"the mildest on record")
chk("0.57 is 'barely more than a third' of 1.50",round(0.57/1.50,2),0.38,0.005,"barely more than a third")
chk("77 years screened 1949-2026",2026-1949,77,0,"seventy-seven years of data")
chk("67 years of real-time record",round((sr.index[-1]-sr.index[0]).days/365.25),67,0,"sixty-seven years")
chk("classifier: 1929-2021 = 92 years",2021-1929,92,0,"ninety-two years")
# the only >1-month real-time non-tail, non-early-warning episode
ir=rec.reindex(sr.index).fillna(0); fl=(sr>=0.50)&(ir==0)
eps=[];cur=[]
for d,f in fl.items():
    if f: cur.append(d)
    elif cur: eps.append(cur); cur=[]
if cur: eps.append(cur)
trs=[pd.Timestamp(x+'-01') for x in TR]; pks=[pd.Timestamp(x+'-01') for x in PK]
multi=[e for e in eps if len(e)>1
       and not any(0<=md(e[0],x)<=1 for x in trs)
       and not any(0<=md(x,e[-1])<=5 for x in pks)]
chk("2024 is the only >1-month non-tail non-warning real-time episode",
    (len(multi),multi[0][0].strftime('%Y-%m') if multi else None),(1,'2024-07'),0,
    "the only crossing of more than one month ... neither the lagging tail ... nor an early warning")
chk("2017-19 min unrate 3.5",round(float(u['2017-01-01':'2019-12-01'].min()),1),3.5,0.001,"fell to 3.5 percent")
pre=u[u.index<pd.Timestamp('2017-01-01')]
chk("lowest since Dec 1969",pre[pre<=3.5].index.max().strftime('%Y-%m'),'1969-12',0,"lowest level since December 1969")
yoy=(cp/cp.shift(12)-1)*100
chk("2017-19 CPI avg 2.1",round(float(yoy['2017-01-01':'2019-12-01'].mean()),1),2.1,0.05,"averaging about 2.1 percent")

print("\n== abstract/conclusion consistency with the body ==")
chk("no 'each strand is now corroborated'","each strand is now corroborated" in t,False,0,"overclaimed corroboration")
chk("no 'a sustained one never has'","a sustained one never has" in t,False,0,"contradicted the paper's own finding")
chk("abstract drops 'in the same window'","reached the same conclusion in the same window" in t,False,0,"classifier readings are 2025")
chk("Sec 7 lead states the difference","whose published readings fall in 2025" in t,True,0,"Section 7 lead precision")
for phrase in ["April to August 2024","537 consecutive trading days","fifteen consecutive months",
               "seventy-seven years","sixty-seven years","ninety-two years","39 percent","0.57"]:
    chk(f"'{phrase}' used consistently",t.count(phrase)>=2,True,0,"restated term appears in body and summary")
print(f"\nPASSED {P}  FAILED {F}")
