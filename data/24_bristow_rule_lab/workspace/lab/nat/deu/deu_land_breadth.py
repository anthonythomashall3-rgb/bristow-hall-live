"""Germany's zero-lag analogue of the American state claims field: registered unemployed by
Land, monthly from January 1991, unadjusted (Bundesagentur fuer Arbeit, 'Arbeitslose und
Arbeitslosenquoten - Deutschland, West/Ost, Laender und Regionaldirektionen (Zeitreihe
Monatszahlen ab 1991)', lab/acq/ba/zr-alo-bl-dwolr-0-xlsx.xlsx, fetched 2 September 2026;
extracted to DEU_unemployed_by_land_nsa.csv).  The Bundesagentur publishes the count for month
T at the end of month T, so a call on month T's data is published inside month T.

The detector is the Canadian/American breadth machine (lab/nat/can/can_claims_breadth.py):
each Land's log count adjusted in real time (month-of-year medians over the seven prior years;
the first two years unadjusted), the causal phase machine, and the share of the sixteen Laender
in the rising phase as the diffusion index; a peak is called when the index has stood at or
above fifty for `r` months and dated at the last month below fifty.  Troughs: the same machine
on the negated panel (Laender in the falling phase).  Scored against the Council of Economic
Experts (peaks 1992-02, 2001-02, 2008-01, 2020-02; troughs 1993-07, 2003-06, 2009-04, 2020-04)
and ECRI.  'Within the month' = the call's data month is no later than the month after the
turning month.  The 1992 peak falls inside the unadjusted first two years and is kept with
that caveat.  Grid ceilings, in sample.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/nat/can')
import numpy as np, pandas as pd
import can_claims_breadth as C
NAT='/home/claude/lab/nat/deu'
LAENDER=['Schleswig-Holstein','Hamburg','Mecklenburg-Vorpommern','Niedersachsen','Bremen','Nordrhein-Westfalen','Hessen','Rheinland-Pfalz','Saarland','Baden-Württemberg','Bayern','Berlin','Brandenburg','Sachsen-Anhalt','Thüringen','Sachsen']
COUNCIL=[('1992-02','1993-07'),('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')]
ECRI=[('1991-01','1994-04'),('2001-01','2003-08'),('2008-04','2009-01'),('2019-05','2020-04')]
def grid(SA, refs, label, sm_set=(1,2,3), amp_set=(2.,5.,10.,15.,20.), mph_set=(3,5), r_set=(1,2,3), top=4):
    rows=[]
    for sm,amp,mph,r in itertools.product(sm_set,amp_set,mph_set,r_set):
        D=C.hdi(SA,sm,amp,mph); calls=C.peak_calls(D,r); got,other=C.score(calls,refs)
        e=[v[2] for v in got.values()]; lag=[C.md(v[0],refs[i]) for i,v in got.items()]
        rows.append((len(got),-len(other),sum(x==0 for x in e),sum(abs(x)<=1 for x in e),sum(l<=1 for l in lag),(sm,amp,mph,r),got,other))
    rows.sort(key=lambda r:(r[0]+0.5*r[1],r[0],r[4],r[2]),reverse=True)
    print(f'\n=== {label}: hits / other / exact / within 1 / in-month | (smooth, amp log points, min phase, run)')
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
    P=pd.read_csv(f'{NAT}/DEU_unemployed_by_land_nsa.csv',index_col=0,parse_dates=True)
    SA=pd.concat([C.sa_rt(P[c]).rename(c) for c in LAENDER],axis=1)
    print('Laender on file:',SA.shape[1],'| span',SA.index.min().strftime('%Y-%m'),'->',SA.index.max().strftime('%Y-%m'))
    for label,refs in (('the Council',COUNCIL),('ECRI',ECRI)):
        Pk=[C.ts(p) for p,t in refs]; Tr=[C.ts(t) for p,t in refs]
        grid(SA,Pk,f'PEAKS against {label}, Laender breadth (unemployed rising)')
        grid(-SA,Tr,f'TROUGHS against {label}, Laender breadth (unemployed falling)')
