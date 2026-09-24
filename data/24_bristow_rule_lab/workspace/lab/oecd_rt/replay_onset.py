"""The onset clauses of lab/speed/onset_channels.py on first prints: the OECD revisions
database walked edition by edition (February 1999 on), the panel rebuilt from each edition
alone, and one call per episode taken on the latest month in hand.

Clauses, each on the panel's log levels x100 smoothed three months, exactly as in
onset_channels.clause: the shipped statistic (median drawdown >= 2), the in-sample winner of
the k-of-n family (three channels each >= 3 below their trailing maximum, two months), and
the self-normalising composite (median standardised six-month change <= -0.5 sigma, two
months; each channel standardised on its own trailing ten years, which the editions carry).
The machine is the simple one of onset_channels: quiet -> call when the clause's latest value
is on -> silent until it has been off for six editions.  Publication month = edition month.
Scored as there: a peak's call is the earliest whose data month lies in [peak-3, min(peak+18,
trough+3)]; later calls inside the contraction are repeats; calls in expansions are other
calls.  The quarterly committees' quarters are read as mid-months, as replay_oecd does.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed'); sys.path.insert(0,'/home/claude/lab/oecd_rt')
import numpy as np, pandas as pd
import replay_oecd as R
from onset_channels import clause, logs, score, tally
CLAUSES=[('the shipped clause: median drawdown >= 2','median',dict(band=2.0)),
         ('three channels each >= 3 below, two months','kofn',dict(band=3.0,k=3,c=2)),
         ('median standardised six-month change <= -0.5, two months','zmed',dict(h=6,z0=0.5,c=2)),
         ('the same, three months','zmed',dict(h=6,z0=0.5,c=3))]
def walk_onset(area, names, kind, kw, rearm=6):
    E=R.editions(area,names); out=[]; state='quiet'; off=0
    for e in E:
        chs=R.panel(area,e,names)
        chs=[(nm,s[s>0].dropna()) for nm,s in chs if len(s)>=40]
        if not chs: continue
        X=logs(chs,3); cond=clause(X,kind,**kw).dropna()
        if not len(cond): continue
        v=bool(cond.iloc[-1]); latest=cond.index[-1]
        if state=='quiet':
            if v: out.append((R.ed_ts(e),latest)); state='called'; off=0
        else:
            off=off+1 if not v else 0
            if off>=rearm: state='quiet'
    return out
if __name__=='__main__':
    names=list(R.CHAN)
    pooled={}
    for label,kind,kw in CLAUSES:
        print(f'\n=== {label}')
        agg=dict(n=0,hits=0,other=0,inMonth=0,w3=0,w6=0,lags=[])
        for area,chron in R.CHRON.items():
            P=[(R.ts(a),R.ts(b)) for a,b in chron]
            calls=walk_onset(area,names,kind,kw)
            first=pd.Timestamp('1999-02-01')
            Pr=[p for p in P if p[0]>=first]
            got,other,rep=score(calls,Pr); t=tally(got,other,Pr,first)
            for f in ('n','hits','other','inMonth','w3','w6'): agg[f]+=t[f]
            agg['lags']+=t['lags']
            print(f"  {area:4s} hits {t['hits']}/{t['n']} other {t['other']:2d} lag<=3 {t['w3']} <=6 {t['w6']} lags {t['lags']}  calls {[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in calls]}")
        print(f"  ALL  hits {agg['hits']}/{agg['n']} other {agg['other']} lag<=1 {agg['inMonth']} <=3 {agg['w3']} <=6 {agg['w6']} median {np.median(agg['lags']) if agg['lags'] else float('nan'):.1f}")
        pooled[label]=agg
    print('\n=== pooled, eleven economies, first prints 1999 on')
    for label,agg in pooled.items():
        print(f"  {label:60s} hits {agg['hits']}/{agg['n']} other {agg['other']:2d} lag<=3 {agg['w3']} <=6 {agg['w6']} median {np.median(agg['lags']):.1f}")
