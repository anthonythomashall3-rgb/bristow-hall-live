"""The even-count median convention, re-selected leave-one-out under the refinement clause.

The panel date is the median of the channel dates; with an even number of voting channels the
median falls between two months and the rule takes the LATER of the two (bristow_rule_v3._median,
by ceiling).  That convention was fixed before the refinement clause existed.  Test (3 September
2026): the same nine chronologies dated with the earlier middle instead, everything else shipped
(refinement (3,1)/(1,0), trim 24, routing), scored exact / within one / within three at every
monthly end; then the convention chosen by leaving one chronology out, exactly as refine_loo.py
chooses the refinement windows.  The four held-out chronologies are run through the same switch
by median_convention_heldout.py.  Nothing is adopted on its own score.
"""
import sys, math, warnings, collections; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
import monthly_ends_all as M
SHIPPED=B._median
def median_earlier(dates, q=0.5):
    ds=sorted(d for d in dates if d is not None)
    if not ds: return None
    if len(ds)==1: return ds[0]
    i=int(math.floor(q*(len(ds)-1)+1e-9))
    return ds[min(max(i,0),len(ds)-1)]
CONV={'later (shipped)':SHIPPED,'earlier':median_earlier}
def run(fn):
    B._median=fn
    try:
        P,T=M.nine()
    finally:
        B._median=SHIPPED
    return [(c,k,e) for c,k,e,w in P if not w],[(c,k,e) for c,k,e,w in T if not w]
def tally(rows, countries=None):
    e=[x for c,k,x in rows if (countries is None or c in countries) and x is not None]
    return (sum(v==0 for v in e), sum(abs(v)<=1 for v in e), sum(abs(v)<=3 for v in e), len(e))
if __name__=='__main__':
    res={}
    for name,fn in CONV.items():
        P,T=run(fn); res[name]=(P,T); tp=tally(P); tt=tally(T)
        print(f'{name:16s}: peaks exact {tp[0]:2d} w1 {tp[1]:2d} w3 {tp[2]:2d} of {tp[3]} | troughs exact {tt[0]:2d} w1 {tt[1]:2d} w3 {tt[2]:2d} of {tt[3]}',flush=True)
    a,b=res['later (shipped)'],res['earlier']
    print('\nends where the two conventions differ (country, episode, shipped error / earlier error):')
    for kind,(ra,rb) in (('peak',(a[0],b[0])),('trough',(a[1],b[1]))):
        for (c,k,ea),(c2,k2,eb) in zip(ra,rb):
            if ea!=eb: print(f'  {kind:6s} {c:26s} {k[:7]}  {ea!s:>5} / {eb!s:<5}')
    countries=sorted(set(c for c,k,e in a[0]))
    print('\nleave one chronology out (selection on exact months at both ends, then within one, then within three):')
    oos_p=[];oos_t=[];picks=collections.Counter()
    for held in countries:
        others=[c for c in countries if c!=held]
        def key(n):
            tp=tally(res[n][0],others); tt=tally(res[n][1],others)
            return (tp[0]+tt[0],tp[1]+tt[1],tp[2]+tt[2])
        best=max(res,key=key)
        # a tie goes to the shipped convention: nothing changes on a tie
        if key(best)==key('later (shipped)'): best='later (shipped)'
        picks[best]+=1
        P,T=res[best]; oos_p+=[r for r in P if r[0]==held]; oos_t+=[r for r in T if r[0]==held]
        tp=tally(P,[held]); tt=tally(T,[held]); sp=tally(a[0],[held]); st=tally(a[1],[held])
        print(f'  held out {held:26s} picks {best:16s} -> peaks {tp[0]}/{tp[1]}/{tp[2]} of {tp[3]}, troughs {tt[0]}/{tt[1]}/{tt[2]} of {tt[3]}   (shipped: {sp[0]}/{sp[1]}/{sp[2]}, {st[0]}/{st[1]}/{st[2]})')
    op=tally(oos_p); ot=tally(oos_t); sp=tally(a[0]); st=tally(a[1])
    print(f'\nout of sample, all nine: peaks exact {op[0]} w1 {op[1]} w3 {op[2]} of {op[3]}; troughs exact {ot[0]} w1 {ot[1]} w3 {ot[2]} of {ot[3]}')
    print(f'shipped (later middle) : peaks exact {sp[0]} w1 {sp[1]} w3 {sp[2]} of {sp[3]}; troughs exact {st[0]} w1 {st[1]} w3 {st[2]} of {st[3]}')
    print('conventions picked:',dict(picks))
