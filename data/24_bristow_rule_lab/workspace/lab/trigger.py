"""A real-time trough call that uses no official date anywhere.

  TRIGGER  the composite deviation statistic reached at least `thr` percent, and has
           since declined for `j` consecutive months and fallen `drop` points from
           that maximum: recovery is visible in the data, so a trough has occurred.
  DATE     the month the composite deviation statistic reached that maximum.
  CENSOR   a call whose trough falls less than `min_cycle` months after the previous
           call's trough is suppressed: Bry and Boschan's minimum-cycle censoring, which
           stops a long recovery with a pause in it being called twice.
The call is published one month after the month of data that triggered it.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True

def calls(D, thr, j, drop, pub=1, min_cycle=15):
    out=[]; start=D.index[0]
    T=None
    for i in range(24,len(D)):
        T=D.index[i]
        seg=D[start:T]
        if len(seg)<4: continue
        pk_at=seg.idxmax(); pk=float(seg.max())
        if pk<thr: continue
        after=seg[seg.index>pk_at]
        if len(after)<j: continue
        tailv=list(after.iloc[-j:])
        prev=float(after.iloc[-j-1]) if len(after)>j else pk
        seqfall=all((tailv[k] < (tailv[k-1] if k>0 else prev)) for k in range(j))
        if seqfall and (pk-float(after.iloc[-1]))>=drop:
            start=T+pd.DateOffset(months=1)
            if out and min_cycle and (pk_at.year*12+pk_at.month)-(out[-1][1].year*12+out[-1][1].month)<min_cycle:
                continue
            out.append((T+pd.DateOffset(months=pub), pk_at))
    return out

if __name__=='__main__':
    chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
    D=composite_dev(chs,12,3,2).dropna()
    D=D['1968':]
    print('composite deviation runs',D.index[0].date(),'to',D.index[-1].date(),'n=',len(D))
    TR=[ts(t) for p,t in US_M if t>='1969']
    for thr,j,drop in [(2.0,4,0.5)]:
     if True:
      if True:
            cs=calls(D,thr,j,drop)
            used=set(); matched=[]; extra=0
            for at,d in cs:
                ks=[i for i in range(len(TR)) if abs(md(d,TR[i]))<=6 and i not in used]
                if ks:
                    k=min(ks,key=lambda i: abs(md(d,TR[i]))); used.add(k); matched.append((TR[k],at,d))
                else: extra+=1
            if not matched: 
                print(f'thr={thr} j={j} drop={drop}  0 matched, {len(cs)} calls'); continue
            lags=[md(at,t) for t,at,d in matched]; errs=[abs(md(d,t)) for t,at,d in matched]
            print(f'thr={thr} j={j} drop={drop}  found {len(matched)}/8  lag mean {np.mean(lags):+.1f} max {max(lags)}  |err| {np.mean(errs):.2f}  false calls {extra}')
            NB={'1991-03':21,'2001-11':20,'2009-06':15,'2020-04':15}
            print(f'{"NBER trough":12s} {"rule called":12s} {"published":10s} {"lag":>4s} {"error":>6s}  {"NBER lag":>8s}')
            for t,at,d in sorted(matched):
                k=t.strftime('%Y-%m')
                print(f'{k:12s} {d:%Y-%m}       {at:%Y-%m}     {md(at,t):4d} {md(d,t):6d}  {str(NB.get(k,"")):>8s}')
            miss=[TR[i].strftime('%Y-%m') for i in range(len(TR)) if i not in used]
            print('   not called at all:',miss)
