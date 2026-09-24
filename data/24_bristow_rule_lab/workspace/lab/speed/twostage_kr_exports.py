"""Korea: exports (published on the first day of the following month) as the zero-lag closer of
the two-stage trough; D on the OECD Korean panel opens (in hand +2).  Exports: OECD KEI values
(seasonally adjusted, final vintage - a first pass, not real-time factors), log x 100; the
close is a rise of `a` log points from the minimum for `r` months.  Scored against Statistics
Korea's troughs since 1990 and ECRI's.  Result (2 September 2026): a negative - see the log."""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, bench
from bench import kei, pro, load, ts
import ecbcs_speed as E, twostage_ec as T2
KEI='/home/claude/lab/kei'
def panel():
    return [(nm,pro(p,kind)) for nm,p,kind in kei('KOR') if nm in ('industrial production','retail volume','employment')]
if __name__=='__main__':
    D=B.composite_deviation(panel(),12,3,1).dropna(); D.index=D.index+pd.DateOffset(months=2)
    KR_T=[ts(bench.ep3(e,'M')[1]) for e in bench.PANELS['Korea']['chrono'] if ts(bench.ep3(e,'M')[1])>=pd.Timestamp('1990-01-01')]
    ECRI_T=[E.ts(d) for k,d in E.ECRI['Korea'] if k=='T' and d>='1990-01']
    ex=np.log(load(f'{KEI}/KOR_EX__T.csv'))*100.0
    print('panel',[n for n,_ in panel()],'exports',ex.index.min().date(),'->',ex.index.max().date())
    for label,T in (('Statistics Korea',KR_T),('ECRI',ECRI_T)):
        print(f'\n=== troughs against {label} ({len(T)}): {[t.strftime("%Y-%m") for t in T]}')
        tt=[(p,d) for p,d in B.real_time_trough_calls(panel(),publication_lag=2,fall_months=4,drop=0.5,min_channels=1) if d>=pd.Timestamp('1990-01-01')]
        T2.line("the tool's own clause on D, published +2 months",tt,T)
        rows=[]
        for a,r in itertools.product((3.,5.,8.,12.),(1,2,3)):
            calls=[(p+pd.DateOffset(months=1),d) for p,d in T2.twostage(D,ex,a,r)]
            rows.append((T2.line(f'  exports a={a} r={r}',calls,T,show=False),a,r,calls))
        rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
        for res,a,r,calls in rows[:4]: T2.line(f'  exports a={a:.0f} r={r}',calls,T)
