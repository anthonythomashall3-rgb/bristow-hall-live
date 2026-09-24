import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/lab/dol/final_record.py').read().split("D,mn=hdi")[0])
TTp={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in PK}
CH=('initial claims','continued weeks claimed')
def sc(sm,amp,mph):
    D,mn=hdi(CH,sm,amp,mph); hits={}; oth=0
    for pub,dt in sorted(esri_calls(D,mn,1,5,15)):
        if pub<S0: continue
        near=min(TTp,key=lambda k: abs(dt-TTp[k]))
        if abs(pub-TTp[near])<=2 and abs(dt-TTp[near])<=2 and near not in hits: hits[near]=1
        else: oth+=1
    return len(hits),oth
for sm in (1,2,3,4):
    print(f'sm={sm}   amp ->', '  '.join(f'{a:>5d}' for a in range(28,49,2)))
    for mph in (8,10,11,12,13,14,16,18):
        row=[]
        for amp in range(28,49,2):
            h,o=sc(sm,float(amp),mph); row.append(f'{h}/{o}')
        print(f'  mph={mph:2d}    ', '  '.join(f'{c:>5s}' for c in row))
