import sys; sys.path.insert(0,'/home/claude/lab')
from us import *
import pandas as pd, numpy as np

def eps_for(stat,thr,pk,tk,tail=12):
    p,t=ts(pk),ts(tk)
    cand=[e for e in episodes(stat,thr) if e[0]>=p and e[0]<=t+pd.DateOffset(months=tail)]
    return cand[0] if cand else None

def make_scorer(u, PKs, TRs):
    def sc(name, fn, thr=0.50, statf=None, tail=12):
        stat = statf if statf is not None else sahm(u,12)
        gaps=[]
        for pk,tk in zip(PKs,TRs):
            e=eps_for(stat,thr,pk,tk,tail)
            if e is None: gaps.append(None); continue
            w0,w1=e[0], e[-1]+pd.DateOffset(months=tail)
            d=fn(stat,u,w0,w1,e)
            gaps.append(None if d is None else md(d,ts(tk)))
        ok=[g for g in gaps if g is not None]
        return dict(name=name,gaps=gaps,hits=sum(1 for g in ok if abs(g)<=3),n=len(ok),
                    worst=max(ok,key=abs) if ok else None,
                    mad=round(float(np.mean([abs(g) for g in ok])),2) if ok else None)
    return sc

scUS=make_scorer(U,PK,TR); scIW=make_scorer(IW,IW_PK,IW_TR)

# --- rule families ---
def f_peak(stat,u,w0,w1,e):
    seg=stat[w0:w1].dropna(); return seg.idxmax() if len(seg) else None

def f_retrace(theta):
    def f(stat,u,w0,w1,e):
        seg=stat[w0:w1].dropna()
        if not len(seg): return None
        pk=seg.idxmax(); mx=seg.max()
        after=seg[pk:]
        below=after[after<=theta*mx]
        return below.index[0] if len(below) else after.index[-1]
    return f

def f_delta_decay(theta,k=3):
    """first month after the peak of the k-month change at which that change has decayed to theta of its max"""
    def f(stat,u,w0,w1,e):
        d=delta(u,k)[w0:w1].dropna()
        if not len(d): return None
        pk=d.idxmax(); mx=d.max()
        after=d[pk:]
        below=after[after<=theta*mx]
        return below.index[0] if len(below) else after.index[-1]
    return f

def f_anchored_peak(stat,u,w0,w1,e):
    m=ma3(u); base=float(m[:w0].tail(12).min())
    seg=(m-base)[w0:w1].dropna()
    return seg.idxmax() if len(seg) else None

rows=[]
def add(name,fn,thr=0.50,statf=None):
    a=scUS(name,fn,thr,statf); b=scIW(name,fn,thr,statf if statf is None else statf)
    rows.append((name,a,b))

add('R0  peak of S (current rule)', f_peak)
for th in (0.9,0.75,0.5,0.33,0.25,0.1):
    add(f'R1  S retraces to {int(th*100):>2d}% of peak', f_retrace(th))
for th in (0.5,0.33,0.25,0.1,0.0):
    add(f'R2  3m change decays to {int(th*100):>2d}% of max', f_delta_decay(th,3))
for th in (0.5,0.25,0.0):
    add(f'R3  6m change decays to {int(th*100):>2d}% of max', f_delta_decay(th,6))
add('R4  peak of anchored level (pre-episode floor)', f_anchored_peak)

print(f"{'rule':46s} {'US postwar':>11s} {'worst':>6s} {'MAD':>5s} | {'interwar':>9s} {'gaps':>10s}")
print('-'*104)
for name,a,b in rows:
    ig=' '.join('  .' if x is None else f'{x:+3d}' for x in b['gaps'])
    print(f"{name:46s} {a['hits']:>4d}/{a['n']:<5d} {str(a['worst']):>6s} {str(a['mad']):>5s} | {b['hits']:>3d}/{b['n']:<4d} {ig:>10s}")
print('\n(interwar gaps are 1929-33 then 1937-38)')
