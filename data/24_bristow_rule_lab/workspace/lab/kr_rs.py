import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, itertools
bench.ABSTAIN=False
s=load('/home/claude/lab/kei/KOR_RS__T.csv')
best=[]
for n in (1,2,3,4,5,6):
  for L in (9,12,15,18):
    for bt in (0.0,0.01,0.02,0.03,0.05,0.08):
      for bp in (0.0,0.01,0.02,0.03,0.05):
        hp=ht=0
        for pk_off,tr_off in KR_M:
            pkm=ts(pk_off); trm=ts(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            tr=ch_trough(s,w0,w1,bt,n,L,abstain=False)
            pk=ch_peak(s,w0,tr if tr is not None else w1,bp,n,abstain=False)
            a,_=hit(pk,pk_off,'M'); b,_=hit(tr,tr_off,'M'); hp+=a; ht+=b
        best.append((hp+ht,hp,ht,n,L,bt,bp))
best.sort(reverse=True)
for x in best[:15]: print('tot=%2d peak=%2d/11 trough=%2d/11  n=%d L=%d band_t=%.2f band_p=%.2f'%x)
print()
print('--- detail at shipped n=3,L=12,bt=0.03,bp=0.02')
for pk_off,tr_off in KR_M:
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    tr=ch_trough(s,w0,w1,0.03,3,12,abstain=False)
    pk=ch_peak(s,w0,tr if tr is not None else w1,0.02,3,abstain=False)
    a,_=hit(pk,pk_off,'M'); b,_=hit(tr,tr_off,'M')
    print(f'  {pk_off} -> {tr_off}   ours {pk:%Y-%m} / {tr:%Y-%m}   {"OK" if a else "  "} {"OK" if b else "  "}')
