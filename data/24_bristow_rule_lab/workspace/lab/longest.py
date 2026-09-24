import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, os
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
IMFDIR='/home/claude/lab/imf'
MAP={'IND_SA_IX':'industrial production','IND_IX':'industrial production',
     'C_IX':'manufacturing production'}
AREA={'Korea':'KOR','Japan':'JPN','Brazil':'BRA','Canada':'CAN','Spain':'ESP','United States':'USA'}

def nobs(p):
    try: return len(pd.read_csv(p))
    except Exception: return 0

def longest(country,area,ch):
    """Replace a channel by the IMF series of the same concept when IMF is longer."""
    ch=list(ch); byname={nm:i for i,(nm,p,k) in enumerate(ch)}
    for code,concept in MAP.items():
        p=f'{IMFDIR}/{area}_{code}.csv'
        if not os.path.exists(p): continue
        if concept in byname:
            i=byname[concept]
            if nobs(p)>nobs(ch[i][1]): ch[i]=(concept,p,'level')
        else:
            ch.append((concept,p,'level')); byname[concept]=len(ch)-1
        break_=False
    return ch

ORIG={c:list(PANELS[c]['ch']) for c in ALL}
def base():
    for c in ALL: PANELS[c]['ch']=list(ORIG[c]); bench._cache.pop(c,None)
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    return t
t=base(); s=score(t,'',show=False)
print('BASE            peak %d/80  trough %d/80'%(s['hp'],s['ht']))

# variant A: longest-series substitution everywhere
for c,a in AREA.items():
    PANELS[c]['ch']=longest(c,a,ORIG[c]); bench._cache.pop(c,None)
t2=[]
for c in ALL: t2+=run_country_concept(c,**K)
s2=score(t2,'',show=False)
print('LONGEST (all)   peak %d/80  trough %d/80'%(s2['hp'],s2['ht']))
for c in ALL:
    x=score([r for r in t if r['country']==c],'',show=False)
    y=score([r for r in t2 if r['country']==c],'',show=False)
    if (x['hp'],x['ht'])!=(y['hp'],y['ht']):
        print('   %-26s %d/%d -> %d/%d   %d/%d -> %d/%d'%(c,x['hp'],x['n'],y['hp'],y['n'],x['ht'],x['n'],y['ht'],y['n']))
