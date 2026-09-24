"""South Africa, held out: every route, at the frozen shipped configuration."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
ZA=[('1946-07','1947-04'),('1948-11','1950-02'),('1951-12','1953-03'),('1955-04','1956-09'),
    ('1958-01','1959-03'),('1960-04','1961-08'),('1965-04','1965-12'),('1967-05','1967-12'),
    ('1970-12','1972-08'),('1974-08','1977-12'),('1981-08','1983-03'),('1984-06','1986-03'),
    ('1989-02','1993-05'),('1996-11','1999-08'),('2007-11','2009-08'),('2013-11','2017-04'),
    ('2019-06','2020-04')]
co=load('/home/claude/lab/sarb/ZAF_coincident.csv')
oecd=load('/home/claude/lab/kei/ZAF_RS__T.csv')
CH=[('coincident indicator',co),
    ('retail volume',load('/home/claude/lab/kei/ZAF_TOVM_G47.csv')),
    ('manufacturing production',load('/home/claude/lab/kei/ZAF_PRVM_C.csv')),
    ('monthly reference GDP',oecd)]
def rtt(s,lam=500000.0):
    y=np.log(s.dropna()); y=y[np.isfinite(y)]
    t=pd.Series(hp_filter(y.values,lam),index=y.index)
    return np.exp(y-t)*100.0
co_c=rtt(co)
def run(mode):
    hp_=ht=0; ep=[]; et=[]; rows=[]; n=0
    for pk_off,tr_off in ZA:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if co.index.min()>w0: continue
        n+=1
        if mode=='committee object':
            tr=ch_trough(co_c,w0,w1,0.0,3,12,abstain=False)
            _u=ch_trough(co_c,w0,w1,0.0,3,12,abstain=False,refine=False)
            pk=ch_peak(co_c,w0,_u if _u is not None else w1,0.0,3,abstain=False,refine=False)
        elif mode=='OECD substitute':
            tr=ch_trough(oecd,w0,w1,0.0,3,12,abstain=False)
            _u=ch_trough(oecd,w0,w1,0.0,3,12,abstain=False,refine=False)
            pk=ch_peak(oecd,w0,_u if _u is not None else w1,0.0,3,abstain=False,refine=False)
        elif mode=='committee object, level clauses':
            tr=ch_trough(co,w0,w1,0.12,3,12,abstain=False)
            pk=ch_peak(co,w0,tr if tr is not None else w1,0.01,3,abstain=False)
        else:  # panel, growth form
            use=[(nm,s) for nm,s in CH if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: use=[(nm,s) for nm,s in CH if s.index.min()<=trm and s.index.max()>=trm]
            b=date_any('South Africa',use,w0,w1,min_depth=1e9,
                       **{k:v for k,v in K.items() if k!='min_depth'})
            pk,tr=b['peak'],b['trough']
        a,e1=hit(pk,pk_off,'M'); b2,e2=hit(tr,tr_off,'M')
        hp_+=a; ht+=b2
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    return hp_,ht,n,np.mean(ep),np.mean(et),sum(1 for x in ep if x<=2),sum(1 for x in et if x<=2),rows
print(f'{"route":42s} {"peaks":>7s} {"troughs":>8s}  {"MAD p":>6s} {"MAD t":>6s}  {"w2 p":>5s} {"w2 t":>5s}')
for m in ('OECD substitute','committee object','committee object, level clauses','panel'):
    r=run(m)
    print(f'{m:42s} {r[0]:3d}/{r[2]:<3d} {r[1]:4d}/{r[2]:<3d}  {r[3]:6.2f} {r[4]:6.2f}  {r[5]:5d} {r[6]:5d}')
print()
r=run('committee object')
print('per episode, the committee object:')
for x in r[7]: print(f'   {x[0]} {str(x[1]):>5s}    {x[2]} {str(x[3]):>5s}')

print()
print('DIAGNOSTIC (not a configuration change): error against the length of the phase')
r=run('committee object')
for x in r[7]:
    a=ts(x[0]); b=ts(x[2]); L=(b.year-a.year)*12+(b.month-a.month)
    print(f'   {x[0]} to {x[2]}  {L:3d} months   peak err {str(x[1]):>5s}  trough err {str(x[3]):>5s}')
print()
print('DIAGNOSTIC: the same object at other lookbacks L (shipped is 12, averaged 9/12/15)')
import bench as B
for L in (12,18,24,36):
    hp_=ht=0; ep=[]; et=[]; n=0
    for pk_off,tr_off in ZA:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if co.index.min()>w0: continue
        n+=1
        tr=ch_trough(co_c,w0,w1,0.0,3,L,abstain=False)
        _u=ch_trough(co_c,w0,w1,0.0,3,L,abstain=False,refine=False)
        pk=ch_peak(co_c,w0,_u if _u is not None else w1,0.0,3,abstain=False,refine=False)
        a,e1=hit(pk,pk_off,'M'); b2,e2=hit(tr,tr_off,'M')
        hp_+=a; ht+=b2
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
    print(f'   L={L:2d}: peaks {hp_}/{n} troughs {ht}/{n}  MAD {np.mean(ep):.2f}/{np.mean(et):.2f}')
