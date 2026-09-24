import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import bristow_rule_v3 as B
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
CONC={'United States':'level','United States (interwar)':'level','Canada':'level','Brazil':'level',
      'Euro area':'level','Spain':'level','France':'level','Japan':'diffusion','Korea':'growth'}
hp=ht=n=0
for c in ALL:
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=chs
        if freq=='Q':
            use=[(nm,B.to_quarter(x)) for nm,x in use]
        vol=quantity(c,use) or use
        r=B.date_turning_points(use,w0,w1,volume_channels=vol,concept=CONC[c],
                                lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,
                                smooth=(1 if freq=='Q' else 3),lookback=(4 if freq=='Q' else 12),
                                dating_series=dating_series(c,w0,trm))
        a,_=hit(r['peak'],pk_off,freq); b,_=hit(r['trough'],tr_off,freq)
        hp+=a; ht+=b; n+=1
print(f'TOOL on the same panels: peak {hp}/{n}  trough {ht}/{n}')
