import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
ch=dict(channels('Canada'))
for _e in PANELS['Canada']['chrono']:
    pk_off,tr_off,freq=ep3(_e,'M')
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    ds=dating_series('Canada',w0,trm)
    if ds is None: print(pk_off,'no route'); continue
    nm,spec,n,L=ds
    gp,gt=bench._ds_lists(spec)
    names={id(v):k for k,v in ch.items()}
    dt=[(names.get(id(x),'?'),ch_trough(x,w0,w1,0.12,n,L,abstain=False)) for x in gt]
    dp=[(names.get(id(x),'?'),ch_peak(x,w0,med([d for _,d in dt]) or w1,0.01,n,abstain=False)) for x in gp]
    print(f"{pk_off}/{tr_off}: peak "+', '.join(f'{k}={v.date() if v is not None else None}' for k,v in dp)
          +'  | trough '+', '.join(f'{k}={v.date() if v is not None else None}' for k,v in dt))
