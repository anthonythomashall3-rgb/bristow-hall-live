import sys; sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np
from core import *

def ts(s): return pd.Timestamp(s+'-01')
MON={m:i+1 for i,m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}

JP=[('1951-06','1951-10'),('1954-01','1954-11'),('1957-06','1958-06'),('1961-12','1962-10'),
    ('1964-10','1965-10'),('1970-07','1971-12'),('1973-11','1975-03'),('1977-01','1977-10'),
    ('1980-02','1983-02'),('1985-06','1986-11'),('1991-02','1993-10'),('1997-05','1999-01'),
    ('2000-11','2002-01'),('2008-02','2009-03'),('2012-03','2012-11'),('2018-10','2020-05')]
CA=[('1929-04','1933-02'),('1937-11','1938-06'),('1947-08','1948-03'),('1951-04','1951-12'),
    ('1953-07','1954-07'),('1957-03','1958-01'),('1960-03','1961-03'),('1974-10','1975-03'),
    ('1981-06','1982-10'),('1990-03','1992-05'),('2008-10','2009-05'),('2020-02','2020-04')]
US=[('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
    ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
    ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]

SERIES={
 'US'    : ('/home/claude/archive/data/fred/UNRATE.csv', US, 'NBER'),
 'Canada': ('/home/claude/a20/LRHUTTTTCAM156S.csv', CA, 'C.D. Howe BCC'),
 'Japan' : ('/home/claude/a20/LRHUTTTTJPM156S.csv', JP, 'ESRI'),
}

def md(a,b): return (a.year-b.year)*12+(a.month-b.month)

def episodes(s,thr):
    out=[];cur=[]
    for d,v in s.dropna().items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur);cur=[]
    if cur: out.append(cur)
    return out

def evaluate(u, chrono, statf, thr, tail=12, anchor='episode', name=''):
    stat=statf(u)
    rows=[]
    for pk,tk in chrono:
        p,t=ts(pk),ts(tk)
        if p < stat.dropna().index.min() or t > stat.dropna().index.max():
            rows.append((pk,tk,None,'no data')); continue
        if anchor=='nber':
            w0,w1=p,t+pd.DateOffset(months=tail)
        else:
            cand=[e for e in episodes(stat,thr) if e[0]>=p and e[0]<=t+pd.DateOffset(months=tail)]
            if not cand: rows.append((pk,tk,None,'no crossing')); continue
            e=cand[0]; w0,w1=e[0], e[-1]+pd.DateOffset(months=tail)
        seg=stat[w0:w1].dropna()
        if not len(seg): rows.append((pk,tk,None,'empty')); continue
        d=seg.idxmax(); rows.append((pk,tk,md(d,t),d.strftime('%Y-%m')))
    return rows

def summarize(rows):
    g=[r[2] for r in rows if r[2] is not None]
    nofire=sum(1 for r in rows if r[2] is None and r[3]=='no crossing')
    return dict(n=len(g),hits=sum(1 for x in g if abs(x)<=3),
                mad=round(float(np.mean([abs(x) for x in g])),2) if g else None,
                worst=max(g,key=abs) if g else None, nofire=nofire)
