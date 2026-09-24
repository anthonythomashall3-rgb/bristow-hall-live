import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
exec(open('/home/claude/lab/diroute.py').read().split("for mode in")[0])
MODES=[('off',0)]+[(m,k) for m in ('peak','trough','both') for k in (0,5,8,10)]
res={}
for m,k in MODES:
    s,tot=run(m,k); res[(m,k)]=tot
oos_p=oos_t=n=0; picks={}
for c in ALL:
    best=max(MODES,key=lambda mk: sum(r['hp']+r['ht'] for r in res[mk] if r['country']!=c))
    picks[c]=best
    mine=[r for r in res[best] if r['country']==c]
    oos_p+=sum(r['hp'] for r in mine); oos_t+=sum(r['ht'] for r in mine); n+=len(mine)
print('in sample:', {mk:(sum(r['hp'] for r in res[mk]),sum(r['ht'] for r in res[mk])) for mk in MODES})
print(f'leave-one-chronology-out: peak {oos_p}/{n} trough {oos_t}/{n}')
print('rule chosen by the other eight:',picks)
