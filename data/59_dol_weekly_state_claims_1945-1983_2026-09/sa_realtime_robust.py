"""sa_realtime with MEDIAN week-of-year factors instead of means (an OCR-noise robustness variant, 5 Sep 2026).  Same
real-time discipline: factors re-estimated each December from data then available, applied unchanged for the next year."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
def woy(idx): return np.array([min(53,(t.dayofyear-1)//7+1) for t in idx])
def factors(x, passes=3):
    w=woy(x.index); seas=np.zeros(len(x))
    for p in range(passes):
        de=pd.Series(x.values-seas,index=x.index); span=53 if p==0 else 27
        tr=de.rolling(span,center=True,min_periods=max(6,span//3)).median().bfill().ffill()
        r=x.values-tr.values; ns=np.zeros(len(x)); fac={}
        for k in range(1,54):
            m=(w==k)&np.isfinite(r)
            if m.sum(): fac[k]=float(np.median(r[m])); ns[w==k]=fac[k]
        mu=np.mean(list(fac.values())); fac={k:v-mu for k,v in fac.items()}; ns-=mu; seas=ns
    return fac
def sa_realtime(s, first_year=1991, minobs=260):
    x=np.log(s.astype(float).replace(0,np.nan))
    out=pd.Series(index=x.index,dtype=float); fac=None
    for y in sorted(set(x.index.year)):
        m=(x.index.year==y); hist=x[x.index.year<y].dropna()
        if len(hist)>=minobs: fac=factors(hist)
        w=woy(x.index[m]); adj=np.array([fac.get(int(k),0.0) for k in w]) if fac else np.zeros(m.sum())
        out[m]=x.values[m]-adj
    return out.dropna()
