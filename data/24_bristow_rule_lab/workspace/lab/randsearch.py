"""A joint random search over the whole parameter space.

Every sweep so far has moved one or two parameters at a time, which finds a local
optimum but cannot rule out a coordinated move that escapes it.  This draws whole
configurations at random - smoothing, lookback, both bands, the peak window, the
depth threshold, where in the plateau each end sits, the order statistic, and the
three diffusion parameters - and scores them on Anthony's criterion.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import random, math, importlib
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
random.seed(20260831)
src=open('/home/claude/lab/bench.py').read()
orig_med=bench.med
def setq(q0):
    def med2(dates,q=None):
        ds=sorted(d for d in dates if d is not None)
        if not ds: return None
        if len(ds)==1: return ds[0]
        qq=q0 if q is None else q
        i=int(math.ceil(qq*(len(ds)-1)-1e-9))
        return ds[min(max(i,0),len(ds)-1)]
    return med2
SHIP=dict(n=3,L=12,band_t=0.12,band_p=0.01,peak_cap=18,min_depth=5.0,lam=500000.)
def evaluate(cfg,pt,pp,q0,dline,drun,dband):
    bench.PLATEAU_T=pt; bench.PLATEAU_P=pp; bench.med=setq(q0)
    old=bench.date_diffusion_panel
    def dd(chs,w0,w1,line=45.0,run=1,band=0.30,n_di=5,n_band=3,L=12,run_p=4):
        return old(chs,w0,w1,dline,run,dband,n_di,n_band,L,drun)
    bench.date_diffusion_panel=dd
    try:
        tot=[]
        for c in ALL: tot+=run_country_concept(c,**cfg)
        a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
        return (a+b, s['hp']+s['ht'], a, b, s['hp'], s['ht'], ma_, mb)
    finally:
        bench.date_diffusion_panel=old; bench.med=orig_med
        bench.PLATEAU_T='mid'; bench.PLATEAU_P='mid'
base=evaluate(SHIP,'mid','mid',0.5,45.,4,0.30)
print(f'shipped   within2 {base[2]}+{base[3]}={base[0]}  hits {base[4]}/{base[5]}  MAE {base[6]:.2f}/{base[7]:.2f}',flush=True)
best=(base,dict(SHIP),'mid','mid',0.5,45.,4,0.30)
seen=0
for it in range(400):
    cfg=dict(n=random.choice([2,3,4]),L=random.choice([6,9,12,15,18,24]),
             band_t=random.choice([0.0,0.01,0.03,0.06,0.09,0.12,0.16,0.20,0.30]),
             band_p=random.choice([0.0,0.005,0.01,0.02,0.04,0.08,0.12]),
             peak_cap=random.choice([6,9,12,18,24,36]),
             min_depth=random.choice([2.0,3.0,5.0,8.0,12.0]),lam=500000.)
    pt=random.choice(['mid','last']); pp=random.choice(['mid','last'])
    q0=random.choice([0.4,0.5,0.6]); dline=random.choice([35.,40.,45.,50.,55.])
    drun=random.choice([2,3,4,5,6]); dband=random.choice([0.10,0.20,0.30,0.45,0.60])
    try: o=evaluate(cfg,pt,pp,q0,dline,drun,dband)
    except Exception: continue
    seen+=1
    if (o[0],o[1])>(best[0][0],best[0][1]):
        best=(o,cfg,pt,pp,q0,dline,drun,dband)
        print(f'  new best at draw {it}: within2 {o[2]}+{o[3]}={o[0]}  hits {o[4]}/{o[5]}  MAE {o[6]:.2f}/{o[7]:.2f}',flush=True)
        print(f'     {cfg} plateau {pt}/{pp} q={q0} di line={dline} run={drun} band={dband}',flush=True)
print(f'\nevaluated {seen} random configurations')
o,cfg,pt,pp,q0,dline,drun,dband=best
print(f'BEST within2 {o[2]}+{o[3]}={o[0]}  hits {o[4]}/{o[5]}  MAE {o[6]:.2f}/{o[7]:.2f}')
print(f'  {cfg} plateau {pt}/{pp} q={q0} di line={dline} run={drun} band={dband}')
