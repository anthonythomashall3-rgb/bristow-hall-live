# q21.py - the two candidate clauses under the walk: (a) walk48 (the co-signer clause) frozen at its own walk-end lines
# (vl 0.25, hback 12, chosen at the 2026 cut); (b) the anatomy of walk49's June 2025 false alarm (the survey-week line
# moved to 0.3 at the 1992 cut) and how close the same configuration came under walk48's lines (the survey-week rate's
# largest rise in 2025 against the 0.4 line; the co-signer; the vacancy). Run: PYTHONPATH=. python3 s2/q21.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk48.py','1962','2026','w48']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
exec(open('walk48.py').read().split(_MARK)[0])
p48=pickle.load(open('cache/w48_carry.pkl','rb')); pg48=pickle.load(open('cache/w48_prog.pkl','rb'))
p46=pickle.load(open('cache/w46_carry.pkl','rb'))
def show(nm,p):
    r,t=build_v(p); op={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
    print(f"{nm}: peaks {len(r['lags_p'])}/13 FALSE {r['other']} lags {[r['lags_p'][i] for i in sorted(r['lags_p'])]} | 2001 {op.get(9)} 2024 {op.get(12)} | troughs {len(r['lags_t'])}/13")
show('walk48 frozen at its walk-end lines (vl 0.25, hback 12)',p48)
q=dict(p48); q['vl']=0.2; q['hback']=9; show('walk48 rule frozen at v3.26 lines (vl 0.2, hback 9)',q)
q=dict(p48); q['vl']=0.2; q['hback']=9; q['wline']=0.3; show('walk48 rule at v3.26 lines with the survey-week line 0.3',q)
q=dict(p48); q['wline']=0.3; show('walk48 rule at its walk-end lines with the survey-week line 0.3',q)
# the survey-week rate in 2025 against its 52-week low, in tenths; the co-signer by release day; the vacancy gap
gW=_tenths(SI-SI.rolling(52,min_periods=52).min().shift(1)).dropna()
w25=gW[(gW.index>='2025-01-01')&(gW.index<='2026-09-01')]
print('survey-week rate above its 52-week low, 2025-26 (tenths), max',float(w25.max()),'at',w25.idxmax().date(),'| months at 0.3:',[m.strftime('%Y-%m') for m,v in w25.items() if v>=0.3-EPS])
cs=gpub_asof[(gpub_asof.index>='2025-01-01')&(gpub_asof.index<='2026-09-01')]
print('household co-signer (3-mo avg above 12-mo low), by release day 2025-26:',{d.date().isoformat():round(float(v),3) for d,v in cs.items()})
G=vgap2_asof(p48['vk'],p48['vb']); g25=G[(G.index>='2024-10-01')&(G.index<='2026-08-01')]
print('vacancy gap (4-mo mean below its 4-mo high), 2024-10..2026:',{m.strftime('%Y-%m'):round(float(v),3) for m,v in g25.items()})
# walk49's June 2025 call: which proposal, which confirmer, at the 2025 cut's lines (wline 0.3)
pg49=pickle.load(open('cache/w49_prog.pkl','rb')); c25=pg49['chosen'][pd.Timestamp('2025-01-01')]
print('walk49 lines at the 2025 cut:',{k:c25[k] for k in ('wline','wline2','low','vl','hback','hline')})
print('W proposals 2025 at wline 0.3 (day, month):',[(a.date().isoformat(),b.strftime('%Y-%m')) for a,b in leg_sv_x(0.3,rearm='zero') if a.year==2025])
print('co-signed on those days:',[(a.date().isoformat(),bool(cosign_asof(a))) for a,b in leg_sv_x(0.3,rearm='zero') if a.year==2025])
