"""Germany's one high-frequency activity object: the daily truck-toll mileage index.

Destatis publishes the digital process data of the truck-toll collection as a daily index
from 1 January 2008 (Statistischer Bericht 42191, updated every Thursday, five to twelve days
after the data; lab/acq/maut/, fetched 2 September 2026; the Bundesbank's calendar- and
seasonally-adjusted daily values, KSB, and the unadjusted ones).  The index moves with
industrial production and is the nearest German analogue of the American weekly claims file.
It reaches two Council contractions - the 2008-09 one only from its January 2008 peak month,
so that peak cannot be called (no trailing history), and 2020 at both ends - which is a
demonstration, not a record.

Read as weekly means of the adjusted daily values (Monday-Sunday), log x 100.  Trough: the
rule's level clause mirrored from the claims file (level_trough_calls on the negative log
level: arm when the series stands `arm` log points below its trailing 52-week maximum, fire
after `run` rising weeks and a rise of `drop` points from the minimum, date the trough at the
month of the minimum, publish seven days after the week).  Peak: the first week the 4-week
mean stands `band` log points below its trailing 52-week maximum after 26 weeks above,
published seven days after.  Every setting printed.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/weekly')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
x=pd.read_excel('/home/claude/lab/acq/maut/lkw_maut_daily_2026-08-22.xlsx',sheet_name='csv-42191-b01',header=0)
x.columns=['stat','geo','date','week','weekday','adj','value']
x['date']=pd.to_datetime(x['date']); x['value']=pd.to_numeric(x['value'],errors='coerce')
ksb=x[x.adj.str.contains('KSB')].set_index('date')['value'].dropna().sort_index()
raw=x[x.adj.str.contains('unbereinigt')].set_index('date')['value'].dropna().sort_index()
W=ksb.resample('W-SUN').mean().dropna()        # weekly means, week ending Sunday
DE_P=[pd.Timestamp('2008-01-01'),pd.Timestamp('2020-02-01')]; DE_T=[pd.Timestamp('2009-04-01'),pd.Timestamp('2020-04-01')]
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def mo(t): return pd.Timestamp(t.year,t.month,1)
if __name__=='__main__':
    print('daily index',ksb.index.min().date(),'->',ksb.index.max().date(),'; weekly means',len(W))
    N=(np.log(W)*100.0)
    print('\n=== troughs (level clause mirrored from the claims file), published +7 days; lag in days from the trough month\'s last day')
    for sm,arm,run,drop in itertools.product((4,8),(5.,10.,15.),(4,6,8),(1.,2.,3.)):
        s=(-N).rolling(sm).mean().dropna()       # a 'claims-like' series: high = deep
        G=s-s.rolling(52,min_periods=26).min()
        df=pd.concat([s.rename('n'),G.rename('g')],axis=1).dropna()
        n=df['n'].values; g=df['g'].values; idx=df.index; out=[]; state='quiet'; nmax=-1e9; ni=0; fall=0; prev=n[0]; off=0
        for i in range(1,len(n)):
            if n[i]>nmax: nmax=n[i]; ni=i; fall=0
            elif n[i]<prev: fall+=1
            else: fall=0
            prev=n[i]
            if state=='called':
                off=off+1 if g[i]<arm/2 else 0
                if off>=13: state='quiet'; off=0
                continue
            if state=='quiet':
                if g[i]>=arm: state='armed'; nmax=n[i]; ni=i; fall=0
                continue
            if fall>=run and (nmax-n[i])>=drop and g[ni]>=arm:
                out.append((idx[i]+pd.Timedelta(days=7),mo(idx[ni]))); state='called'; off=0
        rows=[]
        for tr in DE_T:
            c=[(p,d) for p,d in out if abs(md(d,tr))<=6]
            if c: p,d=min(c,key=lambda z:z[0]); end=(tr+pd.DateOffset(months=1))-pd.Timedelta(days=1); rows.append((tr.strftime('%Y-%m'),d.strftime('%Y-%m'),md(d,tr),(p-end).days))
        other=[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in out if not any(abs(md(d,tr))<=6 for tr in DE_T)]
        if len(rows)==2 and len(other)<=1: print(f'  sm {sm} arm {arm:4.0f} run {run} drop {drop:3.0f}: {rows}  other {other}')
    print('\n=== peaks: 4-week mean `band` log points below its trailing 52-week maximum after 26 weeks above; published +7 days')
    for band in (2.,3.,5.,8.):
        m=N.rolling(4).mean(); dd=(m.rolling(52,min_periods=26).max()-m).dropna()
        starts=[]; below=0
        for t,v in dd.items():
            if v>=band:
                if below>=26: starts.append(t)
                below=0
            else: below+=1
        rows=[]
        for pk in DE_P:
            c=[s for s in starts if -3<=md(s,pk)<=15]
            if c: s0=min(c); end=(pk+pd.DateOffset(months=1))-pd.Timedelta(days=1); rows.append((pk.strftime('%Y-%m'),(s0+pd.Timedelta(days=7)).strftime('%Y-%m-%d'),(s0+pd.Timedelta(days=7)-end).days))
        other=[s.strftime('%Y-%m-%d') for s in starts if not any(-3<=md(s,pk)<=15 for pk in DE_P)]
        print(f'  band {band:3.0f}: {rows}  other {other}')
