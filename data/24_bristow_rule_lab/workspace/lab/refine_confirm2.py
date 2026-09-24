import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
def setting(t,p):
    B.REFINE_TROUGH=t; B.REFINE_PEAK=p; B.REFINE_SMOOTH=None; B.REFINE_SMOOTH_T=1; B.REFINE_SMOOTH_P=2
    bench.REFINE_T=t; bench.REFINE_P=p; bench.REFINE_SMOOTH_T=1; bench.REFINE_SMOOTH_P=2
def run(label):
    ep=[];et=[];q=[0,0];diff=0
    for c in ALL:
        r=run_country_concept(c,**K)
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        i=0
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
            if not use: use=chs
            if freq=='Q': use=[(nm,B.to_quarter(x)) for nm,x in use]
            vol=quantity(c,use) or use
            t=B.date_turning_points(use,w0,w1,volume_channels=vol,concept=CONCEPT[c],
                                    lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,
                                    smooth=(1 if freq=='Q' else 3),lookback=(4 if freq=='Q' else 12),
                                    dating_series=dating_series(c,w0,trm))
            b=r[i]; i+=1
            f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
            if f(t['peak'])!=f(b['pk']) or f(t['trough'])!=f(b['tr']):
                diff+=1; print(f"  DIFF {c} {pk_off}: bench {f(b['pk'])}/{f(b['tr'])} tool {f(t['peak'])}/{f(t['trough'])}")
            if freq=='Q':
                q[1]+=2
                if b['ep'] is not None and abs(b['ep'])<=1: q[0]+=1
                if b['et'] is not None and abs(b['et'])<=1: q[0]+=1
            else:
                ep.append(b['ep']); et.append(b['et'])
    def cnt(e):
        e=[x for x in e if x is not None]
        return f"{sum(abs(x)==0 for x in e)}/{sum(abs(x)<=1 for x in e)}/{sum(abs(x)<=3 for x in e)} bias {sum(e)/len(e):+.2f} mae {sum(abs(x) for x in e)/len(e):.2f} n={len(e)}"
    print(f"{label:34s}|| peaks {cnt(ep)} | troughs {cnt(et)} | Q {q[0]} of {q[1]} | tool/bench diffs {diff}")
run('shipped defaults now: T(3,1) rs1 + P(1,0) rs2')
