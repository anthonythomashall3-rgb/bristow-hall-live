"""THE CLAIMS SUBSTITUTE (collection 329, 23 September 2026; the plan's Step 3b / risks register R1; Anthony's approved order).

When the Department's weekly claims release is stale (no advance week for more than the channel's limit, as in the shutdown
of 1 October - 12 November 2025, when the release stopped on 25 September and the ETA 539 state file kept being posted -
EPI, 15 October 2025), the national numbers the proposers read are rebuilt from the states' own file:

  initial claims, unadjusted, report week W   = the sum over the 53 jurisdictions of the 539 file's initial claims (c3; the
                                                panel of collection 37 stores them under the reflecting week W - 7 days)
  initial claims, seasonally adjusted         = unadjusted / the published factor for W (the Bureau's factors for the Department,
                                                collection 328; NSA = SA x factor), rounded to thousands as the release rounds
  continued claims (insured unemployment) SA  = the sum of continued weeks claimed (c8, reflecting week) / the continued-claims factor
  insured unemployment rate SA                = that, over the sum of covered employment (c18), in per cent, one decimal

Measured (322, corrected 23:3xZ): the state sum equals the release's unadjusted first print within 2 per cent in 799 of 861
weeks since 2010; the adjusted substitute misses the published figure by a median 0.36 per cent; the proposer's object (the
four-week mean over its 52-week low) by a median 0.24 point against a line of 40.

The rows carry kind='substitute' and are used only for weeks AFTER the last real release week; when the release resumes its own
first prints replace them (the substitute never enters the first-print history). The in-hand day of a substitute week is the day
the live run read the 539 file (today) for the newest weeks; in a drill on the past it is W + 12 days - a week after the release
day the week would have had - so that no drill is dated ahead of what the file could have shown.
"""
import os, sys, datetime
import pandas as pd, numpy as np
def _root():
    for c in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data'),
              os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..'))):
        if os.path.isdir(os.path.join(c,'105_bristow_hall_system_2026-09-08')): return c
    return os.path.expanduser('~/Projects/Onset Detector Data')
ROOT=_root()
PANEL=os.path.join(ROOT,'37_dol_eta5159_2026-09','panel','panel_539_weekly.csv')
N45=os.path.join(ROOT,'45_dol_first_prints_2026-09','national_first_prints.csv')
FACT=os.path.join(ROOT,'328_dol_claims_seasonal_factors_2026-09-22','out','dol_claims_seasonal_factors_2026_2027.csv')
JUR=53
def factors():
    """week ending -> (initial factor, continued factor): the Bureau's published table where held, else the release's own implied
    factor (SA/NSA first prints) for the same week; a future week with neither takes the implied factor of the week a year earlier"""
    f={}
    n=pd.read_csv(N45,parse_dates=['ic_week_ended','iu_week_ended'])
    for _,r in n.dropna(subset=['icsa','icnsa']).drop_duplicates('ic_week_ended',keep='first').iterrows():
        if r['icnsa']>0: f[pd.Timestamp(r['ic_week_ended'])]=[float(r['icnsa'])/float(r['icsa']),None,'release']
    for _,r in n.dropna(subset=['iusa','iunsa']).drop_duplicates('iu_week_ended',keep='first').iterrows():
        w=pd.Timestamp(r['iu_week_ended'])
        if r['iunsa']>0 and r['iusa']>0:
            f.setdefault(w,[None,None,'release'])[1]=float(r['iunsa'])/float(r['iusa'])
    if os.path.exists(FACT):
        t=pd.read_csv(FACT)
        for _,r in t.iterrows():
            w=pd.Timestamp(r['week_ending']); f[w]=[float(r['initial_claims_factor']),float(r['continued_claims_factor']),'published']
    return f
def _factor(f,w,k):
    x=f.get(w)
    if x and x[k] is not None: return x[k],x[2]
    y=f.get(w-pd.Timedelta(days=364))
    if y and y[k] is not None: return y[k],'year-earlier'
    return None,None
def substitute_rows(last_release_week, through=None, inhand='today', panel=None):
    """rows in the layout of national_first_prints.csv for report weeks after last_release_week that the 539 panel covers"""
    P=pd.read_csv(PANEL,parse_dates=['week']) if panel is None else panel
    P=P[P['st'].notna()]
    f=factors(); rows=[]
    last=pd.Timestamp(last_release_week)
    weeks=sorted(set(P['week']))
    for c2 in weeks:
        W=c2+pd.Timedelta(days=7)           # the initial-claims report week
        if W<=last: continue
        if through is not None and W>pd.Timestamp(through): continue
        g=P[P['week']==c2]
        carried=[]
        if g['st'].nunique()<JUR:
            # a late reporter (Puerto Rico most often) is carried at its last reported week and named; three or more missing and the week waits
            missing=sorted(set(P['st'])-set(g['st']))
            if len(missing)>2: continue
            prev=P[(P['week']<c2)].sort_values('week').groupby('st').tail(1).set_index('st')
            add=prev.loc[[m for m in missing if m in prev.index]].reset_index(); add['week']=c2
            g=pd.concat([g,add],ignore_index=True); carried=missing
        if g['ic'].isna().any(): continue
        ic=float(g['ic'].sum()); cw=float(g['cw'].sum()); ce=float(g['ce'].sum())
        fi,si=_factor(f,W,0); fc,sc=_factor(f,c2,1)
        if fi is None: continue
        icsa=round(ic/fi,-3)
        iusa=round(cw/fc,-3) if fc else None
        iur=round((cw/fc)/ce*100,1) if (fc and ce>0) else None
        rd=(pd.Timestamp(datetime.date.today()) if inhand=='today' else W+pd.Timedelta(days=12))
        rows.append(dict(release=('S%s'%W.strftime('%y%m%d')),ic_week=W.strftime('%b. %d'),icsa=icsa,icsa_prev_rev=np.nan,icnsa=ic,
                         iu_week=c2.strftime('%b. %d'),iur_sa=iur,iusa=iusa,iunsa=cw,kind='substitute',release_date=rd,
                         ic_week_ended=W,iu_week_ended=c2,factor_source='%s/%s'%(si,sc),carried=';'.join(carried)))
    return pd.DataFrame(rows)
def merged_file(out_path, dark_from=None, dark_weeks=None, inhand='today'):
    """write national_first_prints.csv with the substitute rows appended (and, in a drill, the real prints cut from dark_from for
    dark_weeks weeks). Returns (path, info) or (None, info) when nothing is substituted."""
    n=pd.read_csv(N45,parse_dates=['release_date','ic_week_ended','iu_week_ended'])
    info={'dark_from':None,'dark_weeks':None,'substitute_weeks':[],'last_release_week':None,'factors':[]}
    if dark_from is not None:
        d0=pd.Timestamp(dark_from); d1=d0+pd.Timedelta(days=7*int(dark_weeks)) if dark_weeks else pd.Timestamp('2100-01-01')
        cut=(n['ic_week_ended']>=d0)&(n['ic_week_ended']<d1)
        info['dark_from']=str(d0.date()); info['dark_weeks']=dark_weeks; n=n[~cut].copy()
        last=n[n['ic_week_ended']<d0]['ic_week_ended'].max(); through=d1-pd.Timedelta(days=1)
    else:
        last=n['ic_week_ended'].max(); through=None
    info['last_release_week']=str(pd.Timestamp(last).date())
    sub=substitute_rows(last, through=through, inhand=('drill' if dark_from is not None else inhand))
    if sub.empty: return None, info
    info['substitute_weeks']=[str(w.date()) for w in sub['ic_week_ended']]; info['factors']=sorted(set(sub['factor_source']))
    m=pd.concat([n,sub],ignore_index=True,sort=False).sort_values('ic_week_ended')
    m.to_csv(out_path,index=False)
    return out_path, info
if __name__=='__main__':
    p,i=merged_file('cache/claims_merged_test.csv', dark_from=sys.argv[1] if len(sys.argv)>1 else None, dark_weeks=int(sys.argv[2]) if len(sys.argv)>2 else None)
    print(p); print(i)
