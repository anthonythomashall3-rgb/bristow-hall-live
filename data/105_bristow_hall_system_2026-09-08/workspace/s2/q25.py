# q25.py - the search week in the sudden stop, frozen 1948-2026 at v3.26's walk-end lines (walk47 objects): the record
# with K on the earlier of the claims week and the search week. Expected: 2020 opens 16 March 2020; nothing else moves.
# Run: PYTHONPATH=. python3 s2/q25.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk50.py','1962','2026','w50']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk50.py').read().split(_MARK)[0])
pw=pickle.load(open('cache/w46_carry.pkl','rb'))
print('search-week proposals (day, month):',[(a.date().isoformat(),b.strftime('%Y-%m')) for a,b in leg_K_search(pw['kc'][0],pw['kc'][1])])
print('K on both (day, month):',[(a.date().isoformat(),b.strftime('%Y-%m')) for a,b in leg_K_x(ICfp.dropna(),pw['kc'][0],pw['kc'][1])])
print('March 2020, the search week over its base as known each morning:',{d.strftime('%m-%d'):round(float(v)) for d,v in GT_REL[(GT_REL.index>='2020-03-09')&(GT_REL.index<='2020-03-20')].items()})
r,t=build_v(pw); op={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
print('frozen at v3.26 lines: peaks',len(r['lags_p']),'/13, other',r['other'],'lags',[r['lags_p'][i] for i in sorted(r['lags_p'])]); print('opens:',op)
print('troughs',len(r['lags_t']),'/13')
