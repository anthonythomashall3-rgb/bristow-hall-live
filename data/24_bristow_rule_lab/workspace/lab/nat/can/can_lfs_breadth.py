"""The fast Canadian source: the Labour Force Survey by province (Statistics Canada 14-10-0017,
unadjusted, monthly from January 1976; released in the first week after the reference month).
The American peak detector's breadth form: each province's employment (or unemployment)
adjusted in real time, the causal phase machine, the share of provinces in the falling
(rising) phase as the diffusion index, a peak called after `r` months at or above fifty and
dated at the last month below.  Scored against the Council's peaks from 1981 (four: June 1981,
March 1990, October 2008, February 2020) and troughs, and ECRI's.  A same-month release, so
'within the month' = the call's data month is no later than the month after the peak month."""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/nat/can')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
import can_claims_breadth as C
SRC='/home/claude/lab/acq/statcan/14100017'
PROV=C.PROV
def loadp(ch): 
    P=pd.read_csv(f'{SRC}/CAN_lfs_{ch}_by_province_nsa.csv',index_col=0,parse_dates=True); return P
def sa_panel(P, sign=1.0):
    return pd.concat([(sign*C.sa_rt(P[c])).rename(c) for c in PROV if c in P.columns],axis=1)
COUNCIL_P=[C.ts(x) for x in C.COUNCIL_P if x>='1977']; COUNCIL_T=[C.ts(x) for x in C.COUNCIL_T if x>='1977']
ECRI_P=[C.ts(x) for x in C.ECRI_P if x>='1977']; ECRI_T=[C.ts(x) for x in C.ECRI_T if x>='1977']
def grid_peaks(SA, refs, label, sm_set=(1,3,6), amp_set=(1.,2.,3.,5.,10.), mph_set=(3,5), r_set=(1,2,3), top=5):
    rows=[]
    for sm,amp,mph,r in itertools.product(sm_set,amp_set,mph_set,r_set):
        D=C.hdi(SA,sm,amp,mph); calls=C.peak_calls(D,r); got,other=C.score(calls,refs)
        e=[v[2] for v in got.values()]; lag=[C.md(v[0],refs[i]) for i,v in got.items()]
        rows.append((len(got),-len(other),sum(x==0 for x in e),sum(abs(x)<=1 for x in e),sum(l<=1 for l in lag),(sm,amp,mph,r),got,other))
    rows.sort(key=lambda r:(r[0]+0.5*r[1],r[0],r[4],r[2]),reverse=True)
    print(f'\n=== {label}: (smooth, amp log points, min phase, run)')
    for r in rows[:top]:
        print(f'  hits {r[0]}/{len(refs)} other {-r[1]} exact {r[2]} w1 {r[3]} inMonth {r[4]} | {r[5]}')
        print('     ',{refs[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'data '+v[0].strftime('%Y-%m')) for i,v in r[6].items()})
        if r[7]: print('      other:',[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in r[7]])
    z=[r for r in rows if r[1]==0]
    if z:
        z.sort(key=lambda r:(r[0],r[4],r[2]),reverse=True); r=z[0]
        print(f'  best with no other call: hits {r[0]}/{len(refs)} exact {r[2]} w1 {r[3]} inMonth {r[4]} | {r[5]}')
        print('     ',{refs[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'data '+v[0].strftime('%Y-%m')) for i,v in r[6].items()})
if __name__=='__main__':
    E=loadp('employment'); U=loadp('unemployment'); F=loadp('full_time_employment')
    # peaks: employment FALLING = 'up' phase of -log employment; unemployment RISING = 'up' phase of log unemployment
    SAe=sa_panel(E,-1.0)['1978-01':]; SAu=sa_panel(U,1.0)['1978-01':]; SAf=sa_panel(F,-1.0)['1978-01':]
    print('LFS by province, 1976-01 on; adjusted in real time; scored from 1978')
    grid_peaks(SAe,COUNCIL_P,'PEAKS, employment breadth, the Council')
    grid_peaks(SAu,COUNCIL_P,'PEAKS, unemployment breadth, the Council',amp_set=(5.,10.,15.,20.,30.))
    grid_peaks(SAf,COUNCIL_P,'PEAKS, full-time employment breadth, the Council')
    grid_peaks(pd.concat([SAe,SAu],axis=1),COUNCIL_P,'PEAKS, employment + unemployment breadth (twenty series), the Council',amp_set=(2.,3.,5.,10.))
    grid_peaks(SAe,ECRI_P,'PEAKS, employment breadth, ECRI')
    # troughs: the mirror — employment rising / unemployment falling; use the same machine on the negated panels
    grid_peaks(-SAe,COUNCIL_T,'TROUGHS, employment breadth (rising), the Council')
    grid_peaks(-SAu,COUNCIL_T,'TROUGHS, unemployment breadth (falling), the Council',amp_set=(5.,10.,15.,20.,30.))
