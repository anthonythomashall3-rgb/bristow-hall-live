"""The peak outside the United States: can a zero-lag survey GATE a lower activity threshold?

Section 8c found the Commission's surveys lead the peak by up to a year, so they cannot date
it and cannot call it alone without other calls.  The activity route's D calls the peak when
the median drawdown reaches two per cent, in hand two months late - four to thirty months
after the peak on first prints (median ten).  This script asks whether the survey can serve
as a gate: with the survey already turned down (its balance `x` points below its trailing
twelve-month maximum, adjusted in real time, published in the month it describes), a LOWER
activity threshold (D >= 0.5, 1.0 or 1.5) is allowed to call the peak; without the gate that
lower threshold would fire on every slowdown.  Clauses, each one call per episode (re-arm
after six months off):
  D>=2            the shipped statistic (the row every other is read against)
  D>=t            the lower threshold alone, to show its cost in other calls
  gate & D>=t     the survey gate and the lower threshold together
  survey alone    the survey x points off its maximum for r months
Scored against the committee's peaks (Germany's Council; the euro area, France and Spain as
quarter mid-months) and ECRI's: a call whose data month lies within [peak-3, trough+3] is that
peak's; later calls inside the same contraction are repeats; calls in expansions are other
calls; lag = call month (data month + 2 for D, + 0 for the survey) minus the peak month.
Every setting printed; nothing chosen here.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import ecbcs_speed as E, twostage_ec as T2
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def calls_from(cond, lag, rearm=6):
    out=[]; state='quiet'; off=0
    for t,v in cond.items():
        if state=='quiet':
            if bool(v): out.append((t+pd.DateOffset(months=lag),t)); state='called'; off=0
        else:
            off=off+1 if not bool(v) else 0
            if off>=rearm: state='quiet'
    return out
def score(calls, C):
    got={}; used=set(); rep=[]
    for i,(pk,tr) in enumerate(C):
        c=[(j,p,d) for j,(p,d) in enumerate(calls) if j not in used and -3<=md(d,pk)<=md(tr,pk)+3]
        if c: j,p,d=min(c,key=lambda x:x[1]); got[i]=(p,d); used.add(j)
    for j,(p,d) in enumerate(calls):
        if j in used: continue
        if any(-3<=md(d,pk)<=md(tr,pk)+3 for pk,tr in C): rep.append((p,d)); used.add(j)
    other=[c for j,c in enumerate(calls) if j not in used]
    return got,other,rep
def line(tag, calls, C, show=True):
    got,other,rep=score(calls,C)
    lags=[md(got[i][0],C[i][0]) for i in got]
    s=f'{tag:40s} hits {len(got)}/{len(C)} other {len(other):2d} lag<=1 {sum(l<=1 for l in lags)} <=3 {sum(l<=3 for l in lags)} <=6 {sum(l<=6 for l in lags)} lags {lags}'
    if show:
        print('  '+s)
        if other: print('       other:',[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in other])
    return len(got),len(other),sum(l<=3 for l in lags),sum(l<=6 for l in lags),lags
if __name__=='__main__':
    ccs=sys.argv[1:] or ['DE','FR','ES','EA']
    pooled={}
    for cc in ccs:
        D_in=T2.d_available(cc)              # index = month in hand
        D=D_in.copy(); D.index=D.index-pd.DateOffset(months=2)   # back to data months; lag applied at the call
        C=[(E.ts(a),E.ts(b)) for a,b in E.COMMITTEE[cc]]
        C=[(a,b) for a,b in C if a>=pd.Timestamp('1986-01-01')]
        print(f'\n############ {cc}: committee peaks {[a.strftime("%Y-%m") for a,b in C]}')
        rulers=[('the committee',C)]
        if cc in E.ECRI_CC:
            ec=[(E.ts(d),None) for k,d in E.ECRI[E.ECRI_CC[cc]] if k=='P' and d>='1986-01']
            # pair ECRI peaks with the next ECRI trough
            tr=[E.ts(d) for k,d in E.ECRI[E.ECRI_CC[cc]] if k=='T']
            ec=[(p,min([t for t in tr if t>p],default=p+pd.DateOffset(months=12))) for p,_ in ec]
            rulers.append(('ECRI',ec))
        surveys={}
        for which in ('industry confidence','production expectations','industry and consumer confidence'):
            try: surveys[which]=E.sa_rt(E.series(cc,which)).dropna()
            except KeyError: pass
        for label,CC in rulers:
            print(f'  === peaks against {label} ({len(CC)})')
            for t in (2.0,1.5,1.0,0.5):
                cond=(D>=t); cond=cond[cond.index>=pd.Timestamp('1986-01-01')]
                r=line(f'D>={t}',calls_from(cond,2),CC)
                if label=='the committee': pooled.setdefault(f'D>={t}',[]).append(r)
            for which,s in surveys.items():
                drop=s.rolling(12,min_periods=6).max()-s
                for x in (3.,5.,8.):
                    g=(drop>=x)
                    for r_ in (1,2):
                        gs=g.rolling(r_).sum()>=r_
                        cond=gs[gs.index>=pd.Timestamp('1986-01-01')]
                        r=line(f'{which[:22]} off max >= {x:.0f} for {r_}',calls_from(cond,0),CC,show=(r_==1 and x==5.))
                        if label=='the committee': pooled.setdefault(f'{which[:22]} off>={x:.0f} r={r_}',[]).append(r)
                    for t in (1.5,1.0,0.5):
                        both=(g.reindex(D.index).fillna(False).astype(bool)) & (D>=t)
                        cond=both[both.index>=pd.Timestamp('1986-01-01')]
                        r=line(f'{which[:22]} off>={x:.0f} & D>={t}',calls_from(cond,2),CC,show=(x==5.))
                        if label=='the committee': pooled.setdefault(f'{which[:22]} off>={x:.0f} & D>={t}',[]).append(r)
    print('\n=== pooled over the four committees (peaks since 1986): hits / other / lag<=3 / lag<=6 / median lag')
    rows=[]
    for k,v in pooled.items():
        h=sum(x[0] for x in v); o=sum(x[1] for x in v); w3=sum(x[2] for x in v); w6=sum(x[3] for x in v); lags=[l for x in v for l in x[4]]
        rows.append((h,-o,w6,k,w3,lags))
    rows.sort(reverse=True)
    n=sum(len([1 for a,b in E.COMMITTEE[cc] if E.ts(a)>=pd.Timestamp('1986-01-01')]) for cc in ccs)
    for h,o,w6,k,w3,lags in rows: print(f'  {k:44s} hits {h:2d}/{n} other {-o:3d} lag<=3 {w3:2d} <=6 {w6:2d} median {np.median(lags) if lags else float("nan"):5.1f}')
