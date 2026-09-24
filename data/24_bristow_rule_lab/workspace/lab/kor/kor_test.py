"""Korea, on the committee's own object at last."""
import sys; sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
KR=[('1974-02','1975-06'),('1979-02','1980-09'),('1984-02','1985-09'),('1988-01','1989-07'),
    ('1992-01','1993-01'),('1996-03','1998-08'),('2000-08','2001-07'),('2002-12','2005-04'),
    ('2008-01','2009-02'),('2011-08','2013-03'),('2017-09','2020-05')]
co=load('/home/claude/lab/kor/KOR_coincident_cyclical.csv')
print(f'   the committee\'s own coincident cyclical component  {co.index.min().date()}..{co.index.max().date()}  n={len(co)}')
oecd=[(nm,s) for nm,s in channels('Korea') if nm=='monthly reference GDP']
PANEL=[(nm,s) for nm,s in channels('Korea') if nm not in bench.SKIP]
def run(mode):
    hp=ht=0; ep=[]; et=[]; rows=[]; n=0
    for pk_off,tr_off in KR:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if mode in ('committee object',):
            if co.index.min()>w0: rows.append((pk_off,None,tr_off,None)); continue
            n+=1
            tr=ch_trough(co,w0,w1,0.0,3,12,abstain=False)
            pk=ch_peak(co,w0,tr if tr is not None else w1,0.0,3,abstain=False)
        elif mode=='OECD substitute':
            s=oecd[0][1]
            if s.index.min()>w0: rows.append((pk_off,None,tr_off,None)); continue
            n+=1
            tr=ch_trough(s,w0,w1,0.0,3,12,abstain=False)
            pk=ch_peak(s,w0,tr if tr is not None else w1,0.0,3,abstain=False)
        else:
            use=[(nm,s) for nm,s in PANEL if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: rows.append((pk_off,None,tr_off,None)); continue
            n+=1
            b=date_any('Korea',use,w0,w1,**K); pk,tr=b['peak'],b['trough']
        a,e1=hit(pk,pk_off,'M'); c,e2=hit(tr,tr_off,'M')
        hp+=a; ht+=c
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    return hp,ht,n,(np.mean(ep) if ep else float('nan')),(np.mean(et) if et else float('nan')),rows
print()
print(f'{"route":52s} {"peaks":>8s} {"troughs":>8s}  {"MAD p":>6s} {"MAD t":>6s}')
res={}
for m in ('OECD substitute','panel','committee object'):
    r=run(m); res[m]=r
    print(f'{m:52s} {r[0]:3d}/{r[2]:<4d} {r[1]:4d}/{r[2]:<4d}  {r[3]:6.2f} {r[4]:6.2f}')
print()
print("per episode, the committee's own object:")
for x in res['committee object'][5]:
    print(f'   peak {x[0]} err {str(x[1]):>5s}    trough {x[2]} err {str(x[3]):>5s}')
