import json,math,datetime as dt,sys,collections
sys.path.insert(0,'/tmp/rmv3')
from registry2 import FAMILIES,FAMILY_LABEL,REG
YEAR=365.2425; MONTH=30.4375
P=json.load(open('/tmp/rmv3/params_stage1.json'))['params']
ATS=json.load(open('/tmp/rmv3/ats.json'))
RAW=json.load(open('/tmp/rmv3/raw.json'))
G=len(FAMILIES)
start=dt.date(1957,1,1); end=dt.date.today()
days=[start+dt.timedelta(days=i) for i in range((end-start).days+1)]
# forward-fill S_i,t  (Eq.6 applied to the Eq.10 daily information state)
Sgrid={}
for sid,pr in P.items():
    a=[(dt.date.fromisoformat(d),v) for d,v in ATS.get(sid,[])]
    if not a: continue
    q50,q75=pr['q50'],pr['q75']; sc=q75-q50
    out=[None]*len(days); j=0; cur=None
    for i,day in enumerate(days):
        while j<len(a) and a[j][0]<=day:
            cur=max(0.0,(a[j][1]-q50)/sc); j+=1
        out[i]=cur
    Sgrid[sid]=out
# family / dependency structure
fam_deps=collections.defaultdict(lambda: collections.defaultdict(list))
for sid,pr in P.items(): fam_deps[pr['family']][pr['dep']].append(sid)
def med(x):
    x=sorted(x); n=len(x)
    return x[n//2] if n%2 else (x[n//2-1]+x[n//2])/2
FAM=collections.defaultdict(list); SU=[]; COV=[]; BRE=[]
for i in range(len(days)):
    present=0; tot=0.0; pos=0
    for g in FAMILIES:
        ds=[]
        for dep,sids in fam_deps[g].items():
            vs=[Sgrid[s][i] for s in sids if Sgrid.get(s) and Sgrid[s][i] is not None]
            if vs: ds.append(med(vs))
        if ds:
            f=sum(ds)/len(ds); present+=1; tot+=f
            if f>0: pos+=1
        else: f=None
        FAM[g].append(f)
    SU.append(tot/G); COV.append(present/G); BRE.append(pos/G)
# Eq.12/13 accumulated stress + persistence over the active model span
# The frozen chronology that Eq.12 expects does not exist yet, so the
# active-span reset uses a declared, label-free stand-in: the span restarts
# whenever the headline Stress Unit falls to or below its own prior median.
# This is an operating-policy choice, not a derived chronology rule.
_su_sorted=sorted(SU); QUIET=_su_sorted[len(_su_sorted)//2]
AS=[0.0]*len(days); PERS=[0.0]*len(days); span_start=0
for i in range(len(days)):
    if SU[i]<=QUIET:
        span_start=i; AS[i]=0.0
    else:
        AS[i]=(AS[i-1] if i>0 else 0.0)+((SU[i-1] if i>0 else SU[i])+SU[i])/2.0/MONTH
    dur=max((i-span_start)/MONTH,1.0/MONTH)
    PERS[i]=AS[i]/dur
# Eq.15 recovery deficit over the real-economy set Q
QSET=['PAYEMS','CE16OV','INDPRO','GDPC1','CMRMTSPL','PCEC96','W875RX1','HOUST']
QSET=[q for q in QSET if q in RAW]
lev={}
for qs in QSET:
    a=[(dt.date.fromisoformat(d),v) for d,v in RAW[qs]]
    out=[None]*len(days); j=0; cur=None
    for i,day in enumerate(days):
        while j<len(a) and a[j][0]<=day: cur=a[j][1]; j+=1
        out[i]=cur
    lev[qs]=out
REC=[]
peaks={q:None for q in QSET}
for i in range(len(days)):
    acc=[]
    for qs in QSET:
        v=lev[qs][i]
        if v is None: continue
        if peaks[qs] is None or v>peaks[qs]: peaks[qs]=v
        pk=peaks[qs]
        if pk: acc.append(max(0.0,(pk-v)/abs(pk)))
    REC.append(sum(acc)/len(acc) if acc else 0.0)
# propagation: 90-day rise in family breadth
PROP=[max(0.0,BRE[i]-BRE[i-90]) if i>=90 else 0.0 for i in range(len(days))]
# Eq.16 common-scale conversion, frozen at build
def qq(v,p):
    v=sorted(v); n=len(v); k=(n-1)*p; f=math.floor(k); c=min(f+1,n-1)
    return v[int(k)] if f==c else v[f]*(c-k)+v[c]*(k-f)
comps={'intensity':SU,'breadth':BRE,'persistence':PERS,'burden':AS,'propagation':PROP,'recovery':REC}
SCALE={}
for k,v in comps.items():
    a=qq(v,0.50); b=qq(v,0.75)
    if b<=a: b=a+(qq(v,0.90)-a if qq(v,0.90)>a else 1.0)
    SCALE[k]={'q50':a,'q75':b}
def T(k,x): 
    s=SCALE[k]; return max(0.0,(x-s['q50'])/(s['q75']-s['q50']))
NI=[]
for i in range(len(days)):
    t=[T(k,comps[k][i]) for k in comps]
    NI.append(math.sqrt(sum(x*x for x in t)/6.0))
out={
 'schema':'bristow-hall.v2.1-candidate.artifact-params.v1',
 'built_from_generation':None,
 'grid_start':days[0].isoformat(),'grid_end':days[-1].isoformat(),
 'G':G,'families':FAMILIES,'family_labels':FAMILY_LABEL,
 'scale':SCALE,'params':P,'quiet_reset_su':QUIET,
 'abstained':json.load(open('/tmp/rmv3/params_stage1.json'))['missing'],
 'series_family':{s:P[s]['family'] for s in P},
 'live_map':{P[s]['live']:s for s in P if P[s].get('live')},
 'latest':{'date':days[-1].isoformat(),'SU':SU[-1],'NI':NI[-1],'coverage':COV[-1],
           'breadth':BRE[-1],'persistence':PERS[-1],'burden':AS[-1],
           'propagation':PROP[-1],'recovery':REC[-1],
           'components':{k:T(k,comps[k][-1]) for k in comps},
           'families':{g:FAM[g][-1] for g in FAMILIES}},
}
# weekly downsample of the history for charts
idx=[i for i in range(len(days)) if i%7==0 or i==len(days)-1]
out['history']={'d':[days[i].isoformat() for i in idx],
                'ni':[round(NI[i],4) for i in idx],'su':[round(SU[i],4) for i in idx],
                'br':[round(BRE[i],4) for i in idx],'as':[round(AS[i],4) for i in idx],
                'pe':[round(PERS[i],4) for i in idx],'re':[round(REC[i],4) for i in idx],
                'pr':[round(PROP[i],4) for i in idx],'cv':[round(COV[i],4) for i in idx]}
out['family_history']={g:[round(FAM[g][i],4) if FAM[g][i] is not None else None for i in idx] for g in FAMILIES}
json.dump(out,open('/tmp/rmv3/params.json','w'))
print('days',len(days),'hist pts',len(idx))
L=out['latest']
print('LATEST',L['date'],'SU=%.3f NI=%.3f cov=%.2f breadth=%.2f burden=%.2f pers=%.3f rec=%.4f prop=%.3f'%(L['SU'],L['NI'],L['coverage'],L['breadth'],L['burden'],L['persistence'],L['recovery'],L['propagation']))
print('components',{k:round(v,3) for k,v in L['components'].items()})
print('families',{g:(round(v,3) if v is not None else None) for g,v in L['families'].items()})
import os; print('size %.1f KB'%(os.path.getsize('/tmp/rmv3/params.json')/1024))
