"""Real-time seasonal adjustment of DOL's national weekly claims, 1967 on.
Week-of-year factors as MEDIANS on a moving seven-year window, refitted each December from
the data available then, applied unchanged for the following year.  No look-ahead."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
def woy(idx): return np.array([min(53,(t.dayofyear-1)//7+1) for t in idx])
def factors(x, passes=3):
    w=woy(x.index); seas=np.zeros(len(x))
    for p in range(passes):
        de=pd.Series(x.values-seas,index=x.index)
        span=53 if p==0 else 27
        tr=de.rolling(span,center=True,min_periods=max(6,span//3)).mean().bfill().ffill()
        r=x.values-tr.values; ns=np.zeros(len(x)); fac={}
        for k in range(1,54):
            m=(w==k)
            if m.sum(): fac[k]=float(np.median(r[m])); ns[m]=fac[k]
        mu=np.median(list(fac.values())); fac={k:v-mu for k,v in fac.items()}; ns-=mu; seas=ns
    return fac
def sa_rt(s, win=7, minobs=104):
    x=np.log(s.astype(float).replace(0,np.nan)).interpolate().bfill().ffill()
    out=pd.Series(index=x.index,dtype=float); fac=None
    for y in sorted(set(x.index.year)):
        hist=x[(x.index.year<y)&(x.index.year>=y-win)]
        if len(hist)>=minobs: fac=factors(hist)
        m=(x.index.year==y); w=woy(x.index[m])
        adj=np.array([fac.get(int(k),0.0) for k in w]) if fac else np.full(m.sum(),np.nan)
        out[m]=x.values[m]-adj
    return np.exp(out.dropna())
if __name__=='__main__':
    df=pd.read_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_1967.csv',index_col=0,parse_dates=True)
    out=pd.DataFrame({'ic_sa_rt':sa_rt(df.ic_nsa.dropna()),'cc_sa_rt':sa_rt(df.cc_nsa.dropna())})
    out.to_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_sa_rt.csv')
    print('real-time SA:',out.index.min().date(),out.index.max().date(),len(out))
    for c,ref in (('ic_sa_rt','ic_sa'),('cc_sa_rt','cc_sa')):
        a=np.log(out[c]); b=np.log(df[ref].dropna()); j=a.index.intersection(b.index)
        d=(a[j]-b[j])*100
        # residual seasonality of the real-time series: week-of-year medians of detrended log
        y=a; tr=y.rolling(53,center=True,min_periods=20).mean(); r=(y-tr).dropna()*100
        g=r.groupby(woy(r.index)).median()
        print(f'  {c}: vs DOL SA mean diff {d.mean():+.1f} lp, sd {d.std():.1f} lp;  residual week-of-year spread {g.max()-g.min():.1f} lp')
