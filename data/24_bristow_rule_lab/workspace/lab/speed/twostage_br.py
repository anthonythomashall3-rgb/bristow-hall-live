"""The two-stage trough in Brazil on the CNI's industrial confidence index (ICEI).

The Confederação Nacional da Indústria's ICEI is monthly from 1999 on its old basis and from
January 2010 on the current one (lab/acq/brsurv/, the 'série recente' workbook fetched 2
September 2026 from portaldaindustria.com.br; total industry with its current-conditions and
expectations components, unadjusted), published in the middle of the month it describes (the
August 2026 index on 13 August) - a zero-lag survey like the Philadelphia Fed's.  Stage 1 is
the level route's D on the Brazilian panel as shipped (bench.PANELS['Brazil'] channels), each
reading in hand two months after its month; stage 2 the survey rising `a` points from its
minimum for `r` months, published in the month of the call.  Scored against CODACE's two
troughs in the survey's era - 2016-Q4 and 2020-Q2, read as their middle months as the bench
does - and ECRI's Brazilian troughs; the earlier CODACE troughs lie before 2010.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, bench
from bench import pro, ts, q2m, ep3
import ecbcs_speed as E, twostage_ec as T2
def panel():
    out=[]
    for nm,p,kind in bench.PANELS['Brazil']['ch']:
        try: s=pro(p,kind)
        except Exception: continue
        out.append((nm,s[s>0].dropna()))
    return out
def d_available():
    D=B.composite_deviation(panel(),12,3,2).dropna(); D.index=D.index+pd.DateOffset(months=2); return D
if __name__=='__main__':
    D=d_available(); print('panel',[n for n,_ in panel()],'D in hand',D.index.min().strftime('%Y-%m'),'->',D.index.max().strftime('%Y-%m'))
    tro=[]
    for e in bench.PANELS['Brazil']['chrono']:
        pk,tr,f=ep3(e,'M'); t=ts(tr) if f=='M' else q2m(tr)
        if t>=pd.Timestamp('2010-06-01'): tro.append(t)
    ECRI_T=[E.ts(d) for k,d in E.ECRI['Brazil'] if k=='T' and d>='2010-06']
    X=pd.read_csv('/home/claude/lab/acq/brsurv/BRA_icei_2010_nsa.csv',index_col=0,parse_dates=True)
    for label,T in (('CODACE (quarters as mid-months)',tro),('ECRI',ECRI_T)):
        print(f'\n=== troughs against {label} ({len(T)}): {[t.strftime("%Y-%m") for t in T]}')
        tt=[(p,d) for p,d in B.real_time_trough_calls(panel(),publication_lag=2,fall_months=4,drop=0.5,min_channels=2) if d>=pd.Timestamp('2010-06-01')]
        T2.line("the tool's own clause on D, published +2 months",tt,T)
        for col in X.columns:
            s=E.sa_rt(X[col].dropna()).dropna(); rows=[]
            for a,r in itertools.product((2.,3.,5.,8.),(1,2,3)):
                calls=T2.twostage(D,s,a,r); rows.append((T2.line(f'  ICEI {col} a={a} r={r}',calls,T,show=False),a,r,calls))
            rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
            for res,a,r,calls in rows[:2]: T2.line(f'  ICEI {col} a={a:.0f} r={r}',calls,T)
