"""The weekly level clause on national initial claims, selected leave-one-trough-out (Rule 18).

Rule 17's 'called within the month' is missed at three American troughs (1958, 1991, 2001) because
the objects that fire first there are the monthly claims legs, published on the 10th of the second
month.  Initial claims peak at or just before the trough month (continued claims peak later - the
jobless recoveries of 1975 and 1991), and the Department's national weekly file with the rule's
real-time factors (DOL_national_weekly_claims_sa_rt.csv, 1969 on) is the fastest object the record
holds.  The shipped weekly initial-claims leg (union_troughs.leg_I: eight-week mean, six falling
weeks, drop 10, arm 40, re-arm 13 weeks) was set on the 1986 state-sum file and on the Department's
file calls neither 1991 nor 2001.

This script runs cc_trough_grid's state machine (the same detector Finding 2 uses on continued
claims) over the same 1,440-setting grid on INITIAL claims, and then chooses the setting the way
Rule 18 allows: for each of the eight troughs 1970-2020 the setting is chosen on the other seven
(most troughs called, fewest other calls, most inside the month, most exact, then within one, then
shortest mean lag) and applied to the eighth.  What the held-out troughs get is the out-of-sample
record; the same is done on continued claims so the two objects can be read side by side.  Run 3
September 2026; output ic_trough_loo.log.  Nothing is adopted on its own score.
"""
import sys, itertools, warnings, collections; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude/lab/weekly')
import numpy as np, pandas as pd
import cc_trough_grid as C
GRID=list(itertools.product((2,3,4,6,8),(1,2,3,4,5,6),(1.,2.,3.,4.,6.,8.),(20.,25.,30.,40.),(13,26)))
def run_all(col):
    res={}
    for nsm,rt,delta,nth,mp in GRID:
        D=C.series(nsm,col); cl=C.calls(D,rt,delta,nth,mp); got,fa=C.score(cl)
        res[(nsm,rt,delta,nth,mp)]=(got,fa)
    return res
def key_on(got,fa,keep):
    g={k:v for k,v in got.items() if k in keep}
    hits=len(g); within=sum(1 for v in g.values() if v[1]<=61); exact=sum(1 for v in g.values() if v[0]==0)
    w1=sum(1 for v in g.values() if abs(v[0])<=1); lag=np.mean([v[1] for v in g.values()]) if g else 999
    return (hits,-len(fa),within,exact,w1,-lag)
def loo(res,label,ref=None):
    print(f'\n=== {label}: leave one trough out over the {len(res)} settings')
    if ref is not None:
        got,fa=res[ref]; print(f'reference setting {ref}: '+', '.join(f'{k} {got[k]}' if k in got else f'{k} --' for k in C.TR)+f'; other calls {fa}')
    oos={}; picks=collections.Counter()
    for held in C.TR:
        others=[k for k in C.TR if k!=held]
        best=max(res,key=lambda s:key_on(res[s][0],res[s][1],others))
        picks[best]+=1; got,fa=res[best]
        oos[held]=got.get(held);
        print(f'  held out {held}: picks nsm {best[0]} rt {best[1]} drop {best[2]:.0f} arm {best[3]:.0f} rearm {best[4]} -> '
              f"{'not called' if held not in got else f'err {got[held][0]:+d}, lag {got[held][1]} d, in-month {got[held][1]<=61}'}; that setting's other calls over the whole file: {len(fa)} {fa[:3]}")
    v=[x for x in oos.values() if x is not None]
    print(f'  out of sample: called {len(v)}/8, in-month {sum(1 for x in v if x[1]<=61)}, exact {sum(1 for x in v if x[0]==0)}, within one {sum(1 for x in v if abs(x[0])<=1)}; settings picked {dict(picks)}')
    z=[(key_on(g,f,C.TR),s) for s,(g,f) in res.items()]; z.sort(reverse=True)
    print('  in-sample best five (hits, -other, in-month, exact, w1, -mean lag):')
    for k,s in z[:5]: print(f'    {s}: {k[:5]} lag {-k[5]:.0f}')
if __name__=='__main__':
    ic=run_all('ic_sa_rt'); loo(ic,'initial claims',ref=(8,6,10.,40.,13) if (8,6,10.,40.,13) in ic else None)
    # the shipped initial-claims leg is outside the grid (drop 10): run it as the reference row
    D=C.series(8,'ic_sa_rt'); got,fa=C.score(C.calls(D,6,10.,40.,13))
    print(f'shipped leg I on this file (nsm 8, rt 6, drop 10, arm 40, rearm 13): '+', '.join(f'{k} {got[k]}' if k in got else f'{k} --' for k in C.TR)+f'; other calls {fa}')
    cc=run_all('cc_sa_rt'); loo(cc,'continued claims',ref=(4,6,4.,30.,13))
