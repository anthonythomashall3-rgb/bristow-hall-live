import sys; sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np
from core import *

U=load('/home/claude/archive/data/fred/UNRATE.csv','US postwar')
IW=load('/home/claude/archive/data/robustness/M0892AUSM156SNBR.csv','US interwar')

# NBER monthly peaks/troughs
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
IW_PK=['1929-08','1937-05']; IW_TR=['1933-03','1938-06']
ts=lambda s: pd.Timestamp(s+'-01')

def episodes(s,thr):
    out=[];cur=[]
    for d,v in s.dropna().items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    return out

def window(u, stat, pk, tr, thr, tail=12, anchor='episode'):
    """return (start,end) of the search window"""
    p,t=ts(pk),ts(tr)
    if anchor=='nber': return p, t+pd.DateOffset(months=tail)
    eps=episodes(stat,thr)
    cand=[e for e in eps if e[0]>=p and e[0]<=t+pd.DateOffset(months=tail)]
    if not cand: return None
    e=cand[0]
    return e[0], e[-1]+pd.DateOffset(months=tail)

def score(name, datefn, pks, tks, label=''):
    gaps=[]
    for pk,tk in zip(pks,tks):
        d=datefn(pk,tk)
        gaps.append(None if d is None else md(d,ts(tk)))
    ok=[g for g in gaps if g is not None]
    hits=sum(1 for g in ok if abs(g)<=3)
    worst=max(ok,key=abs) if ok else None
    return dict(name=name,label=label,gaps=gaps,hits=hits,n=len(ok),worst=worst,
                mad=round(float(np.mean([abs(g) for g in ok])),2) if ok else None)

def show(rows, title):
    print('\n'+'='*100); print(title); print('='*100)
    print(f"{'variant':44s} {'US postwar':>12s} {'worst':>6s} {'MAD':>5s}   gaps")
    for r in rows:
        g=' '.join('  .' if x is None else f'{x:+3d}' for x in r['gaps'])
        print(f"{r['name']:44s} {r['hits']:>5d}/{r['n']:<6d} {r['worst']:>+6d} {r['mad']:>5.2f}   {g}")
