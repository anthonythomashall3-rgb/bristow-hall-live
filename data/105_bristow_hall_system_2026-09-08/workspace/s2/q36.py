# q36.py - WHY THE DAILY LINE'S READING IS UNDER 1.00 ON SOME OPEN DAYS (10 September 2026, evening). The audit's new check
# (the line crosses 1.00 on every walked open day by the diary's own branch) fails on 1969, 1973, 1981, 1990, 2001: the
# line is held at 1.00 there with a reading under it, or crosses by another branch. This script runs the builder's
# objects (bhs_build.py up to the readings table; nothing is written) and prints, for each walked open day, every
# branch's proposer and confirmer readings as the builder computes them, so the gap between the walk's call and the
# page's arithmetic can be seen object by object. Run: PYTHONPATH=. python3 s2/q36.py
import sys,os,io,contextlib
sys.path.insert(0,os.getcwd())
src=open('bhs_build.py').read().split("logp=os.path.join(LIVE,'live','LIVE_LOG_v321.tsv')")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
import numpy as np, pandas as pd
def parts(P,d):
    out={}
    cvals={c:_asof(CONF[c],d,6) for c in CONF}
    for nm,confs in (('U',CONF1),('L',CONF2),('I',CONF1),('W',CONF2),('V',CONF2),('B',CONF2)):
        if nm not in P: continue
        pv=_asof(P[nm],d,4); out[nm]=(None if np.isnan(pv) else round(pv,3),{c:(None if np.isnan(cvals[c]) else round(cvals[c],3)) for c in confs})
    if 'K' in P: out['K']=_asof(P['K'],d,0)
    if 'KS' in P: out['KS']=_asof(P['KS'],d,0)
    pv=_asof(P['X'],d,0); out['X']=None if np.isnan(pv) else round(pv,3)
    return out
for e in epis:
    d=pd.Timestamp(e['open_pub']); r,who=_reading(PROP_R,d)
    print(f"\n{e['open_pub']} diary leg {e['open_leg']} | builder reading {r:.3f} by {who}")
    for k,v in parts(PROP_R,d).items(): print('   ',k,v)
    # the walk's own objects on that day, for the diary's leg: the proposer series and the confirmers' as-of gaps
    m=pd.Timestamp(e['open_month']+'-01')
    if e['open_leg'] in ('L','U'):
        print('    insured-rate rise (tenths) last 5 weeks:',[(t.date().isoformat(),round(float(v),3)) for t,v in (RAW[e['open_leg']]*(p['low'] if e['open_leg']=='L' else p['u45'])).dropna().items() if d-pd.Timedelta(days=40)<=t<=d][-5:])
    if e['open_leg'] in ('W','V'):
        print('    survey-week rise last 4 months:',[(t.date().isoformat(),round(float(v),3)) for t,v in (RAW[e['open_leg']]*(p['wline'] if e['open_leg']=='W' else p['wline2'])).dropna().items() if d-pd.DateOffset(months=5)<=t<=d])
    hp=Hc['gap']; print('    housing x rate pair gap (either) by month, last 6 known:',[(t.strftime('%Y-%m'),round(float(v),3)) for t,v in hp.dropna().items() if m-pd.DateOffset(months=7)<=t<=m])
    print('    pair as published (CONF pair) entries in last 8 months:',[(str(pu)[:10],str(t)[:7],round(float(v),3)) for pu,t,v in zip(CONF['pair']['pub'],CONF['pair']['t'],CONF['pair']['v']) if pd.Timestamp(pu)<=d and pd.Timestamp(t)>=m-pd.DateOffset(months=8)])
    print('    spread ratio last 8 weeks:',[(t.date().isoformat(),round(float(v),3)) for t,v in cS.dropna().items() if d-pd.Timedelta(days=60)<=t<=d])
    print('    starts x vacancy pair last 6 months:',[(t.strftime('%Y-%m'),round(float(v),3)) for t,v in cSV.dropna().items() if m-pd.DateOffset(months=7)<=t<=m])
