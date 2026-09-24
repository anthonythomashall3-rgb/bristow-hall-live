import pandas as pd, numpy as np
F=0; P=0
def rd(s):
    d=pd.read_csv(f'a10/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
def chk(lab,got,want,tol=1e-9,claim=None):
    global F,P
    ok = (got==want) if isinstance(want,(str,bool,tuple)) else abs(got-want)<=tol
    print(("PASS " if ok else "FAIL ")+f"{lab}: got={got!r} want={want!r}"+("" if ok else f"   << {claim}"))
    if ok: P+=1
    else: F+=1

u=rd('UNRATE'); sc=rd('SAHMCURRENT'); sr=rd('SAHMREALTIME'); rec=rd('USREC')
ff=rd('FEDFUNDS'); g=rd('GDPC1'); t10=rd('T10Y2Y')
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)

print("== Section 2: Bristow record ==")
gaps=[];peaks=[];pk_months=[];sd=[]
for p,tr in zip(PK,TR):
    p=pd.Timestamp(p+'-01'); tr=pd.Timestamp(tr+'-01')
    w=sc[p:tr+pd.DateOffset(months=12)]
    if len(w)==0: continue
    pm=w.idxmax(); gaps.append(md(pm,tr)); peaks.append(float(w.max())); pk_months.append(pm)
    d3=(sc-sc.shift(3))[p:tr+pd.DateOffset(months=12)]
    sd.append(md(d3.idxmax(),tr))
chk("coincide exactly (gap 0) count",sum(1 for x in gaps if x==0),4,0,"coincides exactly in 1949, 1954, 1980 and 2009")
coincide=[TR[i][:4] for i,x in enumerate(gaps) if x==0]
chk("coincide years",tuple(coincide),('1949','1954','1980','2009'),0,"1949, 1954, 1980 and 2009")
lag13=[TR[i][:4] for i,x in enumerate(gaps) if 1<=x<=3]
chk("lag 1-3 years",tuple(lag13),('1958','1961','1970','1975','1991','2001','2020'),0,"1958, 1961, 1970, 1975, 1991, 2001 and 2020")
leads=[(TR[i][:4],x) for i,x in enumerate(gaps) if x<0]
chk("exactly one lead",len(leads),1,0,"leads in exactly one case")
chk("lead is 1982 by 2",tuple(leads[0]) if leads else None,('1982',-2),0,"1981–82 ... two months before the November trough")
i82=TR.index('1982-11')
chk("1981-82 max value 2.50",round(peaks[i82],2),2.50,0.001,"maximum value of 2.50")
chk("1981-82 peak month Sep 1982",pk_months[i82].strftime('%Y-%m'),'1982-09',0,"first reached in September 1982")
w82=sc[pd.Timestamp('1981-07-01'):pd.Timestamp('1982-11-01')+pd.DateOffset(months=12)]
chk("2.50 matched again in Nov 1982",round(float(w82['1982-11-01']),2),2.50,0.001,"matched again in November")
chk("largest abs gap = 3",max(abs(x) for x in gaps),3,0,"largest absolute gap in the twelve is exactly three")
chk("largest gap is 1990-91",TR[[abs(x) for x in gaps].index(3)][:4],'1991',0,"in 1990–91")
chk("2nd deriv lands on trough in 5",sum(1 for x in sd if x==0),5,0,"lands exactly on the trough in five of the twelve")
chk("2nd deriv never >2 past trough",max(sd),2,0,"never runs more than two months past it")
# 24-month window breaks 1980
w80=sc[pd.Timestamp('1980-01-01'):pd.Timestamp('1980-07-01')+pd.DateOffset(months=24)]
chk("24-mo window breaks 1980",abs(md(w80.idxmax(),pd.Timestamp('1980-07-01')))>3,True,0,"Widen it to twenty-four and the 1980 case breaks")
chk("next recession NBER peak 12 mo after 1980 trough",md(pd.Timestamp('1981-07-01'),pd.Timestamp('1980-07-01')),12,0,"whose NBER peak, July 1981, falls twelve months after the 1980 trough")

print("\n== Section 2: onset lags ==")
lags=[]
for p,tr in zip(PK[1:],TR[1:]):
    p=pd.Timestamp(p+'-01'); tr=pd.Timestamp(tr+'-01')
    w=sc[p:tr+pd.DateOffset(months=6)]
    x=w[w>=0.50]
    if len(x): lags.append(md(x.index[0],p))
chk("11 recessions 1953-2020",len(lags),11,0,"eleven recessions from 1953 through 2020")
chk("mean 3.5",round(float(np.mean(lags)),1),3.5,0.05,"a mean of three and a half")
folds={round(float(np.median([l for j,l in enumerate(lags) if j!=i])),1) for i in range(len(lags))}
chk("LOO median 3 in every fold",tuple(sorted(folds)),(3.0,),0,"three months in every fold")

print("\n== Section 2: recession durations ==")
dur=[md(pd.Timestamp(TR[i]+'-01'),pd.Timestamp(PK[i]+'-01')) for i in range(11)]
chk("1948-2009 durations 6..18",(min(dur),max(dur)),(6,18),0,"between six and eighteen months")
chk("median duration 10",float(np.median(dur)),10.0,0,"a median of ten")
chk("2020 = 2 months",md(pd.Timestamp('2020-04-01'),pd.Timestamp('2020-02-01')),2,0,"at two months")

print("\n== Section 3: policy path ==")
chk("ff cycle peak 5.33",round(float(ff['2022-01-01':'2026-07-01'].max()),2),5.33,0.001,"its 5.33 percent peak")
pk=ff[ff>=5.33]
chk("5.33 held >12 months",len(pk)>12,True,0,"sat at its 5.33 percent peak for more than a year")
chk("still 5.33 in Aug 2024",round(float(ff['2024-08-01']),2),5.33,0.001,"where it still stood in August 2024")
chk("first cut Sep 2024",round(float(ff['2024-09-01']),2)<5.33,True,0,"The first cut came only in September 2024")
ch17=(ff-ff.shift(17)).dropna()
prev=ch17[(ch17.index<pd.Timestamp('2023-01-01'))&(ch17>=5.13)]
chk("last prior 17-mo >=5.13 ends Jun 1981",prev.index[-1].strftime('%Y-%m'),'1981-06',0,"the one ending in June 1981")

print("\n== Section 3: yield curve detail ==")
tt=t10.copy()
neg=tt[tt<0]
apr=neg[(neg.index>=pd.Timestamp('2022-04-01'))&(neg.index<=pd.Timestamp('2022-04-30'))]
chk("Apr 2022 two-day dip",tuple(d.strftime('%b %-d') for d in apr.index),('Apr 1','Apr 4'),0,"April 1 and 4, 2022")
after=tt[tt.index>pd.Timestamp('2024-08-26')]
# first date after which never negative again
lastneg=tt[(tt<0)].index.max()
chk("last negative day in series",lastneg.strftime('%Y-%m-%d'),'2024-09-05',0,"turned durably positive on September 6, 2024")
n98=tt[(tt.index.year==1998)&(tt<0)]
runs=[];cur=[]
alld=list(tt.index)
for d in n98.index:
    if cur and (alld.index(d)-alld.index(cur[-1]))==1: cur.append(d)
    else:
        if cur: runs.append(cur)
        cur=[d]
runs.append(cur)
chk("1998 four runs",len(runs),4,0,"in four separate runs")
chk("1998 longest 18",max(len(r) for r in runs),18,0,"the longest of eighteen days")
chk("1998 min -0.07",round(float(n98.min()),2),-0.07,0.001,"never deeper than −0.07")
chk("1998 span",(n98.index.min().strftime('%b %-d'),n98.index.max().strftime('%b %-d')),('May 26','Jul 27'),0,"between May 26 and July 27, 1998")

print("\n== Section 3: 1947 GDP ==")
ga=(g/g.shift(1))**4-1
chk("1947Q2 annual rate -1.1",round(float(ga['1947-04-01'])*100,1),-1.1,0.05,"1.1 ... percent in today's data")
chk("1947Q3 annual rate -0.8",round(float(ga['1947-07-01'])*100,1),-0.8,0.05,"0.8 percent")

print("\n== Section 4: early warnings and real-time ==")
chk("Nov 1959 cur 0.60",round(float(sc['1959-11-01']),2),0.60,0.001,"0.60")
chk("Dec 1959 cur 0.53",round(float(sc['1959-12-01']),2),0.53,0.001,"0.53")
chk("Nov 1959 is 5 mo before Apr 1960",md(pd.Timestamp('1960-04-01'),pd.Timestamp('1959-11-01')),5,0,"five months before")
chk("rt Dec 1959 0.77",round(float(sr['1959-12-01']),2),0.77,0.001,"0.77")
chk("rt Jan 1960 0.50",round(float(sr['1960-01-01']),2),0.50,0.001,"0.50")
chk("rt Dec59 is 4 mo before Apr 1960",md(pd.Timestamp('1960-04-01'),pd.Timestamp('1959-12-01')),4,0,"four months before")
chk("rt Oct 1969 0.50",round(float(sr['1969-10-01']),2),0.50,0.001,"a single month at 0.50")
chk("rt Oct69 2 mo before Dec 1969",md(pd.Timestamp('1969-12-01'),pd.Timestamp('1969-10-01')),2,0,"two months before")
chk("rt Nov 1976 0.50",round(float(sr['1976-11-01']),2),0.50,0.001,"November 1976 at 0.50")
chk("rt Jul 2003 0.47",round(float(sr['2003-07-01']),2),0.47,0.001,"peaked at 0.47 that July")
chk("rt Aug 2003 0.47",round(float(sr['2003-08-01']),2),0.47,0.001,"and August")
chk("rt 2003 never >=0.50",bool((sr['2003-01-01':'2003-12-01']>=0.50).any()),False,0,"never crossed")
chk("SAHMREALTIME starts Dec 1959",sr.index[0].strftime('%Y-%m'),'1959-12',0,"begins in December 1959")
# four real-time standalone/non-tail episodes
ir=rec.reindex(sr.index).fillna(0)
fl=(sr>=0.50)&(ir==0); eps=[];cur=[]
for d,f in fl.items():
    if f: cur.append(d)
    elif cur: eps.append(cur); cur=[]
if cur: eps.append(cur)
trs=[pd.Timestamp(x+'-01') for x in TR]
nontail=[e for e in eps if not any(0<=md(e[0],t_)<=1 for t_ in trs)]
chk("four real-time non-tail episodes",len(nontail),4,0,"exactly four episodes")
chk("2024 episode 3 months",len([e for e in nontail if e[0]==pd.Timestamp('2024-07-01')][0]),3,0,"three consecutive months")

print("\n== Section 5: Sahm path after 2024 ==")
chk("Aug 2025 = 0.13",round(float(sc['2025-08-01']),2),0.13,0.001,"easing to 0.13 by August 2025")
chk("late-2025 rise 0.35",round(float(sc['2025-09-01':'2025-12-01'].max()),2),0.35,0.001,"modest late-2025 rise to 0.35")
chk("Oct 2024 back below threshold",round(float(sc['2024-10-01']),2)<0.50,True,0,"fell back below the threshold in October 2024")
chk("highest reading after Oct 2024 = 0.40",round(float(sc['2024-10-01':'2026-07-01'].max()),2),0.40,0.001,"0.40 is its highest subsequent reading")
chk("Jul 2026 = -0.03",round(float(sc['2026-07-01']),2),-0.03,0.001,"falling to −0.03 by July 2026")
d3=(sc-sc.shift(3))
chk("2nd-deriv over the rule's own window peaks Aug 2024",d3['2024-07-01':'2025-09-01'].idxmax().strftime('%Y-%m'),'2024-08',0,"fastest three-month climb ends in August 2024")
# 2003 box under the two rules
w03=sc['2003-01-01':'2004-06-01']
first03=w03[w03>=0.50].index[0]
chk("2003 first crossing Jul 2003",first03.strftime('%Y-%m'),'2003-07',0,"onset April 2003")
chk("2003 onset = crossing - 3",(first03-pd.DateOffset(months=3)).strftime('%Y-%m'),'2003-04',0,"onset April 2003")
chk("2003 Bristow end Jul 2003 (ties to first)",sc['2003-01-01':'2004-06-01'].idxmax().strftime('%Y-%m'),'2003-07',0,"end July 2003")
chk("2003 Jul and Aug both 0.50",(round(float(sc['2003-07-01']),2),round(float(sc['2003-08-01']),2)),(0.50,0.50),0,"reads 0.50 in July and August alike")

print("\n== Section 10: 2017-19 benchmark ==")
chk("min unrate 2017-19 = 3.5",round(float(u['2017-01-01':'2019-12-01'].min()),1),3.5,0.001,"fell to 3.5 percent")
pre=u[u.index<pd.Timestamp('2017-01-01')]
chk("lowest since Dec 1969",pre[pre<=3.5].index.max().strftime('%Y-%m'),'1969-12',0,"lowest level since December 1969")

print(f"\nPASSED {P}  FAILED {F}")
