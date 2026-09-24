"""§12 item 7, settled at last: the channel-level depth test, judged on a panel chronology
the configuration has never seen.

The filter: at the peak, a channel abstains if the fall from its own high inside the search
window is less than `f` per cent of its own level.  Three American channels in 1969 - real
personal income less transfers, real consumption and retail volume - never turn at all
inside that episode, each falls less than 1.1 per cent after its own high, and each still
votes, dragging the median of seven four months late.

The filter has always fixed 1969.  What it has never had is a test on a panel chronology
outside the nine the configuration was chosen on.  Germany is that chronology: the German
Council of Economic Experts dates a panel directly, so a filter deciding which channels of
a panel may vote has something to act on there.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP=set(); bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
DE=[('1966-03','1967-05'),('1974-01','1975-07'),('1980-01','1982-11'),('1992-02','1993-07'),
    ('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')]
def L(f): return load('/home/claude/lab/kei/'+f)
CH=[('industrial production',L('DEU_PRVM_BTE.csv')),('retail volume',L('DEU_TOVM_G47.csv')),
    ('exports',L('DEU_EX__T.csv')),('imports',L('DEU_IM__T.csv')),
    ('construction production',L('DEU_PRVM_F.csv')),('car registrations',L('DEU_TOCAPA_G45.csv'))]
def ch_fall_pct(s,w0,w1,n=3):
    m=ma(prep(s,n,False,120,60),n)[w0:w1].dropna()
    if len(m)<4: return None
    hi=float(m.max()); i=m.idxmax()
    lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
    return (hi-lo)/max(abs(hi),1e-9)*100.0
def peak_with_filter(chs,w0,w1,f,cap=18):
    ds=[]
    for nm,s in chs:
        d=ch_fall_pct(s,w0,w1)
        if f>0 and (d is None or d<f): continue
        p=ch_peak(s,w0,w1,0.01,3,abstain=True)
        if p is not None: ds.append(p)
    return med(ds) if ds else None
def run(f):
    hp=0; ep=[]; rows=[]; n=0
    for pk_off,tr_off in DE:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in CH if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<2: continue
        n+=1
        b=date_any('Germany',use,w0,w1,**K)
        tr=b['trough']
        wp1=tr if tr is not None else w1
        p=peak_with_filter(use,w0,wp1,f)
        a,e=hit(p,pk_off,'M'); hp+=a
        if e is not None: ep.append(abs(e))
        rows.append((pk_off,e))
    return hp,n,(np.mean(ep) if ep else float('nan')),rows
print('GERMANY — the channel-level depth filter at the peak, shipped configuration otherwise')
print(f'{"filter":>10s}  {"peaks":>8s}  {"mean error":>10s}   per-episode error')
for f in (0.0,0.5,1.0,1.5,2.0,3.0):
    hp,n,mad,rows=run(f)
    print(f'{f:9.1f}%  {hp:3d}/{n:<4d}  {mad:10.2f}   {[r[1] for r in rows]}')
