"""bhs_build.py v17 -> v18 (the audit of 8 September 2026): the walk is chosen by cache/bhs_version.json
({"walk": "walk39.py", "var": "w39", "version": "v3.22"}); the daily series carries every object on its actual
release day (the release-day functions of walk39: rel_ic, rel_iu, rel_state, rel_h15); the Sahm comparator on the page
is FRED's SAHMREALTIME (cache/SAHMREALTIME.csv); the 2020-05-05 override is gone (walk38 and later carry the true day)."""
import sys
p=sys.argv[1] if len(sys.argv)>1 else 'bhs_build.py'
t=open(p,encoding='utf-8').read()
def rep(old,new,n=1):
    global t
    assert t.count(old)==n, (t.count(old), old[:90])
    t=t.replace(old,new)
rep('''import sys, io, contextlib, os, json, datetime, pickle
sys.argv=['x','2011','2012','wbhs']
src=open('walk38.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
import numpy as np, pandas as pd
CFG=pickle.load(open('cache/w38_carry.pkl','rb'))          # the configuration the v3.21 walk ended on (walk38 = walk37 re-dated; identical lines)''',
'''import sys, io, contextlib, os, json, datetime, pickle
# THE WALK THE SITE STANDS ON is named in cache/bhs_version.json: {"walk": "walk39.py", "var": "w39", "version": "v3.22"}.
# Walks from walk39 on carry the walk loop behind the marker "# ---- the walk itself"; walk38 and before split at the
# "Y0,Y1,VAR=" line. The preamble defines the objects, the release-day functions and build_v.
VERS=json.load(open('cache/bhs_version.json')) if os.path.exists('cache/bhs_version.json') else dict(walk='walk38.py',var='w38',version='v3.21')
WALK,VAR,VERSION=VERS['walk'],VERS['var'],VERS['version']
sys.argv=['x','2011','2012','wbhs']
_wsrc=open(WALK).read()
src=_wsrc.split("# ---- the walk itself")[0] if "# ---- the walk itself" in _wsrc else _wsrc.split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
import numpy as np, pandas as pd
CFG=pickle.load(open(f'cache/{VAR}_carry.pkl','rb'))          # the configuration the walk ended on''')
rep('''_wk12=lambda t:t+pd.Timedelta(days=12); _wk5=lambda t:t+pd.Timedelta(days=5); _wk19=lambda t:t+pd.Timedelta(days=19)
_sv=lambda t:(SW[t]+pd.Timedelta(days=12)) if t in SW.index else None
_pu=lambda m:_rel(_RELU,m,4); _pj=lambda m:_rel(_RELJ,m,29); _sp=lambda t:t     # the H.15 week is complete on its Friday (4:15 PM ET)''',
'''# THE RELEASE DAYS (audit of 8 September 2026). Walks from walk39 define them: rel_ic (the initial-claims week's
# release), rel_iu (the insured week's, a release later), rel_state (two releases later), rel_h15 (the first business
# day after the H.15 week's Friday, when the Federal Reserve posts Friday's rates). Under an older walk the lab's
# conventions stand in (five, twelve and nineteen days; the Friday).
if 'rel_ic' in globals():
    _wk5=rel_ic; _wk12=rel_iu; _wk19=rel_state; _sp=rel_h15
    _sv=lambda t:(rel_iu(SW[t]) if t in SW.index else None)
else:
    _wk12=lambda t:t+pd.Timedelta(days=12); _wk5=lambda t:t+pd.Timedelta(days=5); _wk19=lambda t:t+pd.Timedelta(days=19)
    _sv=lambda t:(SW[t]+pd.Timedelta(days=12)) if t in SW.index else None
    _sp=lambda t:t
_pu=lambda m:_rel(_RELU,m,4); _pj=lambda m:_rel(_RELJ,m,29)''')
rep('''pg=pickle.load(open('cache/w38_prog.pkl','rb')); LOG=sorted(pg['log'],key=lambda z:z[0])''','''pg=pickle.load(open(f'cache/{VAR}_prog.pkl','rb')); LOG=sorted(pg['log'],key=lambda z:z[0])''')
rep('''for e in epis:                                   # the 2020 call: the diary's 5 May 2020 was the hours pair's approximate day
    if e['open_pub']=='2020-05-05':
        fz=[(a,b) for a,b in FROZEN if a.year==2020]
        if fz:
            a,b=fz[0]; e.update(open_pub=a.date().isoformat(),close_pub=(None if b.year==2100 else b.date().isoformat()),close_month=(None if b.year==2100 else b.strftime('%Y-%m')),corrected='the hours pair dated by the Employment Situation release day (was the fifth of the month)')
''','')
rep('''# dates the spread a day after its Friday, a conservative convention; the page carries the Friday, when the week's
# H.15 data exist.)''','''# from walk39 dates every object on its actual release day; the page carries the same days.)''')
rep('''SAHM=g.dropna(); SAHM=SAHM[SAHM.index>=SITE_START]''','''# THE SAHM COMPARATOR IS FRED'S OWN REAL-TIME SERIES (SAHMREALTIME, refreshed by bhs_update.py). Audit of 8 September
# 2026: the page had carried the rule's own Sahm object (the gap on first prints) under FRED's name; the two agree on
# every crossing of 0.50 inside a recession since 1960 but the rule's object also crosses in June 2003, FRED's does not.
_sf=pd.read_csv('cache/SAHMREALTIME.csv',index_col=0,parse_dates=True).iloc[:,0].dropna() if os.path.exists('cache/SAHMREALTIME.csv') else g.dropna()
SAHM=_sf[_sf.index>=SITE_START]''')
rep('''# ---- the Sahm rule in real time, for the same rows: the first month at or above 0.50 on first prints, on its release day ----
SAHM_CALLS=[]; _armed=True
for m,v in g.dropna().items():''','''# ---- the Sahm rule in real time, for the same rows: the first month at or above 0.50 in FRED's SAHMREALTIME, on its release day ----
SAHM_CALLS=[]; _armed=True
for m,v in _sf.items():''')
rep('''version='v3.21',''','''version=VERSION,walk=WALK,''')
rep('''(walk38: walk37 with the hours pair on the release calendar; identical lines at every cut) produced;''','''named in cache/bhs_version.json produced;''')
open(p,'w',encoding='utf-8').write(t); print('bhs_build.py patched to v18')
