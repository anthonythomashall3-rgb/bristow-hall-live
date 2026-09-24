# asof_permits.py - BUILDING PERMITS AS THEY STOOD ON THE DAY, for the housing half of the pairs (10 September 2026).
# Sources, in order of preference for each day: the ALFRED vintage table (collection 27, PERMIT_all_vintages.csv, vintages
# from 17 August 1999); the Economic Indicators tables as printed (collection 107, ei_permits_as_printed.csv: the July to
# October 1990 issues and the October 1969 issue, each carrying the prior thirteen months as they stood at the end of the
# issue's month); and, where neither exists, the current file (cache/surveys/PERMIT.csv) - a declared bound, as for the
# vacancy before 2010. The object is walk46's housing half with permits in place of starts: the three-month mean of
# 100 x log(permits) below its twelve-month high, over the starts line (29); the rate half and the vacancy half are the
# as-of objects already loaded. Run after walk46's preamble: exec(open('s2/asof_permits.py').read()).
import csv as _csv, os as _os
import numpy as np, pandas as pd
_C107=_os.path.expanduser('~/Projects/Onset Detector Data/107_permits_first_prints_1990_2026-09-10')
_PV=load_vintages(_AL+'PERMIT_all_vintages.csv'); _PVD=sorted(_PV)
_PM_CUR=pd.read_csv('cache/surveys/PERMIT.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
_EI=pd.read_csv(_os.path.join(_C107,'ei_permits_as_printed.csv'),parse_dates=['as_of','month'])
# each issue takes effect on the release day of the newest month it prints (the Census release), not the issue's own date
_EI_ISSUES=[]
for iss,_gp in _EI.groupby('issue_ym'):   # (_gp, not g: g is the lab's Sahm-gap series and must not be rebound - found on the first live build, 10 September 2026)
    newest=_gp['month'].max(); eff=relH[newest] if newest in relH.index else pd.Timestamp(newest)+pd.DateOffset(months=1)+pd.Timedelta(days=17)
    _EI_ISSUES.append((pd.Timestamp(eff),_gp.set_index('month')['permits_authorized_saar_thous'].astype(float).sort_index()))
_EI_ISSUES.sort(key=lambda x:x[0])
def permits_asof(d):
    """the permits series as it stood on day d"""
    d=pd.Timestamp(d); vd=[v for v in _PVD if v<=d]
    if vd: return _PV[vd[-1]]
    s=_PM_CUR.copy()
    eff=[(e,t) for e,t in _EI_ISSUES if e<=d]
    if eff:
        e,t=eff[-1]
        if (d-e).days<=45:                      # inside the window the issue covers; the next issue takes over at its own release day
            s.loc[t.index]=t.values; s=s[s.index<=t.index.max()]
    return s
PERM_ASOF={}; PERM_PUB={}; PERM_SRC={}
for m in _PM_CUR.index:
    if m<pd.Timestamp('1961-01-01'): continue
    d=relH[m] if m in relH.index else pd.Timestamp(m)+pd.DateOffset(months=1)+pd.Timedelta(days=17)
    s=permits_asof(d); L=np.log(s.dropna())*100
    hh=(L.rolling(12).max()-L.rolling(3).mean())/BASE15['starts']
    if m in hh.index and not np.isnan(hh[m]):
        PERM_ASOF[m]=float(hh[m]); PERM_PUB[m]=pd.Timestamp(d)
        PERM_SRC[m]=('alfred' if [v for v in _PVD if v<=d] else ('economic-indicators' if any(e<=d and (d-e).days<=45 for e,_ in _EI_ISSUES) else 'current-file'))
PERM_ASOF=pd.Series(PERM_ASOF).sort_index(); PERM_PUB=pd.Series(PERM_PUB).sort_index()
def _mkpair_two(hh,hpub,other,opub,name,hline=1.0,other_from='1960-01-01'):
    ev=[(pd.Timestamp(hpub[m]),'D',m) for m in hh.index if m in hpub.index]+[(pd.Timestamp(opub[m]),'U',m) for m in other.index if m in opub.index and m>=pd.Timestamp(other_from)]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(hh.get(lastD,np.nan),other.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastU); mx[key]=max(mx.get(key,-9),v)
        if v>=hline-EPS and key not in fires: fires[key]=d
    G_=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name=name,gap=G_,line=hline,pubs=PB,mx=pd.Series(mx).sort_index())
def mkpair_perm_asof(hline=1.0): return _mkpair_two(PERM_ASOF,PERM_PUB,rate_asof,rate_pub,'pairPERM',hline)
def mkpair_sv_perm_asof(G_,pubsV,vl): return _mkpair_two(PERM_ASOF,PERM_PUB,(G_/vl),pubsV,'pairSVPERM',1.0)
