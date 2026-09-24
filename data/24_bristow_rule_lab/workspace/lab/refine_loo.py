"""Rule 18, pass on the refinement windows: exact-month scoring of every monthly end of the
nine chronologies over a grid of refinement windows, with the window chosen by leaving one
chronology out (plan section 3), and the four held-out chronologies never touched here.

The shipped windows are trough (3 back, 1 forward) on the unsmoothed level and peak (1, 0)
on a two-month mean (memo section 8e).  Grid: trough windows (2,1) (3,1) (4,1) (3,2) (6,2)
(6,3); peak windows (1,0) (2,0) (2,1) (3,1) (3,0).  For each fold the window pair with the
most exact months on the other eight chronologies (ties: within one, then within three) is
applied to the ninth; the out-of-sample tally is what a chronology the windows were never
chosen on would get.  Everything else is the shipped configuration (monthly_ends_all.nine).
"""
import sys, itertools, warnings, collections; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
import monthly_ends_all as M
T_GRID=[(2,1),(3,1),(4,1),(3,2),(6,2),(6,3)]
P_GRID=[(1,0),(2,0),(2,1),(3,1),(3,0)]
def run(tw,pw):
    B.REFINE_TROUGH=tw; B.REFINE_PEAK=pw
    P,T=M.nine()
    return [(c,e) for c,k,e,w in P if not w],[(c,e) for c,k,e,w in T if not w]
def tally(rows, countries=None):
    e=[x for c,x in rows if (countries is None or c in countries) and x is not None]
    return (sum(v==0 for v in e), sum(abs(v)<=1 for v in e), sum(abs(v)<=3 for v in e), len(e))
if __name__=='__main__':
    res={}
    for tw,pw in itertools.product(T_GRID,P_GRID):
        P,T=run(tw,pw); res[(tw,pw)]=(P,T)
        tp=tally(P); tt=tally(T)
        print(f'T{tw} P{pw}: peaks exact {tp[0]:2d} w1 {tp[1]:2d} w3 {tp[2]:2d} of {tp[3]} | troughs exact {tt[0]:2d} w1 {tt[1]:2d} w3 {tt[2]:2d} of {tt[3]}', flush=True)
    countries=sorted(set(c for c,e in res[((3,1),(1,0))][0]))
    print('\nleave one chronology out (selection on exact months at both ends, then within one, then within three):')
    oos_p=[]; oos_t=[]; picks=collections.Counter()
    for held in countries:
        others=[c for c in countries if c!=held]
        def key(k):
            tp=tally(res[k][0],others); tt=tally(res[k][1],others)
            return (tp[0]+tt[0], tp[1]+tt[1], tp[2]+tt[2])
        best=max(res, key=key); picks[best]+=1
        P,T=res[best]
        oos_p+= [(c,e) for c,e in P if c==held]; oos_t+=[(c,e) for c,e in T if c==held]
        tp=tally(P,[held]); tt=tally(T,[held]); sp=tally(res[((3,1),(1,0))][0],[held]); st=tally(res[((3,1),(1,0))][1],[held])
        print(f'  held out {held:26s} picks T{best[0]} P{best[1]} -> peaks {tp[0]}/{tp[1]}/{tp[2]} of {tp[3]}, troughs {tt[0]}/{tt[1]}/{tt[2]} of {tt[3]}   (shipped: {sp[0]}/{sp[1]}/{sp[2]}, {st[0]}/{st[1]}/{st[2]})')
    op=tally(oos_p); ot=tally(oos_t); sp=tally(res[((3,1),(1,0))][0]); st=tally(res[((3,1),(1,0))][1])
    print(f'\nout of sample, all nine: peaks exact {op[0]} w1 {op[1]} w3 {op[2]} of {op[3]}; troughs exact {ot[0]} w1 {ot[1]} w3 {ot[2]} of {ot[3]}')
    print(f'shipped (3,1)/(1,0)   : peaks exact {sp[0]} w1 {sp[1]} w3 {sp[2]} of {sp[3]}; troughs exact {st[0]} w1 {st[1]} w3 {st[2]} of {st[3]}')
    print('windows picked:', dict(picks))
