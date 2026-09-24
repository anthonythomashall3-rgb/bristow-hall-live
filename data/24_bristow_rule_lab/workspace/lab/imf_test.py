import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, copy
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)

AREA={'Korea':'KOR','Japan':'JPN','Brazil':'BRA','Canada':'CAN','Spain':'ESP',
      'United States':'USA'}
EA=['DEU','NLD','BEL','AUT','ITA','ESP','FRA']

def base_score():
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    return score(tot,'',show=False), tot

b,tot=base_score()
print('BASE  peak %d/%d  trough %d/%d'%(b['hp'],b['n'],b['ht'],b['n']))
for c in ALL:
    s=score([r for r in tot if r['country']==c],'',show=False)
    print('   %-26s %2d/%-2d  %2d/%-2d'%(c,s['hp'],s['n'],s['ht'],s['n']))

ORIG={c:list(PANELS[c]['ch']) for c in ALL}

def restore():
    for c in ALL: PANELS[c]['ch']=list(ORIG[c])

print()
print('--- adding IMF Production Indexes, one country at a time')
for c,a in AREA.items():
    restore()
    add=imf(a)
    if not add: print('   %-26s no IMF series'%c); continue
    PANELS[c]['ch']=ORIG[c]+add
    tot2=[]
    for cc in ALL: tot2+=run_country_concept(cc,**K)
    s2=score([r for r in tot2 if r['country']==c],'',show=False)
    s1=score([r for r in tot  if r['country']==c],'',show=False)
    print('   %-26s %2d/%-2d -> %2d/%-2d   %2d/%-2d -> %2d/%-2d   (+%d channels)'%(
        c,s1['hp'],s1['n'],s2['hp'],s2['n'],s1['ht'],s1['n'],s2['ht'],s2['n'],len(add)))
restore()

print()
print('--- Euro area with IMF national production indexes')
add=[]
for a in EA: add+=[(f'{a} IMF production',p,k) for nm,p,k in imf(a)]
PANELS['Euro area']['ch']=ORIG['Euro area']+add
tot2=[]
for cc in ALL: tot2+=run_country_concept(cc,**K)
s2=score([r for r in tot2 if r['country']=='Euro area'],'',show=False)
s1=score([r for r in tot  if r['country']=='Euro area'],'',show=False)
print('   Euro area  %d/%d -> %d/%d   %d/%d -> %d/%d  (+%d channels)'%(
    s1['hp'],s1['n'],s2['hp'],s2['n'],s1['ht'],s1['n'],s2['ht'],s2['n'],len(add)))
restore()
