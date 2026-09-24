import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.ABSTAIN=False
s=load('/home/claude/lab/kei/KOR_RS__T.csv')
for (n,L,bt,bp) in [(3,12,0.00,0.02),(3,12,0.00,0.03),(1,12,0.00,0.03),(3,12,0.03,0.02)]:
    hp=ht=0; rows=[]
    for pk_off,tr_off in KR_M:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        tr=ch_trough(s,w0,w1,bt,n,L,abstain=False)
        pk=ch_peak(s,w0,tr if tr is not None else w1,bp,n,abstain=False)
        a,_=hit(pk,pk_off,'M'); b,_=hit(tr,tr_off,'M'); hp+=a; ht+=b
        rows.append(f'  {pk_off}->{tr_off}  {pk:%Y-%m}/{tr:%Y-%m} {"P" if a else "-"}{"T" if b else "-"}')
    print(f'n={n} L={L} bt={bt} bp={bp}  peak {hp}/11 trough {ht}/11')
    for r in rows: print(r)
    print()
