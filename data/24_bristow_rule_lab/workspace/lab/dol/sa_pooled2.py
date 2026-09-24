"""Weekly seasonal adjustment with no look-ahead, a pooled warm-up and moving factors.

Every state shares the calendar, so the week-of-year pattern can be estimated from all
fifty-three at once: one year of fifty-three states carries as much information about the
calendar as fifty-three years of one state.  The factors are therefore POOLED across
states until a state has `own_years` of its own history, and state-specific after that.

The factors are re-estimated each December from the data available then and applied
unchanged for the following twelve months, and they are estimated on a MOVING SEVEN-YEAR
WINDOW - the span of the default 3x5 seasonal filter in X-13ARIMA-SEATS - with medians
rather than means across years, so that the 1980s calendar does not set the factors used
in the 2020s and a recession inside the window does not tilt them.  No observation is
adjusted with information that did not exist when it was published.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
WIN=7
def woy(idx): return np.array([min(53,(t.dayofyear-1)//7+1) for t in idx])
def _fac(X,passes=3):
    seas=pd.DataFrame(0.0,index=X.index,columns=X.columns); w=woy(X.index)
    cols=list(X.columns)
    for p in range(passes):
        de=X-seas
        span=53 if p==0 else 27
        tr=de.rolling(span,center=True,min_periods=max(6,span//3)).mean().bfill().ffill()
        R=X-tr
        own={}; pooled={}; NS=np.zeros(X.shape)
        for k in range(1,54):
            m=(w==k)
            if not m.any(): continue
            v=R.values[m]; v=v[np.isfinite(v)]
            pooled[k]=float(np.median(v)) if len(v) else 0.0
            row=np.empty(len(cols))
            for ci,c in enumerate(cols):
                q=R[c].values[m]; q=q[np.isfinite(q)]
                if len(q)>=3: own[(c,k)]=float(np.median(q))
                row[ci]=own.get((c,k),pooled[k])
            NS[m,:]=row
        mu=float(np.median(list(pooled.values())))
        pooled={k:v-mu for k,v in pooled.items()}; own={k:v-mu for k,v in own.items()}
        seas=pd.DataFrame(NS-mu,index=X.index,columns=X.columns)
    return own,pooled
def sa_pooled(P,own_years=5,win=WIN):
    X=np.log(P.replace(0,np.nan)).interpolate().bfill().ffill()
    out=pd.DataFrame(index=X.index,columns=X.columns,dtype=float)
    for y in sorted(set(X.index.year)):
        hist=X[(X.index.year<y)&(X.index.year>=y-win)]
        m=(X.index.year==y)
        if len(hist)<80:
            out.loc[m]=X.loc[m]; continue
        own,pooled=_fac(hist)
        w=woy(X.index[m])
        for c in X.columns:
            enough=X[X.index.year<y][c].notna().sum()>=own_years*52
            adj=np.array([(own.get((c,int(k)),pooled.get(int(k),0.0)) if enough
                           else pooled.get(int(k),0.0)) for k in w])
            out.loc[m,c]=X.loc[m,c].values-adj
    return out.dropna(how='all')
def build(col,out_panel,out_nat):
    d=pd.read_csv('/home/claude/lab/dol/ar539.csv',low_memory=False)
    d['wk']=pd.to_datetime(d['c2'],errors='coerce'); d=d.dropna(subset=['wk'])
    d['v']=pd.to_numeric(d[col],errors='coerce')
    P=d.pivot_table(index='wk',columns='st',values='v',aggfunc='sum').sort_index()
    P=P[P.index>=pd.Timestamp('1986-02-01')]; P=P.loc[:,P.notna().mean()>0.95]
    grid=pd.date_range(P.index.min(),P.index.max(),freq='W-SAT')
    P=P.reindex(P.index.union(grid)).interpolate(method='time').reindex(grid)
    SA=sa_pooled(P); SA.to_csv(out_panel)
    N=sa_pooled(pd.DataFrame({'US':P.sum(axis=1)}))['US']
    if out_nat: pd.DataFrame({'initial claims':np.exp(N)}).to_csv(out_nat)
    X=N*100.0
    def resid(lo,hi):
        s=X[lo:hi]; t=s.rolling(53,center=True,min_periods=27).mean(); r=(s-t).dropna()
        f=r.groupby(woy(r.index)).median(); return float(f.max()-f.min())
    print(f'{col}: panel {SA.shape}  residual week-of-year  whole {resid("1986-01","2026-12"):.1f}  '
          f'1990-2000 {resid("1990-01","2000-12"):.1f}  2015-2026 {resid("2015-01","2026-12"):.1f} log points')
    return SA
if __name__=='__main__':
    IC=build('c3','/home/claude/lab/dol/US_state_claims_sa_pooled.csv','/home/claude/lab/weekly/US_nat_claims_pooled.csv')
    CC=build('c8','/home/claude/lab/dol/US_state_cc_sa_pooled.csv',None)
    BOTH=pd.concat([IC.add_suffix(' IC'),CC.add_suffix(' CC')],axis=1)
    BOTH.to_csv('/home/claude/lab/dol/US_state_claims_both_sa.csv')
    print('both:',BOTH.shape)
