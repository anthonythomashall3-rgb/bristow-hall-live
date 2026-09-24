"""Two stages for the trough, outside the United States: the activity data say a contraction is
under way, the zero-lag survey says when it ended.

Stage 1 (activity): the level route's composite deviation D on the OECD panel for the economy
(industrial production and retail volume, plus employment where the file exists; lab/kei),
smoothing 3, lookback 12 - the shipped settings - with each month's reading treated as in
hand two months after the month it describes (the OECD publication lag; the first-print
replay of memo section 8c found the same panel's first prints date like its final vintage).
A contraction is open from the first month D >= 2 per cent is in hand until the trough is
called; the state re-arms once D < 2 is in hand again.

Stage 2 (survey): the Commission's unadjusted survey balance for the economy, adjusted in real
time (ecbcs_speed.sa_rt), tracked from three months before the contraction opened; the trough
is called in the first month the balance has stood `a` points above its minimum for `r`
consecutive months, dated at the month of the minimum, and published in the month of the call
(the survey for month T is released in the last days of month T).

For comparison, the tool's own real-time trough clause on the same D (real_time_trough_calls
at the shipped decision: four falling months, half a point), published two months after its
triggering month.  Both are scored the same way against the committee (Germany's Council; the
euro area, France and Spain as quarter mid-months) and ECRI: hits within six months, exact,
within one, within three, published within the month (call month <= trough month + 1), other
calls.  Grid over survey series x (a, r); every setting printed for the committee so nothing
is chosen by the score.
"""
import sys, itertools, json, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, bench
from bench import kei, pro
import ecbcs_speed as E
KEIMAP={'DE':'DEU','FR':'FRA','ES':'ESP','IT':'ITA','UK':'GBR','SE':'SWE','AT':'AUT','EA':'EA20','PL':'POL'}
USE={'industrial production','retail volume','employment'}
LAG=2
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def panel(cc):
    chs=[]
    for nm,p,kind in kei(KEIMAP[cc]):
        if nm in USE: chs.append((nm,pro(p,kind)))
    return chs
def d_available(cc):
    D=B.composite_deviation(panel(cc),12,3,1).dropna()   # one channel suffices before a second file begins (EA20 retail volume starts 1995)
    D.index=D.index+pd.DateOffset(months=LAG)     # the month each reading is in hand
    return D
def twostage(D, s, a, r, pre=3, min_cycle=12):
    """returns troughs as (published month, dated month)"""
    idx=s.index; out=[]; state='quiet'; open_at=None; last=None
    for t in idx:
        if t not in D.index: continue
        d=float(D[t])
        if state=='quiet':
            if d>=2.0 and (last is None or md(t,last)>=min_cycle):
                state='open'; open_at=t
        elif state=='open':
            seg=s[open_at-pd.DateOffset(months=pre):t].dropna()
            if len(seg)<2: continue
            m=seg.idxmin(); lo=float(seg.min())
            tail=seg[seg.index>m]
            if len(tail)>=r and bool((tail.iloc[-r:]>=lo+a).all()):
                out.append((t,m)); last=m; state='recover'
        else:
            if d<2.0: state='quiet'
    return out
def tool_troughs(cc):
    calls=B.real_time_trough_calls(panel(cc),publication_lag=LAG,fall_months=4,drop=0.5,min_channels=1)
    return calls
def score(calls, refs, tol=6):
    got={}; used=set()
    for i,ref in enumerate(refs):
        best=None
        for j,(pub,dt) in enumerate(calls):
            if j in used: continue
            e=md(dt,ref)
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(j,e)
        if best: got[i]=(calls[best[0]][0],calls[best[0]][1],best[1]); used.add(best[0])
    return got,[c for j,c in enumerate(calls) if j not in used]
def line(tag, calls, T, show=True):
    got,other=score(calls,T)
    e=[v[2] for v in got.values()]; lag=[md(v[0],T[i]) for i,v in got.items()]
    s=f'{tag:44s} hits {len(got)}/{len(T)} other {len(other)} exact {sum(x==0 for x in e)} w1 {sum(abs(x)<=1 for x in e)} w3 {sum(abs(x)<=3 for x in e)} inMonth {sum(l<=1 for l in lag)}'
    if show:
        print(s); print('      ',{T[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'pub '+v[0].strftime('%Y-%m'),'lag '+str(md(v[0],T[i]))) for i,v in got.items()})
        if other: print('       other:',[(p.strftime('%Y-%m'),x.strftime('%Y-%m')) for p,x in other])
    return len(got),len(other),sum(x==0 for x in e),sum(abs(x)<=1 for x in e),sum(abs(x)<=3 for x in e),sum(l<=1 for l in lag)
if __name__=='__main__':
    ccs=sys.argv[1:] or ['DE','FR','ES','IT','UK','SE','AT','EA']
    for cc in ccs:
        print(f'\n############ {cc}: panel {[nm for nm,s in panel(cc)]}, since {min(s.index.min() for nm,s in panel(cc)):%Y-%m}')
        D=d_available(cc)
        rulers=[]
        if cc in E.COMMITTEE: rulers.append(('the committee',[E.ts(t) for p,t in E.COMMITTEE[cc]]))
        if cc in E.ECRI_CC: rulers.append(('ECRI',[E.ts(d) for k,d in E.ECRI[E.ECRI_CC[cc]] if k=='T' and d>='1986-01']))
        tt=[(p,d) for p,d in tool_troughs(cc) if d>=pd.Timestamp('1986-01-01')]   # the survey era only, so the two are scored on the same turns
        for label,T in rulers:
            print(f'\n  === troughs against {label} ({len(T)})')
            line("the tool's own clause on D, published +2 months",tt,T)
            for which in E.SERIES:
                try: s=E.sa_rt(E.series(cc,which)).dropna()
                except KeyError: continue
                rows=[]
                for a,r in itertools.product((2.,3.,5.,8.),(1,2,3)):
                    calls=twostage(D,s,a,r)
                    rows.append((line(f'  {which} a={a} r={r}',calls,T,show=False),a,r,calls))
                rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
                for res,a,r,calls in rows[:2]:
                    line(f'  {which} a={a} r={r}',calls,T)
