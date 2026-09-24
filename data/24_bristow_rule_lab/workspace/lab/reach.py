import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
# the configuration actually shipped
cur={}
for c in ALL:
    for r in run_country_concept(c,**K):
        cur[(c,str(r['peak_off']))]=r
miss=[k for k,r in cur.items() if not (r['hp'] and r['ht'])]
print(f'{len(miss)} contractions missed at one or both ends by the shipped configuration\n')

# is the episode REACHABLE by any defensible setting?
GRID=[]
for concept in ['level','growth','diffusion']:
    for bt in [0.01,0.02,0.03,0.05]:
        for bp in [0.01,0.02,0.03,0.05]:
            for cap in [9,12,18,24]:
                GRID.append(dict(concept=concept,band_t=bt,band_p=bp,peak_cap=cap))
print(f'{len(GRID)} settings tried per episode (three concepts x bands x peak window)\n')
print(f'{"chronology":24s} {"episode":20s} {"ch":>3s} {"shipped":>9s}   {"reachable":>9s}  {"best setting"}')
data=0; method=0
for c in ALL:
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    for _e in cfg['chrono']:
        pk,tr,fq=ep3(_e,cfg['freq'])
        key=(c,str(pk))
        if key not in miss: continue
        r0=cur[key]
        pkm=ts(pk) if fq=='M' else q2m(pk); trm=ts(tr) if fq=='M' else q2m(tr)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        best=None
        for g in GRID:
            cpt=g['concept']
            try:
                if cpt=='diffusion':
                    d=date_diffusion_panel(use,w0,w1)
                    if d['peak'] is None or d['trough'] is None: continue
                else:
                    kk=dict(K); kk.update({k2:v2 for k2,v2 in g.items() if k2!='concept'})
                    if cpt=='growth': kk['min_depth']=1e9
                    else: kk['min_depth']=0.0
                    d=date_any(c,use,w0,w1,**kk)
            except Exception: continue
            a,ep=hit(d['peak'],pk,fq); b,et=hit(d['trough'],tr,fq)
            sc=(a+b, -(abs(ep or 99)+abs(et or 99)))
            if best is None or sc>best[0]: best=(sc,g,ep,et)
        ok = best is not None and best[0][0]==2
        if ok: method+=1
        else: data+=1
        tag='YES' if ok else 'no'
        gs='' if best is None else f"{best[1]['concept']}, bt={best[1]['band_t']}, bp={best[1]['band_p']}, cap={best[1]['peak_cap']}  (ep={best[2]}, et={best[3]})"
        print(f'{c:24s} {str(pk)+" "+str(tr):20s} {len(use):3d} {str(r0["ep"])+"/"+str(r0["et"]):>9s}   {tag:>9s}  {gs}')
print()
print(f'reachable by some defensible setting (method gap): {method}')
print(f'not reachable by any setting (data limit):         {data}')
