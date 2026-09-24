import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
di=load('/home/claude/lab/esri2/JPN_DI_coincident.csv')
ci=load('/home/claude/lab/esri2/JPN_CI_coincident.csv')
print('ESRI coincident DI, ESRI\'s own 50-percent rule, on ESRI\'s own chronology')
for name,ser,fn in [('DI (50-line rule)',di,'di'),('CI (band rule)',ci,'ci')]:
    hp=ht=n=0; det=[]
    for pk_off,tr_off in JP_M:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if ser.index.min()>w0 or ser.index.max()<trm: continue
        n+=1
        if fn=='di':
            d=di_dates_censored(ser,w0,w1,50.0,1,1); pk,tr=d['peak'],d['trough']
        else:
            tr=ch_trough(ser,w0,w1,0.03,3,12,abstain=False)
            pk=ch_peak(ser,w0,tr if tr is not None else w1,0.02,3,abstain=False)
        a,_=hit(pk,pk_off,'M'); b,_=hit(tr,tr_off,'M'); hp+=a; ht+=b
        f=lambda x: x.strftime('%Y-%m') if x is not None else '--'
        det.append(f'   {pk_off}->{tr_off}  {f(pk)}/{f(tr)}  {"P" if a else "-"}{"T" if b else "-"}')
    print(f'{name}:  peak {hp}/{n}  trough {ht}/{n}')
    for d_ in det: print(d_)
