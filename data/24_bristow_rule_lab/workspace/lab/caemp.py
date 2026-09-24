"""C.D. Howe, verbatim: "...refined with either monthly GDP post-1961 or industrial
production prior to 1961, along with monthly employment."  Test employment alongside."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_orig=bench.dating_series
MODE=['base']

def ds(country,w0,trm):
    if country!='Canada' or MODE[0]=='base': return _orig(country,w0,trm)
    ch=dict(bench.channels(country))
    gdp=ch.get('monthly GDP'); ip=ch.get('industrial production'); emp=ch.get('employment')
    def ok(s): return s is not None and s.index.min()<=w0 and s.index.max()>=trm
    core=None; nm=None
    if ok(gdp): core,nm=gdp,'monthly GDP'
    elif ok(ip): core,nm=ip,'industrial production'
    if core is None: return None
    if MODE[0]=='emp' and ok(emp): return (nm+'+employment',[core,emp],3,12)
    return (nm,core,3,12)

bench.dating_series=ds
def run(tag):
    bench._DEV.clear()
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    ca=score([r for r in tot if r['country']=='Canada'],'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]
    et=[abs(r['et']) for r in tot if r['et'] is not None]
    print(f'{tag:10s} peak {s["hp"]}/{s["n"]} trough {s["ht"]}/{s["n"]}  mean|e| {np.mean(ep):.2f}/{np.mean(et):.2f}'
          f'  w2 {sum(1 for x in ep if x<=2)},{sum(1 for x in et if x<=2)}'
          f'   CANADA {ca["hp"]}/{ca["n"]},{ca["ht"]}/{ca["n"]} MAD {ca["mp"]:.1f}/{ca["mt"]:.1f}')
    return tot
for M in ('base','core','emp'):
    MODE[0]=M; tot=run(M)
MODE[0]='emp'; tot=run('emp again')
for r in tot:
    if r['country']=='Canada':
        print(f"   {r['peak_off']}/{r['tr_off']}  ep={r['ep']} et={r['et']}  {r['verdict']}")
