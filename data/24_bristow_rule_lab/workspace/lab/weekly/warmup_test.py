"""Why the weekly state file's record begins in 1991 - measured, and the 1990 peak's reach on it.

The weekly caller (speed_final.py / final_rt.py) reports its record from 1991, "the first year with
five years of history behind the factors".  This script measures what a shorter warm-up does:
sa_realtime.py is rerun with the factor floor at 104, 156, 208 and 260 weeks (two to five years),
the breadth index of the shipped peak clause is rebuilt on each, and three things are read - the
month-of-year residual of the adjusted national sum over 1988-90 against 1992-99 (mean absolute
deviation of the block's month means, log points), the winter (December-March) maximum of the
breadth index in 1987/88, 1988/89 and 1989/90, and the peak calls the clause makes before 2002.
Run on 3 September 2026; output in warmup_test.log.
"""
import pandas as pd, numpy as np, warnings, sys; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude/lab/weekly')
import sa_realtime as S
def mo(t): return pd.Timestamp(t.year,t.month,1)
d=pd.read_csv('/home/claude/lab/dol/ar539.csv',low_memory=False)
d['wk']=pd.to_datetime(d['c2'],errors='coerce'); d=d.dropna(subset=['wk'])
d['ic']=pd.to_numeric(d['c3'],errors='coerce')
P=d.pivot_table(index='wk',columns='st',values='ic',aggfunc='sum').sort_index()
P=P[P.index>=pd.Timestamp('1986-02-01')]
P=P.loc[:,P.notna().mean()>0.95]
grid=pd.date_range(P.index.min(),P.index.max(),freq='W-SAT')
P=P.reindex(P.index.union(grid)).interpolate(method='time').reindex(grid)
exec(open('/home/claude/lab/weekly/final_caller.py').read().split("def peak_calls")[1].join(["def peak_calls",""]).split("def trough_calls(")[0])
def breadth(SA,sm,L,thsq):
    K=SA.rolling(sm).mean()*100.0
    S_=K-K.rolling(L,min_periods=L//2).min()
    return ((S_>=thsq).sum(axis=1)/S_.notna().sum(axis=1)*100.0).dropna()
def resid(SA,yrs):
    N=np.exp(SA).sum(axis=1); L=np.log(N)*100
    m_=L.groupby([L.index.year,L.index.month]).mean().unstack(); dev=m_.sub(m_.mean(axis=1),axis=0)
    return dev.loc[yrs].mean(axis=0).abs().mean()
if __name__=='__main__':
    for minobs,fy in [(260,1991),(208,1990),(156,1989),(104,1988)]:
        SA=pd.DataFrame({c:S.sa_realtime(P[c],first_year=fy,minobs=minobs) for c in P.columns}).dropna(how='all')
        Bd=breadth(SA,13,104,25.)
        calls=peak_calls(Bd,50.,2,52,'first_above')
        m=Bd.resample('ME').max()
        w=[float(round(m.loc[f'{y}-12':f'{y+1}-03'].max(),1)) for y in (1987,1988,1989)]
        print(f'factor floor {minobs} weeks (first factor year {fy}): residual 1988-90 {resid(SA,[1988,1989,1990]):.1f} log points, 1992-99 {resid(SA,list(range(1992,2000))):.1f}; '
              f'winter breadth maxima 87/88, 88/89, 89/90 = {w}; Jun-Nov 1990 monthly maxima {[float(x) for x in m.loc["1990-06":"1990-11"].round(1).tolist()]}')
        print('   peak calls before 2002:',[(p.strftime("%Y-%m-%d"),dt.strftime("%Y-%m")) for p,dt in calls if p<pd.Timestamp('2002-01-01')])
    print('\nReading: at every floor the 1988-90 factors carry 8-16 points of residual against 2 from 1992, the breadth index'
          ' spikes above 70 per cent every winter through 1989/90, the clause fires on the first spike (January 1988) and'
          ' never re-arms before the July 1990 peak; 1990 is data-bound on this object and the five-year warm-up stands.')
