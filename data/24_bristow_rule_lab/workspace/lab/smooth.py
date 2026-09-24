"""The smoothing is trailing, and a trailing average lags.

m(t) is the mean of t-2, t-1 and t, so its turning points sit about a month after the
series' own.  That is necessary in real time - you cannot average months you have not
seen - but dating is retrospective, and a CENTRED average has no lag by construction.
Tested here: trailing, centred, and a few other filters, on the dating pass only.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_orig=bench.ma
HEND13=np.array([-0.019,-0.028,0.0,0.066,0.147,0.214,0.240,0.214,0.147,0.066,0.0,-0.028,-0.019])
def mk(kind):
    cache={}
    def ma2(x,n):
        k=(id(x),n,kind); e=cache.get(k)
        if e is not None and e[0] is x: return e[1]
        if kind=='trailing': r=x.rolling(n).mean()
        elif kind=='centred': r=x.rolling(n,center=True,min_periods=1).mean()
        elif kind=='centred5': r=x.rolling(5,center=True,min_periods=1).mean()
        elif kind=='median3': r=x.rolling(n,center=True,min_periods=1).median()
        elif kind=='ema': r=x.ewm(span=n,adjust=False).mean()
        elif kind=='henderson':
            v=x.values.astype(float); out=np.full(len(v),np.nan)
            h=len(HEND13)//2
            for i in range(h,len(v)-h):
                out[i]=float(np.dot(HEND13,v[i-h:i+h+1]))
            r=pd.Series(out,index=x.index).fillna(x.rolling(n,center=True,min_periods=1).mean())
        elif kind=='none': r=x.astype(float)
        else: raise ValueError(kind)
        cache[k]=(x,r); return r
    return ma2
for kind in ('trailing','centred','centred5','median3','ema','henderson','none'):
    bench.ma=mk(kind)
    for m in (bench,):
        pass
    tot=[]
    try:
        for c in ALL: tot+=run_country_concept(c,**K)
    except Exception as e:
        print(kind,'ERR',str(e)[:60]); bench.ma=_orig; continue
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'{kind:10s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}  bias {sa:+.2f}/{sb:+.2f}')
bench.ma=_orig
