"""Leave one turning point out.

For each turning point in the record, the three settings of the peak detector are chosen on
the other eight and the choice is scored on the one held out.  Nothing about the held-out
turning point enters the choice.  The selection criterion is the same one used to ship:
hits first, then fewest other calls, then the neighbourhood average.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/lab/dol/final_record.py').read().split("D,mn=hdi")[0])
CH=('initial claims','continued weeks claimed')
AMPS=list(range(28,49,1)); MPHS=list(range(8,19,1)); SMS=[1,2,3,4]
CACHE={}
def calls(sm,amp,mph):
    k=(sm,amp,mph)
    if k not in CACHE:
        D,mn=hdi(CH,sm,float(amp),mph); CACHE[k]=sorted(esri_calls(D,mn,1,5,15))
    return CACHE[k]
def score(cl,targets):
    TTp={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in targets}
    hits={}; oth=0
    for pub,dt in cl:
        if pub<S0: continue
        near=min(TTp,key=lambda k: abs(dt-TTp[k]))
        if abs(pub-TTp[near])<=2 and abs(dt-TTp[near])<=2 and near not in hits:
            hits[near]=(pub-TTp[near],dt-TTp[near])
        else: oth+=1
    return hits,oth
ALL=list(PK)
grid=[(sm,a,m) for sm in SMS for a in AMPS for m in MPHS]
print('building grid',len(grid),'points')
for g in grid: calls(*g)
print('done')
rows=[]
for held in ALL:
    rest=[k for k in ALL if k!=held]
    sc={g:score(calls(*g),rest) for g in grid}
    def rob(g):
        sm,a,m=g; tot=[];
        for da in (-1,0,1):
            for dm in (-1,0,1):
                gg=(sm,a+da,m+dm)
                if gg in sc: tot.append(sc[gg][0].__len__()-0.5*sc[gg][1])
        return np.mean(tot)
    bestg=max(grid,key=lambda g:(len(sc[g][0]),-sc[g][1],rob(g)))
    h,o=score(calls(*bestg),ALL)
    got = held in h
    rows.append((held,bestg,len(sc[bestg][0]),sc[bestg][1],got,h.get(held)))
print(f'{"held out":10s} {"chosen on the other eight":26s} {"fit 8":6s} {"other":6s} {"held out":9s}')
n=0
for held,g,f,o,got,d in rows:
    n+=got
    print(f'{held:10s} sm={g[0]} amp={g[1]} mph={g[2]:<12d} {f}/8   {o:2d}     '
          f'{"HIT lag %+d err %+d"%d if got else "missed"}')
print(f'=> out of sample the detector reaches {n} of {len(ALL)}')
