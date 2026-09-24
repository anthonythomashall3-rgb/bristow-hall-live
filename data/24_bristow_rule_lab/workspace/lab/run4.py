import sys; sys.path.insert(0,'/home/claude/lab')
from us import *
import pandas as pd, numpy as np

def bracket(u,pk,tk,tail=24,thr=0.50):
    stat=sahm(u,12); p,t=ts(pk),ts(tk)
    cand=[e for e in episodes(stat,thr) if e[0]>=p and e[0]<=t+pd.DateOffset(months=12)]
    if not cand: return None
    e=cand[0]; w0,w1=e[0], e[-1]+pd.DateOffset(months=12)
    spk=stat[w0:w1].dropna().idxmax()
    m=ma3(u)
    upk=m[w0:e[-1]+pd.DateOffset(months=tail)].dropna().idxmax()
    d3=delta(u,3)
    her=d3[w0:w1].dropna().idxmax()
    return her,spk,upk

for lab,u,PKs,TRs in (('POSTWAR',U,PK,TR),('INTERWAR',IW,IW_PK,IW_TR)):
    print('='*88); print(lab)
    print(f"{'trough':10s} {'herald':>9s} {'S peak':>9s} {'u peak':>9s} | {'[S,u] holds':>11s} {'[her,u] holds':>13s} {'width':>6s}")
    okS=okH=0;n=0
    for pk,tk in zip(PKs,TRs):
        b=bracket(u,pk,tk)
        if b is None: print(f'{tk:10s}   no crossing'); continue
        her,spk,upk=b; t=ts(tk); n+=1
        a1 = (spk<=t<=upk); a2=(her<=t<=upk)
        okS+=a1; okH+=a2
        print(f"{tk:10s} {her.strftime('%Y-%m'):>9s} {spk.strftime('%Y-%m'):>9s} {upk.strftime('%Y-%m'):>9s} | {str(a1):>11s} {str(a2):>13s} {md(upk,spk):>6d}")
    print(f'   [S peak, u peak] contains the trough: {okS}/{n}      [herald, u peak]: {okH}/{n}')
