import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, json
bench.ABSTAIN=True; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
K=dict(min_depth=5.0,lam=500000.)

def local_minima_count(m, gamma=0.25):
    """How many separate bottoms the window has: local minima within gamma of the
    window's peak-to-trough amplitude above the global minimum, separated by 5 months."""
    v=m.values; lo=float(v.min()); hi=float(v.max()); amp=max(hi-lo,1e-9)
    thr=lo+gamma*amp; idx=[]
    for i in range(2,len(v)-2):
        if v[i]<=thr and v[i]==v[max(0,i-3):i+4].min():
            if not idx or i-idx[-1]>=5: idx.append(i)
    return max(1,len(idx))

rows=[]
for c in ALL:
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    for _e in cfg['chrono']:
        pk,tr,fq=ep3(_e,cfg['freq'])
        pkm=ts(pk) if fq=='M' else q2m(pk); trm=ts(tr) if fq=='M' else q2m(tr)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        if not use: continue
        q=quantity(c,use) or use
        # which estimators are right?
        got={}
        for nm,kk in (('level',{**K,'min_depth':0.0}),('growth',{**K,'min_depth':1e9})):
            d=date_any(c,use,w0,w1,**kk)
            a,_=hit(d['peak'],pk,fq); b,_=hit(d['trough'],tr,fq); got[nm]=int(a)+int(b)
        d=date_diffusion_panel(use,w0,w1)
        a,_=hit(d['peak'],pk,fq); b,_=hit(d['trough'],tr,fq); got['diffusion']=int(a)+int(b)
        # observable features
        ci=composite_level(q); m=ma(ci,3)[w0:w1].dropna()
        deepest=min([maxdd(ma(s,3)[w0:w1].dropna()) or 0 for _,s in q])
        cdep=maxdd(m) or 0
        dur=md(trm,pkm)
        try: cy=cyc_hp(q,500000.,3); cyd=maxdd(cy[w0:w1].dropna()) or 0
        except Exception: cyd=0
        base=date_any(c,use,w0,w1,**K)
        rows.append(dict(country=c,ep=str(pk),freq=fq,nch=len(use),
                         deepest=deepest,cdepth=cdep,cycdepth=cyd,dur=dur,
                         nmin=local_minima_count(m),
                         steep=cdep/max(dur,1),
                         gapratio=cyd/(cdep-1e-9) if cdep<0 else 9.9,
                         spread=max(base['spread_peak'] or 0, base['spread_trough'] or 0),
                         **{f'ok_{k}':v for k,v in got.items()}))
json.dump(rows,open('feat.json','w'),default=str)
print('episodes:',len(rows))
best=lambda r: max(('level','growth','diffusion'), key=lambda k: r['ok_'+k])
import collections
print('\nbest estimator by episode count:',collections.Counter(best(r) for r in rows))
print('\nfeature means by best estimator:')
keys=['nch','deepest','cdepth','cycdepth','dur','nmin','steep','gapratio','spread']
print(f'{"":10s}'+''.join(f'{k:>10s}' for k in keys))
for e in ['level','growth','diffusion']:
    g=[r for r in rows if best(r)==e]
    if not g: continue
    print(f'{e:10s}'+''.join(f'{np.mean([r[k] for r in g]):10.2f}' for k in keys))
