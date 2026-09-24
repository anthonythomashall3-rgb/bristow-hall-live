# q26.py - the either pair (starts or permits in the housing x rate pair) with the search week, frozen 1948-2026 at v3.26's
# walk-end lines (walk51's objects). Expected: 1990 opens 26 July 1990 (-5), 2020 opens 16 March 2020, all else v3.26's.
# Run: PYTHONPATH=. python3 s2/q26.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk51.py','1962','2026','w51']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk51.py').read().split(_MARK)[0])
pw=pickle.load(open('cache/w46_carry.pkl','rb'))
E=mkpair_either_asof(pw['hline']); A=mkpair_asof(pw['hline']); P=mkpair_perm_asof(pw['hline'])
for y in (1969,1990,2023,2025):
    print(y,'either at line months:',[m.strftime('%Y-%m') for m,v in E['gap'].items() if m.year==y and v>=1.0-EPS],'| starts:',[m.strftime('%Y-%m') for m,v in A['gap'].items() if m.year==y and v>=1.0-EPS],'| permits:',[m.strftime('%Y-%m') for m,v in P['gap'].items() if m.year==y and v>=1.0-EPS])
r,t=build_v(pw); op={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
print('frozen at v3.26 lines: peaks',len(r['lags_p']),'/13, other',r['other'],'lags',[r['lags_p'][i] for i in sorted(r['lags_p'])]); print('opens:',op); print('troughs',len(r['lags_t']),'/13')
q=dict(pw); q['wline']=0.3; r2,t2=build_v(q); print('at survey-week line 0.3: peaks',len(r2['lags_p']),'other',r2['other'],'1990',r2['opens'].get(8,{}).get('published'))
