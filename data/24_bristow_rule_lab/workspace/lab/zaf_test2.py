"""HELD OUT, second pass: the SARB's own composite coincident business cycle indicator.

The SARB "identifies reference turning points in the business cycle according to the
growth cycle definition, which entails identifying turning points in the fluctuations
around the long-term trend of aggregate economic activity" (Quarterly Bulletin, September
2025), and the aggregate it publishes for that purpose is the composite coincident
business cycle indicator, monthly and seasonally adjusted, series DIFN002A, from January
1960.  This is the South African analogue of the KOSIS series Korea needs.

Nothing about South Africa entered any choice made in building the rule.  The
configuration is the shipped one, unchanged.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
ZA=[('1946-07','1947-04'),('1948-11','1950-02'),('1951-12','1953-03'),('1955-04','1956-09'),
    ('1958-01','1959-03'),('1960-04','1961-08'),('1965-04','1965-12'),('1967-05','1967-12'),
    ('1970-12','1972-08'),('1974-08','1977-12'),('1981-08','1983-03'),('1984-06','1986-03'),
    ('1989-02','1993-05'),('1996-11','1999-08'),('2007-11','2009-08'),('2013-11','2017-04'),
    ('2019-06','2020-04')]
co=load('/home/claude/lab/sarb/ZAF_coincident.csv')
oecd=load('/home/claude/lab/kei/ZAF_RS__T.csv')
def rtt(s,lam):
    y=np.log(s.dropna()); y=y[np.isfinite(y)]
    t=pd.Series(hp_filter(y.values,lam),index=y.index)
    return np.exp(y-t)*100.0
OBJ={'OECD reference series (ratio to trend)':oecd,
     "SARB's own coincident indicator, ratio to its HP trend":rtt(co,500000.0)}
for tag,ref in OBJ.items():
    hp_=ht=0; ep=[]; et=[]; rows=[]; n=0
    for pk_off,tr_off in ZA:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if ref.index.min()>w0 or ref.index.max()<trm: continue
        n+=1
        tr=ch_trough(ref,w0,w1,0.0,3,12,abstain=False)
        pk=ch_peak(ref,w0,tr if tr is not None else w1,0.0,3,abstain=False)
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
        hp_+=a; ht+=b
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    print(f'--- {tag}')
    for r in rows: print(f'      {r[0]} {str(r[1]):>5s}   {r[2]} {str(r[3]):>5s}')
    print(f'    {n} contractions: peaks {hp_}/{n} troughs {ht}/{n}  mean |error| '
          f'{np.mean(ep):.2f}/{np.mean(et):.2f}  within two {sum(1 for x in ep if x<=2)},'
          f'{sum(1 for x in et if x<=2)}')
