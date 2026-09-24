import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from pat import pat_cycle
import pandas as pd
bench.ABSTAIN=True
lvl=load('/home/claude/lab/kei/KOR_RSNOR.csv')   # the reference series level (normalised)
rt =load('/home/claude/lab/kei/KOR_RSRT.csv')    # OECD's own ratio to trend
def scoreit(tag,ser,n_=3,bt=0.0,bp=0.01):
    hp=ht=0; det=[]
    for pk_off,tr_off in KR_M:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if ser is None or ser.index.min()>w0 or ser.index.max()<trm: det.append((pk_off,'--','--')); continue
        tr=ch_trough(ser,w0,w1,bt,n_,12,abstain=False)
        pk=ch_peak(ser,w0,tr if tr is not None else w1,bp,n_,abstain=False)
        a,ep=hit(pk,pk_off,'M'); b,et=hit(tr,tr_off,'M'); hp+=a; ht+=b
        det.append((pk_off,ep,et))
    print(f'{tag:44s} peak {hp}/11 trough {ht}/11   errs {det}')
scoreit('OECD ratio to trend (HP)',rt)
for lm in (57,75,96,120):
    scoreit(f'PAT on the reference level, long_ma={lm}',pat_cycle(lvl,long_ma=lm))
