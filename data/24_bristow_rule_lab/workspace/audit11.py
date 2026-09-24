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

print("== TABLE A1: span retrieved, all 19 series ==")
SPAN={'UNRATE':('1948-01','2026-07'),'T10Y2Y':('1976-06','2026-08'),
 'GS10':('1953-04','2026-07'),'GS1':('1953-04','2026-07'),
 'GDPC1':('1947-01','2026-04'),'A261RX1Q020SBEA':('1947-01','2026-04'),
 'W875RX1':('1959-01','2026-07'),'CMRMTSPL':('1967-01','2026-06'),
 'INDPRO':('1919-01','2026-07'),'PAYEMS':('1939-01','2026-07'),
 'JTSJOL':('2000-12','2026-06'),'CLF16OV':('1948-01','2026-07'),
 'IURSA':('1971-01','2026-08'),'FEDFUNDS':('1954-07','2026-07'),
 'CPIAUCNS':('1913-01','2026-07'),'WALCL':('2002-12','2026-08'),
 'SAHMREALTIME':('1959-12','2026-07'),'SAHMCURRENT':('1949-03','2026-07'),
 'USREC':('1854-12','2026-07')}
for s,(a,b) in SPAN.items():
    x=rd(s); chk(f"A1 {s}",(x.index[0].strftime('%Y-%m'),x.index[-1].strftime('%Y-%m')),(a,b),0,"Table A1 span")

print("\n== TABLE 1: inversion episodes and NBER outcomes ==")
t10=rd('T10Y2Y'); g10=rd('GS10'); g1=rd('GS1'); rec=rd('USREC')
sp=(g10-g1).dropna()
# NBER episodes from USREC
r=rec[rec.index>=pd.Timestamp('1946-01-01')]
eps=[];inr=False
for d,v in r.items():
    if v==1 and not inr: st=d; inr=True
    elif v==0 and inr: eps.append((st,prev)); inr=False
    prev=d
NB={f"{a.strftime('%b %Y')}-{b.strftime('%b %Y')}" for a,b in eps}
chk("NBER episodes from USREC (post-1945 count)",len(eps),12,0,"twelve postwar recessions")
for a,b in eps: print(f"    NBER: {a.strftime('%b %Y')} – {b.strftime('%b %Y')}")
# pre-1976 monthly 10Y-1Y first negative month of each named episode
# pre-1976 rows are episode labels, not first-negative months (stated in the Table 1 note)
chk("T1 1966 episode: negative Dec 1965 - Feb 1967",
    (sp['1965-06':'1967-06'][sp['1965-06':'1967-06']<0].index[0].strftime('%Y-%m'),
     sp['1965-06':'1967-06'][sp['1965-06':'1967-06']<0].index[-1].strftime('%Y-%m')),
    ('1965-12','1967-02'),0,"turned negative in December 1965 and stayed negative through February 1967")
chk("T1 1968-69 episode negative before Dec 1969 peak",
    bool((sp['1968-01':'1969-11']<0).any()),True,0,"inverted ahead of the 1969-70 recession")
chk("T1 1973 first negative month",sp['1972-06':'1974-06'][sp['1972-06':'1974-06']<0].index[0].strftime('%Y-%m'),'1973-03',0,"Table 1 row 1973")
chk("1966 all twelve months negative",bool((sp['1966-01':'1966-12']<0).all()),True,0,"all twelve months of 1966")
# post-1976 T10Y2Y episode starts: first negative day in each named month
def firstneg(lo,hi):
    w=t10[lo:hi]; n=w[w<0]
    return n.index[0] if len(n) else None
for lab,lo,hi,want in [("Aug 1978",'1976-06-01','1979-12-31','1978-08'),
                       ("Sep 1980",'1980-08-01','1981-12-31','1980-09'),
                       ("Dec 1988",'1985-01-01','1989-12-31','1988-12'),
                       ("Feb 2000",'1999-01-01','2000-12-31','2000-02'),
                       ("Dec 2005",'2003-01-01','2006-12-31','2005-12'),
                       ("Aug 2019",'2008-01-01','2019-12-31','2019-08')]:
    d=firstneg(lo,hi); chk(f"T1 {lab} first negative day",d.strftime('%Y-%m'),want,0,f"Table 1 row {lab}")
chk("T1 2022 durable inversion start",firstneg('2022-05-01','2023-12-31').strftime('%Y-%m-%d'),'2022-07-06',0,"Jul 6, 2022")
chk("no dated recession after Apr 2020",bool((rec[rec.index>pd.Timestamp('2020-04-01')]==1).any()),False,0,"None dated")
chk("Aug 2019 is first negative since 2007",firstneg('2008-01-01','2019-12-31').strftime('%Y-%m'),'2019-08',0,"Aug 2019 episode")

print("\n== TABLE 2: every cell ==")
u=rd('UNRATE'); sc=rd('SAHMCURRENT'); sr=rd('SAHMREALTIME'); g=rd('GDPC1'); gdi=rd('A261RX1Q020SBEA')
pi=rd('W875RX1'); ms=rd('CMRMTSPL'); ip=rd('INDPRO'); jo=rd('JTSJOL'); lf=rd('CLF16OV')
ga=lambda s:(s/s.shift(1))**4-1
chk("T2 GDP Q1 2022 current -1.0",round(float(ga(g)['2022-01-01'])*100,1),-1.0,0.05,"Q1 −1.0%")
chk("T2 GDP Q2 2022 current +0.6",round(float(ga(g)['2022-04-01'])*100,1),0.6,0.05,"Q2 +0.6%")
chk("T2 GDI Q2 2022 -0.3",round(float(ga(gdi)['2022-04-01'])*100,1),-0.3,0.05,"Q2 −0.3%")
chk("T2 GDI Q4 2022 -2.3",round(float(ga(gdi)['2022-10-01'])*100,1),-2.3,0.05,"Q4 −2.3%")
chk("T2 PILT -1.7 Dec21->Jun22",round(100*(float(pi['2022-06-01'])/float(pi['2021-12-01'])-1),1),-1.7,0.05,"−1.7%")
chk("T2 mfg/trade -2.6 Jan22->Jun22",round(100*(float(ms['2022-06-01'])/float(ms['2022-01-01'])-1),1),-2.6,0.05,"−2.6%")
chk("T2 IP peak Apr 2022",ip['2021-06-01':'2024-12-01'].idxmax().strftime('%Y-%m'),'2022-04',0,"Peak Apr 2022")
chk("T2 IP trough Jan 2024",ip['2022-05-01':'2024-12-01'].idxmin().strftime('%Y-%m'),'2024-01',0,"Jan 2024 trough")
chk("T2 IP -2.2 to trough",round(100*(float(ip['2024-01-01'])/float(ip['2022-04-01'])-1),1),-2.2,0.05,"−2.2%")
chk("T2 openings 12.3mn Mar 2022",round(float(jo['2022-03-01'])/1000,1),12.3,0.05,"12.3 mn (Mar 2022)")
chk("T2 openings peak month is Mar 2022",jo.idxmax().strftime('%Y-%m'),'2022-03',0,"12.3 mn (Mar 2022)")
chk("T2 openings 7.5mn Aug 2024",round(float(jo['2024-08-01'])/1000,1),7.5,0.05,"7.5 mn (Aug 2024)")
v=jo/lf*100
chk("T2 vacancy rate 7.5 -> 4.5",(round(float(v['2022-03-01']),1),round(float(v['2024-08-01']),1)),(7.5,4.5),0,"7.5% → 4.5%")
for m,rt,cv in [('2024-07-01',0.53,0.50),('2024-08-01',0.57,0.57),('2024-09-01',0.50,0.53)]:
    chk(f"T2 Sahm rt {m[:7]}",round(float(sr[m]),2),rt,0.001,"real-time row")
    chk(f"T2 Sahm cur {m[:7]}",round(float(sc[m]),2),cv,0.001,"current-vintage row")
mi=pd.read_csv('dash_new.csv'); mi.columns=['date','m']; mi['date']=pd.to_datetime(mi.date); mi=mi.set_index('date')['m']
chk("T2 Michez 0.29 Mar 2024",round(float(mi['2024-03-01']),2),0.29,0.001,"Reaches 0.29 in Mar 2024")
chk("T2 Michez peak 0.54 Aug 2024",(round(float(mi['2024-01-01':'2024-12-01'].max()),2),mi['2024-01-01':'2024-12-01'].idxmax().strftime('%Y-%m')),(0.54,'2024-08'),0,"peaks 0.54 in Aug 2024")
chk("T2 unrate Jul 2024 revised 4.2",round(float(u['2024-07-01']),1),4.2,0.001,"Revised to 4.2%")
chk("T2 unrate Nov 2025 4.5",round(float(u['2025-11-01']),1),4.5,0.001,"4.5% by Nov 2025")
print(f"\nPASSED {P}  FAILED {F}")

print("\n== never-fired instruments, named series and thresholds ==")
for s,lab in [('CFNAIMA3','CFNAI-MA3'),('RECPROUSM156N','Chauvet-Piger'),('JHGDPBRINDX','Hamilton')]:
    x=rd(s); w=x['2022-01-01':'2026-07-01']
    if s=='CFNAIMA3':
        chk("CFNAI-MA3 min -0.39",round(float(w.min()),2),-0.39,0.001,"never fell past -0.39")
        chk("CFNAI-MA3 never <= -0.70",bool((w<=-0.70).any()),False,0,"the -0.70 line")
    if s=='RECPROUSM156N': chk("Chauvet-Piger max 2.3",round(float(w.max()),1),2.3,0.05,"never exceeded 2.3 percent")
    if s=='JHGDPBRINDX':
        chk("Hamilton max 37.4",round(float(w.max()),1),37.4,0.05,"peaked at 37.4")
        chk("Hamilton never >= 67",bool((w>=67).any()),False,0,"rises above 67%")
up=rd('DFEDTARU'); lo=rd('DFEDTARL')
chk("target range +5.25pp upper",round(float(up['2023-08-01']-up['2022-03-01']),2),5.25,0.001,"5.25 percentage points of target-range increases")
chk("target range +5.25pp lower",round(float(lo['2023-08-01']-lo['2022-03-01']),2),5.25,0.001,"5.25 percentage points of target-range increases")
cp=rd('CPIAUCNS'); yoy=(cp/cp.shift(12)-1)*100
chk("Dec 2021 7.0 fastest since Jun 1982",yoy[yoy.index<pd.Timestamp('2021-01-01')][lambda z:z>=float(yoy['2021-12-01'])].index.max().strftime('%Y-%m'),'1982-06',0,"the fastest pace since June 1982")
chk("Jun 2022 9.1 highest since Nov 1981",yoy[yoy.index<pd.Timestamp('2022-01-01')][lambda z:z>=float(yoy['2022-06-01'])].index.max().strftime('%Y-%m'),'1981-11',0,"the highest since November 1981")
print(f"\nPASSED {P}  FAILED {F}")
