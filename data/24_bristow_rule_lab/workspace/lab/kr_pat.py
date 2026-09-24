import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from pat import pat_cycle
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
ref=load('/home/claude/lab/kei/KOR_RS__T.csv')          # OECD ratio-to-trend (HP)
lvl=None
# the OECD also publishes the reference series normalised; rebuild a level to detrend
chs=[(nm,s) for nm,s in channels('Korea') if nm not in bench.SKIP]
comp=composite_level(quantity('Korea',chs) or chs)
for tag,ser,n_,L_ in [('OECD ratio-to-trend (HP)',ref,3,12),
                      ('PAT on the panel composite',pat_cycle(comp),3,12),
                      ('PAT on the OECD reference level',None,3,12)]:
    if ser is None: continue
    hp=ht=0; det=[]
    for pk_off,tr_off in KR_M:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if ser.index.min()>w0 or ser.index.max()<trm: det.append((pk_off,'--','--',0,0)); continue
        tr=ch_trough(ser,w0,w1,0.0,n_,L_,abstain=False)
        pk=ch_peak(ser,w0,tr if tr is not None else w1,0.01,n_,abstain=False)
        a,ep=hit(pk,pk_off,'M'); b,et=hit(tr,tr_off,'M'); hp+=a; ht+=b
        det.append((pk_off,pk.strftime('%Y-%m') if pk is not None else '--',
                    tr.strftime('%Y-%m') if tr is not None else '--',ep,et))
    print(f'{tag:34s} peak {hp}/11 trough {ht}/11')
    for d in det: print('     ',d)
