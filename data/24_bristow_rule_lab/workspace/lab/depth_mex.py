"""§12 item 7 re-run on the SEVEN-channel Mexican panel (the IGAE added)."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP=set(); bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
MX=[(None,'1983-06'),('1985-09','1986-12'),('1994-11','1995-05'),('2000-09','2002-01'),
    ('2008-06','2009-05'),('2019-05','2020-05')]
def L(f): return load('/home/claude/lab/kei/'+f)
CH=[('industrial production',L('MEX_PRVM_BTE.csv')),('construction production',L('MEX_PRVM_F.csv')),
    ('exports',L('MEX_EX__T.csv')),('imports',L('MEX_IM__T.csv')),
    ('retail volume',L('MEX_TOVM_G47.csv')),('unemployment',L('MEX_UNEMP__T.csv')),
    ('IGAE',load('/home/claude/lab/mex/MEX_igae_sa.csv'))]
def ch_fall_pct(s,w0,w1,n=3):
    m=ma(prep(s,n,False,120,60),n)[w0:w1].dropna()
    if len(m)<4: return None
    hi=float(m.max()); i=m.idxmax(); lo=float(m[i:].min())
    return (hi-lo)/hi*100.0
def peak_with_filter(chs,w0,w1,f):
    ds=[]
    for nm,s in chs:
        d=ch_fall_pct(s,w0,w1)
        if f>0 and (d is None or d<f): continue
        p=ch_peak(s,w0,w1,0.01,3,abstain=True)
        if p is not None: ds.append(p)
    return med(ds) if ds else None
def run(f):
    hp=0; ep=[]; rows=[]; n=0
    for pk_off,tr_off in MX:
        if pk_off is None: continue
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in CH if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<2: continue
        n+=1
        b=date_any('Mexico',use,w0,w1,**K); tr=b['trough']
        p=peak_with_filter(use,w0,tr if tr is not None else w1,f)
        a,e=hit(p,pk_off,'M'); hp+=a
        if e is not None: ep.append(abs(e))
        rows.append((pk_off,e))
    return hp,n,(np.mean(ep) if ep else float('nan')),rows
print('MEXICO — the channel-level depth filter at the peak, seven-channel panel')
print(f'{"filter":>10s}  {"peaks":>8s}  {"mean error":>10s}   per-episode error')
for f in (0.0,1.0,1.5,2.0,3.0,5.0):
    hp,n,mad,rows=run(f)
    print(f'{f:9.1f}%  {hp:3d}/{n:<4d}  {mad:10.2f}   {[r[1] for r in rows]}')
