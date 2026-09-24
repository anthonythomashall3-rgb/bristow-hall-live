"""Choose by robustness, not by the maximum.

A configuration that scores well only at one point of a grid and badly at its neighbours
has been fitted to the record rather than read off it.  The score is therefore computed
over a fine grid and each point is judged by the average of its own neighbourhood.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/lab/dol/final_record.py').read().split("D,mn=hdi")[0])
TTp={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in PK}
def sc(chs,sm,amp,mph):
    D,mn=hdi(chs,sm,amp,mph)
    hits={}; oth=0
    for pub,dt in sorted(esri_calls(D,mn,1,5,15)):
        if pub<S0: continue
        near=min(TTp,key=lambda k: abs(dt-TTp[k]))
        if abs(pub-TTp[near])<=2 and abs(dt-TTp[near])<=2 and near not in hits: hits[near]=1
        else: oth+=1
    return len(hits),oth,tuple(sorted(hits))
AMPS=list(range(16,61,2)); MPHS=list(range(4,25,2)); SMS=[2,3,4]
COMBOS=[('initial claims','continued weeks claimed'),('initial claims',),
        ('continued weeks claimed',),
        ('initial claims','continued weeks claimed','weeks compensated','first payments')]
for chs in COMBOS:
    G={}
    for sm in SMS:
        for ai,amp in enumerate(AMPS):
            for mi,mph in enumerate(MPHS):
                G[(sm,ai,mi)]=sc(chs,sm,float(amp),mph)
    rows=[]
    for (sm,ai,mi),v in G.items():
        nb=[G[(sm,a,m)] for a in range(max(0,ai-1),min(len(AMPS),ai+2))
                        for m in range(max(0,mi-1),min(len(MPHS),mi+2))]
        rob=np.mean([h-0.5*o for h,o,_ in nb])
        rows.append((rob,v[0],-v[1],sm,AMPS[ai],MPHS[mi],v[2]))
    rows.sort(reverse=True)
    print(f'=== {"+".join(c[:4] for c in chs)}   most robust neighbourhoods')
    for r in rows[:5]:
        print(f'   robust {r[0]:5.2f}   sm={r[3]} amp={r[4]} mph={r[5]}   {r[1]}/9 hits, {-r[2]} other   {list(r[6])}')
    b=max(rows,key=lambda r:(r[1],r[2]))
    print(f'   best point: sm={b[3]} amp={b[4]} mph={b[5]}  {b[1]}/9, {-b[2]} other  (robustness {b[0]:.2f})')
