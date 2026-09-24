"""The channel-level depth filter, on both new panel chronologies."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP=set(); bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
def L(f): return load('/home/claude/lab/kei/'+f)
DE=[('1966-03','1967-05'),('1974-01','1975-07'),('1980-01','1982-11'),('1992-02','1993-07'),
    ('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')]
MX=[('1985-09','1986-12'),('1994-11','1995-05'),('2000-09','2002-01'),
    ('2008-06','2009-05'),('2019-05','2020-05')]
CHD=[('industrial production',L('DEU_PRVM_BTE.csv')),('retail volume',L('DEU_TOVM_G47.csv')),
     ('exports',L('DEU_EX__T.csv')),('imports',L('DEU_IM__T.csv')),
     ('construction production',L('DEU_PRVM_F.csv')),('car registrations',L('DEU_TOCAPA_G45.csv'))]
CHM=[('industrial production',L('MEX_PRVM_BTE.csv')),('construction production',L('MEX_PRVM_F.csv')),
     ('exports',L('MEX_EX__T.csv')),('imports',L('MEX_IM__T.csv')),
     ('retail volume',L('MEX_TOVM_G47.csv')),('unemployment',L('MEX_UNEMP__T.csv'))]
def fall_pct(s,w0,w1,n=3):
    m=ma(prep(s,n,False,120,60),n)[w0:w1].dropna()
    if len(m)<4: return None
    hi=float(m.max()); i=m.idxmax()
    lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
    return (hi-lo)/max(abs(hi),1e-9)*100.0
def run(chrono,chs,country,f):
    hp=0; ep=[]; rows=[]; n=0
    for pk_off,tr_off in chrono:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<2: continue
        n+=1
        b=date_any(country,use,w0,w1,**K); tr=b['trough']; wp1=tr if tr is not None else w1
        ds=[]
        for nm,s in use:
            d=fall_pct(s,w0,wp1)
            if f>0 and (d is None or d<f): continue
            p=ch_peak(s,w0,wp1,0.01,3,abstain=True)
            if p is not None: ds.append(p)
        p=med(ds) if ds else None
        a,e=hit(p,pk_off,'M'); hp+=a
        if e is not None: ep.append(abs(e))
        rows.append(e)
    return hp,n,(np.mean(ep) if ep else float('nan')),rows
for name,chrono,chs,ctry in [('GERMANY',DE,CHD,'Germany'),('MEXICO',MX,CHM,'Mexico')]:
    print(f'=== {name} — channel-level depth filter at the peak')
    for f in (0.0,0.5,1.0,1.5,2.0,3.0,5.0):
        hp,n,mad,rows=run(chrono,chs,ctry,f)
        print(f'   filter {f:4.1f}%   peaks {hp}/{n}   mean error {mad:5.2f}   {rows}')
