"""Rule 17 sweep: exact-month scoring at both ends across every chronology, under
(smoothing) x (trough clause) x (US panel) variants.  Retrospective, current vintage."""
import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B, pandas as pd, numpy as np, warnings, itertools, json
warnings.filterwarnings('ignore')
SKIPSET={'exports','imports','car registrations','construction production','construction output',
         'capital goods production','intermediate goods production','consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
US_SIX={'industrial production (Federal Reserve)','payroll employment','household employment',
        'real income less transfers','real consumption','real manufacturing and trade sales'}
def panel(c, us_variant, skip_unemp):
    chs=bench.channels(c)
    out=[]
    for nm,s in chs:
        if nm in SKIPSET: continue
        if skip_unemp and nm=='unemployment': continue
        if c=='United States' and us_variant=='six' and nm not in US_SIX and nm!='unemployment': continue
        out.append((nm,s))
    return out or chs
def score(smooth_m, clause, us_variant, skip_unemp, band_t=0.12, band_p=0.01):
    B.TROUGH_CLAUSE=clause
    per={}
    ep=[];et=[];qp=[];qt=[]
    for c in bench.ALL:
        cfg=bench.PANELS[c]; chs=panel(c,us_variant,skip_unemp)
        cp=[];ct=[]
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
                e1=bench.md(r['peak'],pkm) if r['peak'] is not None else None
                e2=bench.md(r['trough'],trm) if r['trough'] is not None else None
                if e1 is not None: ep.append(e1)
                if e2 is not None: et.append(e2)
            else:
                a,e1=bench.hit(r['peak'],pk_off,'Q'); b_,e2=bench.hit(r['trough'],tr_off,'Q')
                if e1 is not None: qp.append(e1)
                if e2 is not None: qt.append(e2)
            cp.append(e1); ct.append(e2)
        per[c]=(cp,ct)
    f=lambda v,k: sum(abs(x)<=k for x in v)
    return dict(n=len(ep),p_exact=f(ep,0),p_w1=f(ep,1),p_w3=f(ep,3),p_bias=float(np.mean(ep)),
        t_exact=f(et,0),t_w1=f(et,1),t_w3=f(et,3),t_bias=float(np.mean(et)),
        qn=len(qp),qp_exact=f(qp,0),qt_exact=f(qt,0),per=per)
if __name__=='__main__':
    B.TROUGH_CLAUSE='later'
    rows=[]
    for sm,clause,usv,su in itertools.product((1,2,3),('later','dpeak'),('all','six'),(False,True)):
        s=score(sm,clause,usv,su)
        tag=f'smooth {sm} | {clause:5s} | US {usv:3s} | {"no-unemp" if su else "unemp   "}'
        print(f'{tag} || peaks {s["p_exact"]:>2d}/{s["p_w1"]:>2d}/{s["p_w3"]:>2d} of {s["n"]} bias {s["p_bias"]:+.2f} | troughs {s["t_exact"]:>2d}/{s["t_w1"]:>2d}/{s["t_w3"]:>2d} bias {s["t_bias"]:+.2f} | Q {s["qp_exact"]}/{s["qt_exact"]} of {s["qn"]}', flush=True)
        us=s['per']['United States']; print('    US peaks',us[0],'troughs',us[1], flush=True)
        rows.append((tag,{k:v for k,v in s.items() if k!='per'},{c:v for c,v in s['per'].items()}))
    json.dump(rows,open('/home/claude/lab/rule17_sweep.json','w'),default=str)
