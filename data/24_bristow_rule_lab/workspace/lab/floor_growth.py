"""The end-of-floor convention on the growth-cycle committees' own objects.

Two of the three growth-cycle committees document that they take the LAST month of a flat
floor: the South African Reserve Bank's 2023 note reads its detrended coincident indicator
as bottoming in mid-2015 and running flat to January 2017 and dates April 2017; Taiwan's
National Development Council took the last month of a five-month floor in 1998 (memo
sections 13 and 13b).  The rule's growth route reads the extremum (band zero), so the
convention costs it the 2017 South African trough (-23) and the 1998 Taiwanese one (-5).

This script prices the convention as a clause: on each committee's own detrended object
(South Africa: the Reserve Bank's coincident indicator, ratio to its HP trend; Taiwan: the
Council's published detrended index; Korea, in sample: Statistics Korea's cyclical
component), the trough is the plateau within `beta` of the minimum read at its middle or
its last month, over the grid beta in {0, 0.5, 1, 2, 3 per cent} x {mid, last}.  Korea is
the in-sample check (Rule 18: a held-out instance cannot choose a clause); South Africa and
Taiwan show the held-out consequence.  Peaks are untouched.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, bench
from bench import load, ts, hp_filter, kor_coincident
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def rtt(s,lam=500000.0):
    y=np.log(s.dropna()); y=y[np.isfinite(y)]
    return np.exp(y-pd.Series(hp_filter(y.values,lam),index=y.index))*100.0
ZA=[('1946-07','1947-04'),('1948-11','1950-02'),('1951-12','1953-03'),('1955-04','1956-09'),('1958-01','1959-03'),('1960-04','1961-08'),('1965-04','1965-12'),('1967-05','1967-12'),('1970-12','1972-08'),('1974-08','1977-12'),('1981-08','1983-03'),('1984-06','1986-03'),('1989-02','1993-05'),('1996-11','1999-08'),('2007-11','2009-08'),('2013-11','2017-04'),('2019-06','2020-04')]
TW=[('1955-11','1956-09'),('1964-09','1966-01'),('1968-08','1969-10'),('1974-02','1975-02'),('1980-01','1983-02'),('1984-05','1985-08'),('1989-05','1990-08'),('1995-02','1996-03'),('1997-12','1998-12'),('2000-09','2001-09'),('2004-03','2005-02'),('2008-03','2009-02'),('2011-02','2012-01'),('2014-10','2016-02'),('2022-01','2023-04')]
KR=[(bench.ep3(e,'M')[0],bench.ep3(e,'M')[1]) for e in bench.PANELS['Korea']['chrono']]
def objects():
    za=rtt(load('/home/claude/lab/sarb/ZAF_coincident.csv'))
    bci=pd.read_csv('/home/claude/lab/twn/TWN_bci.csv',index_col=0,parse_dates=True)
    tw=pd.to_numeric(bci['景氣同時指標不含趨勢指數(點)'],errors='coerce').dropna()
    kr=kor_coincident()
    return {'South Africa (held out)':(za,ZA,3),'Taiwan (held out)':(tw,TW,3),'Korea (in sample)':(kr,KR,3)}
def score(obj, chron, smooth, beta, where):
    errs=[]
    for pk,tr in chron:
        pkm=ts(pk); trm=ts(tr); w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if obj.index.min()>w0 or obj.index.max()<trm: continue
        t=B.channel_trough(obj,w0,w1,beta,smooth,12,abstain=False,where=where)
        errs.append((tr[:7],None if t is None else md(t,trm)))
    e=[x for _,x in errs if x is not None]
    f=lambda k: sum(abs(x)<=k for x in e)
    return errs, f'n {len(e)} exact {f(0)} w1 {f(1)} w3 {f(3)} mae {np.mean(np.abs(e)):.2f}'
if __name__=='__main__':
    for name,(obj,chron,sm) in objects().items():
        print(f'\n=== {name}: troughs on the committee\'s own object, band beta x plateau reading')
        for beta,where in itertools.product((0.0,0.005,0.01,0.02,0.03),('mid','last')):
            errs,summ=score(obj,chron,sm,beta,where)
            flag=' <- shipped (band 0)' if beta==0.0 and where=='mid' else ''
            print(f'  beta {beta:.3f} {where:4s}: {summ}{flag}')
            if beta in (0.0,0.01,0.02) : print('       ',{k:v for k,v in errs})
