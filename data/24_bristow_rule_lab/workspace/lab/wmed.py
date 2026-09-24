"""§12 item 2, the last modelling gap: a depth-WEIGHTED channel median.

The hard filter of item 7 is inert outside the chronology it was built for.  Its motive is
sound, though: in 1969 three American channels fall less than 1.1 per cent and still get a
full vote.  The continuous form of the same idea is to weight each channel's date by how
far that channel actually fell, so a channel that barely turned counts for little without
being thrown away.  Weight w = its own fall in per cent, raised to `gamma`; gamma = 0
recovers the plain median and gamma large approaches taking the deepest channel alone.

Judged on the American panel, and on the two panel chronologies the configuration has never
seen, at the same time.  A fix that helps the United States and hurts Germany or Mexico is
not a fix.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
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
     ('retail volume',L('MEX_TOVM_G47.csv')),('unemployment',L('MEX_UNEMP__T.csv')),
     ('IGAE',load('/home/claude/lab/mex/MEX_igae_sa.csv'))]
US=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
US_C=[(a,b) for a,b in zip([e[0] for e in PANELS['United States']['chrono']],
                            [e[1] for e in PANELS['United States']['chrono']])]
def fall_pct(s,w0,w1,n=3):
    m=ma(prep(s,n,False,120,60),n)[w0:w1].dropna()
    if len(m)<4: return None
    hi=float(m.max()); i=m.idxmax()
    lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
    return (hi-lo)/max(abs(hi),1e-9)*100.0
def wmedian(pairs):
    """pairs: [(date, weight)].  The weighted median, taking the later of two middles."""
    pairs=[(d,max(w,0.0)) for d,w in pairs if d is not None]
    if not pairs: return None
    tot=sum(w for _,w in pairs)
    if tot<=0: return _med_plain([d for d,_ in pairs])
    pairs.sort(key=lambda x:x[0]); c=0.0
    for d,w in pairs:
        c+=w
        if c>=tot/2.0: return d
    return pairs[-1][0]
def _med_plain(ds):
    ds=sorted(ds); n=len(ds)
    return ds[n//2] if n%2 else ds[n//2]
def run(chrono,chs,country,gamma,freq='M'):
    hp=0; ep=[]; n=0; rows=[]
    for pk_off,tr_off in chrono:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<2: continue
        n+=1
        b=date_any(country,use,w0,w1,**K); tr=b['trough']; wp1=tr if tr is not None else w1
        pr=[]
        for nm,s in use:
            p=ch_peak(s,w0,wp1,0.01,3,abstain=True)
            d=fall_pct(s,w0,wp1)
            if p is not None: pr.append((p,(d or 0.0)**gamma if gamma>0 else 1.0))
        p=wmedian(pr)
        a,e=hit(p,pk_off,'M'); hp+=a
        if e is not None: ep.append(abs(e))
        rows.append(e)
    return hp,n,(np.mean(ep) if ep else float('nan')),rows
USC=[(a,b) for a,b in PANELS['United States']['chrono']]
print(f'{"gamma":>6s}  {"United States":>22s}  {"Germany":>16s}  {"Mexico":>16s}')
for g in (0.0,0.5,1.0,1.5,2.0,3.0):
    u=run(USC,US,'United States',g); d=run(DE,CHD,'Germany',g); m=run(MX,CHM,'Mexico',g)
    print(f'{g:6.1f}  {u[0]:3d}/{u[1]:<3d} err {u[2]:5.2f}      {d[0]:3d}/{d[1]:<3d} err {d[2]:5.2f}   {m[0]:3d}/{m[1]:<3d} err {m[2]:5.2f}')
print()
u=run(USC,US,'United States',0.0); print('US per-episode, gamma=0:',u[3])
u=run(USC,US,'United States',1.0); print('US per-episode, gamma=1:',u[3])
