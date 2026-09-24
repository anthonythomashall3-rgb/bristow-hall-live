"""Does the IGAE - the series the Mexican committee names first - recover the two peaks
the OECD panel misses?  Reported whichever way it falls."""
import sys; sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude')
import bench
from bench import *
import bristow_rule_v3 as B
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP=set(); bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
MX=[(None,'1983-06'),('1985-09','1986-12'),('1994-11','1995-05'),('2000-09','2002-01'),
    ('2008-06','2009-05'),('2019-05','2020-05')]
def L(f): return load('/home/claude/lab/kei/'+f)
CH=[('industrial production',L('MEX_PRVM_BTE.csv')),
    ('construction production',L('MEX_PRVM_F.csv')),
    ('exports',L('MEX_EX__T.csv')),
    ('imports',L('MEX_IM__T.csv')),
    ('retail volume',L('MEX_TOVM_G47.csv')),
    ('unemployment',L('MEX_UNEMP__T.csv'))]
IGAE=load('/home/claude/lab/mex/MEX_igae_sa.csv')
OECD=load('/home/claude/lab/kei/MEX_RS__T.csv')
print(f'IGAE, INEGI open data, self-adjusted  {IGAE.index.min().date()}..{IGAE.index.max().date()}  n={len(IGAE)}')
print(f"OECD Mexican reference series         {OECD.index.min().date()}..{OECD.index.max().date()}  n={len(OECD)}")

def run(chs, ds=None):
    hp=ht=0; np_=nt=0; rows=[]
    for pk_off,tr_off in MX:
        trm=ts(tr_off); pkm=ts(pk_off) if pk_off else trm-pd.DateOffset(months=18)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<2: rows.append((pk_off,None,tr_off,None)); continue
        d=None
        if ds is not None:
            nm2,s2=ds
            if s2.index.min()<=w0 and s2.index.max()>=trm: d=(nm2,s2,3,12)
        vol=quantity('Mexico',use) or use
        b=B.date_turning_points(use,w0,w1,volume_channels=vol,concept='level',
              lam=500000.,band_trough=0.12,band_peak=0.01,peak_cap=18,
              smooth=3,lookback=12,dating_series=d)
        e1=None
        if pk_off:
            np_+=1; a,e1=hit(b['peak'],pk_off,'M'); hp+=a
        nt+=1; c,e2=hit(b['trough'],tr_off,'M'); ht+=c
        rows.append((pk_off,e1,tr_off,e2))
    return hp,np_,ht,nt,rows

for label,chs,ds in [
    ('the six-channel OECD panel (shipped)',            CH, None),
    ('panel + IGAE as a seventh channel',               CH+[('IGAE',IGAE)], None),
    ('panel, routed to the IGAE the committee names',   CH, ('IGAE',IGAE)),
    ("panel, routed to the OECD's reference series",    CH, ('OECD reference series',OECD)),
]:
    hp,np_,ht,nt,rows=run(chs,ds)
    print(f'\n{label}:  peaks {hp}/{np_}   troughs {ht}/{nt}')
    for x in rows:
        print(f'   peak {str(x[0]):>8s} err {str(x[1]):>5s}    trough {x[2]} err {str(x[3]):>5s}')
