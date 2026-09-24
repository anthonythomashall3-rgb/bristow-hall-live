"""How flat is the peak configuration?"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/lab/dol/final_record.py').read().split("D,mn=hdi")[0])
TTp={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in PK}
def sc(chs,sm,amp,mph,r,pmin,cyc):
    D,mn=hdi(chs,sm,amp,mph)
    hits={}; oth=0
    for pub,dt in sorted(esri_calls(D,mn,r,pmin,cyc)):
        if pub<S0: continue
        near=min(TTp,key=lambda k: abs(dt-TTp[k]))
        if abs(pub-TTp[near])<=2 and abs(dt-TTp[near])<=2 and near not in hits: hits[near]=1
        else: oth+=1
    return len(hits),oth
CH=('initial claims','continued weeks claimed')
print('amplitude (log points), holding sm=3 mph=12 phase>=5 cycle>=15')
for amp in (20.,22.,25.,27.,30.,32.,35.,40.,45.,50.):
    print(f'   amp={amp:5.0f}  {sc(CH,3,amp,12,1,5,15)}')
print('minimum phase for a channel turn (months), holding sm=3 amp=30')
for mph in (6,8,9,10,12,14,15,18,21,24):
    print(f'   mph={mph:3d}  {sc(CH,3,30.,mph,1,5,15)}')
print('smoothing (months), holding amp=30 mph=12')
for sm in (1,2,3,4,5,6):
    print(f'   sm={sm:2d}   {sc(CH,sm,30.,12,1,5,15)}')
