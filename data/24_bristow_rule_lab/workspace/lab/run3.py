import sys; sys.path.insert(0,'/home/claude/lab')
from us import *
import pandas as pd, numpy as np
S12U=sahm(U,12); S12I=sahm(IW,12)
def runs(stat,thr=0.5):
    out=[];cur=[]
    for d,v in stat.dropna().items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur);cur=[]
    if cur: out.append(cur)
    return out
print('POSTWAR crossing-run lengths (S>=0.50):')
for e in runs(S12U):
    print(f'   {e[0].date()} .. {e[-1].date()}   {len(e):3d} months')
print('\nINTERWAR crossing-run lengths:')
for e in runs(S12I):
    print(f'   {e[0].date()} .. {e[-1].date()}   {len(e):3d} months')
