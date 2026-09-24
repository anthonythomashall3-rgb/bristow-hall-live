"""Rule 17 objective: EXACT month.  How do the shipped settings do, and does the
trailing smoothing - the source of the US trough late bias - cost exact-month hits
across the nine chronologies?"""
import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
CH={c:[(nm,s) for nm,s in bench.channels(c) if nm not in bench.SKIP] for c in bench.ALL}
def score(smooth_m, band_t=0.12, band_p=0.01):
    ep=[];et=[]; qp=[];qt=[]
    for c in bench.ALL:
        cfg=bench.PANELS[c]; chs=CH[c]
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=bench.ep3(_e,cfg['freq'])
            pkm=bench.ts(pk_off) if freq=='M' else bench.q2m(pk_off)
            trm=bench.ts(tr_off) if freq=='M' else bench.q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
            if not use: use=chs
            if freq=='Q': use=[(nm,B.to_quarter(x)) for nm,x in use]
            vol=bench.quantity(c,use) or use
            r=B.date_turning_points(use,w0,w1,volume_channels=vol,concept=bench.CONCEPT[c],
                lam=500000.0,band_trough=band_t,band_peak=band_p,peak_cap=18,
                smooth=(1 if freq=='Q' else smooth_m),lookback=(4 if freq=='Q' else 12),
                dating_series=bench.dating_series(c,w0,trm))
            if freq=='M':
                if r['peak'] is not None: ep.append(bench.md(r['peak'],pkm))
                if r['trough'] is not None: et.append(bench.md(r['trough'],trm))
            else:
                a,e1=bench.hit(r['peak'],pk_off,'Q'); b,e2=bench.hit(r['trough'],tr_off,'Q')
                if e1 is not None: qp.append(e1)
                if e2 is not None: qt.append(e2)
    f=lambda v,k: sum(abs(x)<=k for x in v)
    return dict(n=len(ep),
        p_exact=f(ep,0),p_w1=f(ep,1),p_w2=f(ep,2),p_w3=f(ep,3),p_bias=np.mean(ep),
        t_exact=f(et,0),t_w1=f(et,1),t_w2=f(et,2),t_w3=f(et,3),t_bias=np.mean(et),
        qn=len(qp),qp_exact=f(qp,0),qp_w1=f(qp,1),qt_exact=f(qt,0),qt_w1=f(qt,1))
print(f'{"smooth":>6s} | {"MONTHLY peaks: exact w1 w2 w3 bias":>38s} | {"troughs: exact w1 w2 w3 bias":>32s} | quarterly p/t exact')
for sm in (1,2,3):
    s=score(sm)
    print(f'{sm:>6d} | {s["p_exact"]:>5d} {s["p_w1"]:>3d} {s["p_w2"]:>3d} {s["p_w3"]:>3d} {s["p_bias"]:+.2f} of {s["n"]:>2d}      | '
          f'{s["t_exact"]:>5d} {s["t_w1"]:>3d} {s["t_w2"]:>3d} {s["t_w3"]:>3d} {s["t_bias"]:+.2f}       | {s["qp_exact"]}/{s["qn"]}  {s["qt_exact"]}/{s["qn"]}')
