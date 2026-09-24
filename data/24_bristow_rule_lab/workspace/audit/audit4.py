import pandas as pd, numpy as np
def L(n):
    d=pd.read_csv(n+'.csv',parse_dates=['observation_date']); d.columns=['date','v']
    d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().reset_index(drop=True)
OK=[];FAIL=[]
def chk(l,g,w,tol=1e-9):
    ok=abs(g-w)<=tol if isinstance(w,(int,float)) and isinstance(g,(int,float)) else g==w
    (OK if ok else FAIL).append(f"{'PASS' if ok else 'FAIL'} | {l} | got={g} claimed={w}")
def note(l,v): OK.append(f"VAL  | {l} = {v}")

f=L('FEDFUNDS').set_index('date').v
chk("FEDFUNDS Feb 2022 = 0.08", float(f['2022-02-01']), 0.08, 0.001)
chk("FEDFUNDS peak 5.33", round(float(f['2023-08-01':'2024-08-01'].max()),2), 5.33, 0.001)
chk("FEDFUNDS Aug 2024 = 5.33", float(f['2024-08-01']), 5.33, 0.001)
chk("FEDFUNDS Sep 2024 = 5.13 (first cut)", float(f['2024-09-01']), 5.13, 0.001)
chk("17-month rise to Aug2023", round(float(f['2023-08-01']-f['2022-03-01']),2), 5.13, 0.001)
fr=f.reset_index(); fr['d17']=fr.v-fr.v.shift(17)
prior=fr[(fr.date<'2022-01-01')&(fr.d17>=5.13)]
chk("last prior 17-mo rise >=5.13 = Jun 1981", prior.date.max().strftime('%Y-%m'), '1981-06')
chk("none 1982-2021", len(fr[(fr.date>='1982-01-01')&(fr.date<='2021-12-01')&(fr.d17>=5.13)]), 0)

w=L('WALCL').set_index('date').v
chk("WALCL peak value (millions)", int(w.max()), 8965487)
chk("WALCL peak date", w.idxmax().strftime('%Y-%m-%d'), '2022-04-13')
chk("WALCL peak ~ $8.97T", round(w.max()/1e6,2), 8.97, 0.005)

c=L('CPIAUCNS').set_index('date').v
yoy=(c/c.shift(12)-1)*100
chk("CPI YoY Nov 2021 = 6.8", round(float(yoy['2021-11-01']),1), 6.8, 0.05)
chk("CPI YoY Dec 2021 = 7.0", round(float(yoy['2021-12-01']),1), 7.0, 0.05)
chk("CPI YoY Jun 2022 = 9.1", round(float(yoy['2022-06-01']),1), 9.1, 0.05)
pre=yoy[:'2021-01-01']
chk("last >=7.04 before = Jun 1982", pre[pre>=float(yoy['2021-12-01'])].index.max().strftime('%Y-%m'), '1982-06')
chk("last >=9.06 before = Nov 1981", pre[pre>=float(yoy['2022-06-01'])].index.max().strftime('%Y-%m'), '1981-11')
chk("CPI YoY mean 2017-2019 = 2.1", round(float(yoy['2017-01-01':'2019-12-01'].mean()),1), 2.1, 0.05)

# SOS
d=L('IURSA'); d['ma26']=d.v.rolling(26).mean(); d['sos']=(d.ma26-d.ma26.rolling(52).min()).round(4)
plat=d[(d.sos==0.2000)&(d.date>='2023-01-01')&(d.date<='2023-12-31')]
chk("SOS plateau weeks = 11", len(plat), 11)
chk("SOS plateau first week", plat.date.min().strftime('%Y-%m-%d'), '2023-09-02')
chk("SOS plateau last week", plat.date.max().strftime('%Y-%m-%d'), '2023-11-11')
chk("SOS never exceeds 0.20 in 2023", float(d[(d.date>='2023-01-01')&(d.date<='2023-12-31')].sos.max()), 0.20, 0.0001)
chk("SOS latest (week ending Aug 15 2026) = 0.0", float(d[d.date=='2026-08-15'].sos.iloc[0]), 0.0, 0.0001)
RECS=[("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),
      ("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
exceeded=0
for p,t in RECS:
    w2=d[(d.date>=p)&(d.date<=pd.Timestamp(t)+pd.DateOffset(months=6))]
    if (w2.sos>0.20).any(): exceeded+=1
chk("SOS exceeded 0.20 in all 7 in-sample recessions", exceeded, 7)
chk("IURSA starts Jan 1971", d.date.min().strftime('%Y-%m'), '1971-01')

# Vacancies
o=L('JTSJOL'); lf=L('CLF16OV'); m=o.merge(lf,on='date',suffixes=('_o','_l'))
m['vr']=100*m.v_o/m.v_l; m=m.set_index('date')
chk("JTSJOL peak level", int(m.v_o.max()), 12301)
chk("JTSJOL peak month", m.v_o.idxmax().strftime('%Y-%m'), '2022-03')
chk("Vacancy rate peak 7.5%", round(float(m.vr.max()),1), 7.5, 0.05)
chk("Aug 2024 openings 7.5mn", round(float(m.loc['2024-08-01','v_o'])/1000,1), 7.5, 0.05)
chk("Aug 2024 vacancy rate 4.5%", round(float(m.loc['2024-08-01','vr']),1), 4.5, 0.05)
chk("Openings decline 39%", round(100*(float(m.loc['2024-08-01','v_o'])/float(m.v_o.max())-1)), -39)
chk("Vacancy rate fall ~3pp", round(float(m.vr.max())-float(m.loc['2024-08-01','vr']),1), 3.0, 0.06)

# Michez recomputation
u=L('UNRATE').set_index('date').v
mm=m.join(u.rename('u'),how='inner')
mm['u3']=mm.u.rolling(3).mean(); mm['v3']=mm.vr.rolling(3).mean()
mm['uh']=mm.u3-mm.u3.rolling(12).min(); mm['vh']=mm.v3.rolling(12).max()-mm.v3
mm['mn']=mm[['uh','vh']].min(axis=1)
note("Michez recomputed 2023-12..2025-01", [(d.strftime('%Y-%m'),round(x,3)) for d,x in mm.loc['2023-12-01':'2025-01-01','mn'].items()])
chk("Michez recomputed peak month", mm.loc['2024-01-01':'2024-12-01','mn'].idxmax().strftime('%Y-%m'), '2024-08')
chk("Michez recomputed peak value 0.53", round(float(mm.loc['2024-01-01':'2024-12-01','mn'].max()),2), 0.53, 0.006)
note("vacancy channel vh through 2024", [(d.strftime('%Y-%m'),round(x,2)) for d,x in mm.loc['2024-01-01':'2024-12-01','vh'].items()])
chk("vh min in 2024 >= 0.92", round(float(mm.loc['2024-01-01':'2024-12-01','vh'].min()),2), 0.92, 0.005)
chk("vh max in 2024 <= 1.06", round(float(mm.loc['2024-01-01':'2024-12-01','vh'].max()),2), 1.06, 0.006)
print("\n".join(OK)); print(); print("\n".join(FAIL) if FAIL else "NO FAILURES IN BLOCK 4")
