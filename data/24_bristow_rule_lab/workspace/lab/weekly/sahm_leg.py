"""Sahm's rule as a peak object for the American union of section 8f: the three-month mean of
the unemployment rate standing half a point or more above its minimum over the prior twelve
months (Sahm 2019, the rule as she published it; nothing chosen here), read on the
unemployment rate exactly as first published (ALFRED UNRATE vintages, March 1960 on; the
publication day is the vintage day, the first Friday after the month).  One call per
episode: the first vintage on which the indicator stands at or above the line; the object
re-arms once the indicator has stood below the line for twelve consecutive months of data.

The rule is a call, not a date - Sahm's rule says a recession has begun and says nothing about
the month it began - so in the union it can only open the call; the date is another leg's.
Scored as union_peaks.py scores its legs: a call published inside [peak-6 months, trough+3]
is that peak's; later calls inside the same contraction are repeats; the rest are other
calls.  Lag in days from the last day of the NBER peak month.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude/lab/rt')
import numpy as np, pandas as pd
import alfred as al
PK=[pd.Timestamp(x) for x in ('1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
TR=[pd.Timestamp(x) for x in ('1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04')]
def month_end(t): return (t+pd.DateOffset(months=1))-pd.Timedelta(days=1)
def sahm(u):
    m3=u.rolling(3).mean(); return m3-m3.shift(1).rolling(12).min()
def calls(line=0.50, rearm_months=12):
    out=[]; state='quiet'; below=0
    for T in al.vintages('UNRATE'):
        s=sahm(al.asof('UNRATE',T)).dropna()
        if len(s)<15: continue
        v=float(s.iloc[-1]); m=s.index[-1]
        if state=='quiet':
            if v>=line: out.append((T,m)); state='called'; below=0
        else:
            below=below+1 if v<line else 0
            if below>=rearm_months: state='quiet'
    return out
if __name__=='__main__':
    C=calls()
    print('Sahm 0.50 on the vintages:',[(p.strftime('%Y-%m-%d'),m.strftime('%Y-%m')) for p,m in C])
    used=set(); print('\npeak      call         lag(d)  in-month  data month')
    for pk,tr in zip(PK,TR):
        c=[(i,p,m) for i,(p,m) in enumerate(C) if pk-pd.DateOffset(months=6)<=p<=tr+pd.DateOffset(months=3)]
        if not c: print(f'{pk:%Y-%m}   none'); continue
        i,p,m=min(c,key=lambda x:x[1]); used.add(i); lag=(p-month_end(pk)).days
        print(f'{pk:%Y-%m}   {p:%Y-%m-%d}   {lag:5d}   {"yes" if p<=month_end(pk+pd.DateOffset(months=1)) else "no ":3s}      {m:%Y-%m}')
        for j,pp,mm in c[1:]: used.add(j)
    print('other calls:',[(p.strftime('%Y-%m-%d'),m.strftime('%Y-%m')) for i,(p,m) in enumerate(C) if i not in used])
