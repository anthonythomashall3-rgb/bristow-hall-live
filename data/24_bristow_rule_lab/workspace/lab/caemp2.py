"""Peak from the output series alone; trough from output and employment together.
C.D. Howe 1960: "Industrial production peaked in March 1960, which points to this month
as the peak"; "The cyclical trough in both output and jobs was in March 1961"."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_rcc=bench.run_country_concept
_orig=bench.dating_series
MODE=['base']

def ds(country,w0,trm):
    if country!='Canada': return _orig(country,w0,trm)
    ch=dict(bench.channels(country))
    gdp=ch.get('monthly GDP'); ip=ch.get('industrial production'); emp=ch.get('employment')
    def ok(s): return s is not None and s.index.min()<=w0 and s.index.max()>=trm
    core=None;nm=None
    if ok(gdp): core,nm=gdp,'monthly GDP'
    elif ok(ip): core,nm=ip,'industrial production'
    if core is None: return None
    if MODE[0]=='base': return (nm,core,3,12)
    tro=[core,emp] if ok(emp) else [core]
    return (nm,dict(peak=[core],trough=tro,q=MODE[0]),3,12)

# patched dating branch inside run_country_concept
def run_country_concept2(country, lead=12, tail=12, concept=None, **kw):
    cfg=bench.PANELS[country]; chs=[(nm,s) for nm,s in bench.channels(country) if nm not in bench.SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=bench.ep3(_e,cfg['freq'])
        pkm=bench.ts(pk_off) if freq=='M' else bench.q2m(pk_off)
        trm=bench.ts(tr_off) if freq=='M' else bench.q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        d=ds(country,w0,trm)
        if country=='Canada' and d is not None and isinstance(d[1],dict):
            _nm,spec,_n,_L=d; q=spec['q']
            tr=bench.med([bench.ch_trough(x,w0,w1,kw.get('band_t',.12),_n,_L,abstain=False)
                          for x in spec['trough']], q=(1.0 if q=='late' else 0.0))
            pk=bench.med([bench.ch_peak(x,w0,tr if tr is not None else w1,kw.get('band_p',.01),_n,abstain=False)
                          for x in spec['peak']])
            a,ep=bench.hit(pk,pk_off,freq); b,et=bench.hit(tr,tr_off,freq)
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=2,pk=pk,tr=tr,
                             ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None,verdict=_nm)); continue
        rows+= _rcc(country,lead,tail,concept,**kw)[len(rows):len(rows)+1] if False else []
        # fall back: single-episode via original
        rows+=[r for r in _rcc(country,lead,tail,concept,**kw) if r['peak_off']==pk_off and r['tr_off']==tr_off]
    return rows

def run(tag):
    bench._DEV.clear()
    tot=[]
    for c in ALL:
        tot+= (run_country_concept2(c,**K) if c=='Canada' else _rcc(c,**K))
    s=score(tot,'',show=False)
    ca=score([r for r in tot if r['country']=='Canada'],'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]
    et=[abs(r['et']) for r in tot if r['et'] is not None]
    print(f'{tag:8s} peak {s["hp"]}/{s["n"]} trough {s["ht"]}/{s["n"]}  mean|e| {np.mean(ep):.2f}/{np.mean(et):.2f}'
          f'  w2 {sum(1 for x in ep if x<=2)},{sum(1 for x in et if x<=2)}'
          f'   CANADA {ca["hp"]}/{ca["n"]},{ca["ht"]}/{ca["n"]} MAD {ca["mp"]:.1f}/{ca["mt"]:.1f}')
    return tot
for M in ('base','late','early'):
    MODE[0]=M; tot=run(M)
    if M!='base':
        for r in tot:
            if r['country']=='Canada': print(f"     {r['peak_off']}/{r['tr_off']} ep={r['ep']} et={r['et']}")
