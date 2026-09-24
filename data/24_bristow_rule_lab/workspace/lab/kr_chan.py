import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.ABSTAIN=False
PANELS['Korea']['ch']=PANELS['Korea']['ch']+imf('KOR'); bench._cache.pop('Korea',None)
chs=channels('Korea')
print(f'{"channel":34s} {"peak":>6s} {"trough":>7s}   (of episodes it covers)')
for nm,s in chs:
    hp=ht=n=0
    for pk_off,tr_off in KR_M:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if s.index.min()>w0 or s.index.max()<trm: continue
        n+=1
        tr=ch_trough(s,w0,w1,0.03,3,12,abstain=False)
        pk=ch_peak(s,w0,tr if tr is not None else w1,0.02,3,abstain=False)
        a,_=hit(pk,pk_off,'M'); b,_=hit(tr,tr_off,'M'); hp+=a; ht+=b
    if n: print(f'{nm:34s} {hp:3d}/{n:<3d} {ht:3d}/{n:<3d}')
# cyclical component of the reference series treated as a growth cycle
print()
for nm,s in chs:
    if 'reference' not in nm and 'IMF' not in nm: continue
    hp=ht=n=0
    for pk_off,tr_off in KR_M:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if s.index.min()>w0 or s.index.max()<trm: continue
        n+=1
        m=ma(s,3)[w0:w1].dropna()
        if len(m)<6: continue
        v=m.values; idx=m.index; runmax=0; best=None
        for j in range(1,len(v)):
            if v[j-1]>v[runmax]: runmax=j-1
            d=v[runmax]-v[j]
            if best is None or d>best[0]: best=(d,runmax,j)
        pk,tr=idx[best[1]],idx[best[2]]
        a,_=hit(pk,pk_off,'M'); b,_=hit(tr,tr_off,'M'); hp+=a; ht+=b
    if n: print(f'MAXSWING {nm:25s} {hp:3d}/{n:<3d} {ht:3d}/{n:<3d}')
