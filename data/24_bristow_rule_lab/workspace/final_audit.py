import pandas as pd, numpy as np, re
D='/home/claude/audit/'
def L(n):
    d=pd.read_csv(D+n+'.csv',parse_dates=['observation_date']); d.columns=['date','v']
    d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().reset_index(drop=True)
paper=open('/home/claude/paper_v6_full.md',encoding='utf8').read()
F=[];P=0
def chk(lab,got,want,tol=1e-9,claim_in_paper=None):
    global P
    if claim_in_paper is not None and claim_in_paper not in paper:
        F.append(f"TEXT-MISS | {lab} | paper does not contain: {claim_in_paper[:70]}"); return
    ok=abs(got-want)<=tol if isinstance(want,(int,float)) and isinstance(got,(int,float)) else got==want
    if ok: P+=1
    else: F.append(f"FAIL | {lab} | got={got} claimed={want}")

t=L('T10Y2Y'); t['neg']=t.v<0
runs=[];st=None
for i,r in t.iterrows():
    if r.neg and st is None: st=i
    if not r.neg and st is not None: runs.append((t.date[st],t.date[i-1],i-st,t.v[st:i].min(),t.v[st:i].sum())); st=None
r22=[r for r in runs if r[0]==pd.Timestamp('2022-07-06')][0]
chk("537 days",r22[2],537,0,"537 consecutive trading days")
chk("end date",r22[1].strftime('%Y-%m-%d'),'2024-08-26',0,"August 26, 2024")
chk("trough",round(r22[3],2),-1.08,0,"−1.08")
chk("423",sorted(runs,key=lambda x:-x[2])[1][2],423,0,"423")
chk("-2.41 (series minimum; no longer cited in the paper)",round(t.v.min(),2),-2.41,0)
chk("-1.70 (1980-81 trough; no longer cited in the paper)",round([r for r in runs if r[0]==pd.Timestamp('1980-09-12')][0][3],2),-1.70,0)
chk("area -259",round(r22[4]),-259,0,"−259")
chk("area -304",round(min(r[4] for r in runs)),-304,0,"−304")
chk("1998 neg days",int((t[(t.date>='1998-01-01')&(t.date<='1998-12-31')].v<0).sum()),27,0,"27 trading days between May 26 and July 27, 1998")
chk("no neg 1976-78",int((t[(t.date<'1978-08-01')].v<0).sum()),0,0,"records no negative day before August 1978")

g=L('GDPC1'); g['a']=((g.v/g.v.shift(1))**4-1)*100; g=g.set_index('date')
i_=L('A261RX1Q020SBEA'); i_['a']=((i_.v/i_.v.shift(1))**4-1)*100; i_=i_.set_index('date')
chk("GDP 22Q1",round(g.loc['2022-01-01','a'],1),-1.0,0.05,"Q1 −1.0%")
chk("GDP 22Q2",round(g.loc['2022-04-01','a'],1),0.6,0.05,"Q2 +0.6%")
chk("GDI 22Q2",round(i_.loc['2022-04-01','a'],1),-0.3,0.05)
chk("GDI 22Q4",round(i_.loc['2022-10-01','a'],1),-2.3,0.05)
chk("GDP 03Q3",round(g.loc['2003-07-01','a'],1),6.8,0.05,"6.8 percent annual rate")

pi=L('W875RX1').set_index('date').v; ms=L('CMRMTSPL').set_index('date').v; ip=L('INDPRO').set_index('date').v
chk("PI ex tr",round(100*(pi['2022-06-01']/pi['2021-12-01']-1),1),-1.7,0.05,"declined 1.7 percent")
chk("mfg sales",round(100*(ms['2022-06-01']/ms['2022-01-01']-1),1),-2.6,0.05,"fell 2.6 percent")
chk("IP dd",round(100*(ip['2024-01-01']/ip['2022-04-01']-1),1),-2.2,0.05,"2.2 percent below")

sc=L('SAHMCURRENT').set_index('date').v; sr=L('SAHMREALTIME').set_index('date').v
for m,c,r in [('2024-07-01',0.50,0.53),('2024-08-01',0.57,0.57),('2024-09-01',0.53,0.50)]:
    chk(f"cur {m[:7]}",round(float(sc[m]),2),c,0.001); chk(f"rt {m[:7]}",round(float(sr[m]),2),r,0.001)
chk("2022 Sahm max",round(float(sc['2022-01-01':'2022-12-01'].max()),2),0.03,0.001,"never rose above 0.03")
chk("2023 Sahm max",round(float(sc['2023-01-01':'2023-12-01'].max()),2),0.30,0.001,"peaked at 0.30")
mi=pd.read_csv('/home/claude/m_recession_indicator.csv',parse_dates=['Date']); mi.columns=['date','m']; mi=mi.set_index('date').m
chk("2022 Michez max",round(float(mi['2022-01-01':'2022-12-01'].max()),2),0.04,0.001,"never above 0.04")
chk("2023 Michez max",round(float(mi['2023-01-01':'2023-12-01'].max()),2),0.26,0.001,"at 0.26")
chk("Michez Mar24",round(float(mi['2024-03-01']),2),0.29,0.001,"March 2024")
chk("Michez peak",round(float(mi['2024-01-01':'2024-12-01'].max()),2),0.54,0.001,"0.54")
chk("Michez 15mo",int((mi['2024-03-01':'2025-05-01']>=0.29).sum()),15,0,"fifteen consecutive months")
py=L('PAYEMS').set_index('date').v
chk("payrolls H1 22",round(100*(py['2022-06-01']/py['2021-12-01']-1),1),1.7,0.05,"rose 1.7 percent in the first half")

REC=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),("1969-12","1970-11"),
     ("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),
     ("2007-12","2009-06"),("2020-02","2020-04")]
gaps=[];peaks=[]
for p,tr in REC:
    p=pd.Timestamp(p);tr=pd.Timestamp(tr); w=sc[p:tr+pd.DateOffset(months=12)]
    mx=w.max(); pk=w[w==mx].index[0]; gaps.append((pk.year-tr.year)*12+(pk.month-tr.month)); peaks.append(mx)
chk("12/12 within 3",all(abs(x)<=3 for x in gaps),True,0,"within three months of the NBER trough in all twelve")
chk("median signed 1.5",float(np.median(gaps)),1.5,0,"median gap is a month and a half")
chk("median abs 2.0",float(np.median([abs(x) for x in gaps])),2.0,0,"taken without sign, the median is two months")
chk("smallest peak",round(min(peaks),2),1.50,0.001,"1.50, in 1990–91")
lags=[]
for p,tr in REC:
    p=pd.Timestamp(p);tr=pd.Timestamp(tr); w=sc[p:tr+pd.DateOffset(months=6)]; c=w[w>=0.50]
    if p>=pd.Timestamp('1953-01-01'): lags.append((c.index[0].year-p.year)*12+(c.index[0].month-p.month))
chk("lag 1-8 median 3",(min(lags),max(lags),float(np.median(lags))),(1,8,3.0),0,"one and eight months after")

o=L('JTSJOL').set_index('date').v; lf=L('CLF16OV').set_index('date').v
chk("openings peak",int(o.max()),12301,0,"12.3 million")
chk("openings Aug24",round(float(o['2024-08-01'])/1000,1),7.5,0.05,"7.5 million")
chk("drop 39pct",round(100*(o['2024-08-01']/o.max()-1)),-39,0,"39 percent")
import warnings; warnings.filterwarnings('ignore')
off=pd.read_excel('/home/claude/sos.xlsx',sheet_name='Data')[['Date','SOS indicator']]
off.columns=['date','sos']; off=off.dropna().set_index('date').sos
d=L('IURSA').set_index('date').v
mine=d.rolling(26).mean()-d.rolling(26).mean().shift(1).rolling(52).min()
j=pd.concat([mine.rename('m'),off.rename('o')],axis=1,sort=True).dropna()
chk("SOS formula reproduces official series",float((j.m-j.o).abs().max())<1e-9,True,0,"reproduces the Federal Reserve Bank of Richmond's own published SOS series exactly")
chk("SOS official obs count",len(off),2826,0,"2,826 weekly observations")
n23=off['2023-01-01':'2023-12-31'].round(4)
plat=n23[n23==0.2]
chk("SOS 12 weeks",len(plat),12,0,"twelve weeks")
chk("SOS window",(plat.index.min().strftime('%b %-d'),plat.index.max().strftime('%b %-d')),('Sep 2','Nov 18'),0,"September 2 through November 18, 2023")
chk("SOS never exceeds 0.20 in 2023",bool((n23>0.2).any()),False,0)
chk("SOS latest 0.0",round(float(off.iloc[-1]),4),0.0,1e-9,"0.0 as of the week ending August 15, 2026")
u3s=L('UNRATE').set_index('date').v.rolling(3).mean()
rep=(u3s-u3s.shift(1).rolling(12).min()).round(2)
jj=pd.concat([rep.rename('m'),sc.rename('o')],axis=1,sort=True).dropna()
chk("Sahm formula reproduces FRED in 923 of 928",int((jj.m-jj.o).abs().lt(1e-9).sum()),923,0,"923 of the 928 months")
u=L('UNRATE').set_index('date').v
for lab,dt,v in [("3.4 Apr23",'2023-04-01',3.4),("4.2 Jul24",'2024-07-01',4.2),("4.5 Nov25",'2025-11-01',4.5),("4.4 Dec25",'2025-12-01',4.4),("6.7 Jan86",'1986-01-01',6.7),("4.0 Oct67",'1967-10-01',4.0),("3.6 Nov66",'1966-11-01',3.6),("6.3 Jun03",'2003-06-01',6.3),("5.5 Nov01",'2001-11-01',5.5)]:
    chk(lab,float(u[dt]),v,0.001)
f=L('FEDFUNDS').set_index('date').v
chk("ff Feb22",float(f['2022-02-01']),0.08,0.001,"0.08 percent in February 2022")
chk("ff 17mo",round(float(f['2023-08-01']-f['2022-03-01']),2),5.13,0.001,"5.13 percentage points")
w=L('WALCL').set_index('date').v
chk("walcl",(round(w.max()/1e6,2),w.idxmax().strftime('%Y-%m-%d')),(8.97,'2022-04-13'),0,"April 13, 2022")
c=L('CPIAUCNS').set_index('date').v; yoy=(c/c.shift(12)-1)*100
chk("cpi Nov21",round(float(yoy['2021-11-01']),1),6.8,0.05,"6.8 percent")
chk("cpi Dec21",round(float(yoy['2021-12-01']),1),7.0,0.05,"7.0 percent by December")
chk("cpi Jun22",round(float(yoy['2022-06-01']),1),9.1,0.05,"9.1 percent")
chk("cpi 17-19",round(float(yoy['2017-01-01':'2019-12-01'].mean()),1),2.1,0.05,"2.1 percent")
g10=L('GS10').set_index('date').v; g1=L('GS1').set_index('date').v; sp=(g10-g1).dropna()
chk("1966 all neg",bool((sp['1966-01-01':'1966-12-01']<0).all()),True,0,"all twelve months of 1966")
print(f"CHECKS PASSED: {P}")
print(f"FAILURES: {len(F)}")
for x in F: print("  ",x)
