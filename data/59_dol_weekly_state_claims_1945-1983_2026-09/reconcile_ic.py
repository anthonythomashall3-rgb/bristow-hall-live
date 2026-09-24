"""Assemble the tolerant prints into one weekly state initial-claims panel, 1945-1983, reconciling each print against its
neighbour: IC(t) - change(t) is the release's own second print of IC(t-1).  Sources kept per cell."""
import glob, pandas as pd, numpy as np
D=pd.concat([pd.read_csv(f,parse_dates=['week']).assign(pass1=('tolerant2' not in f)) for f in sorted(glob.glob('ic_tolerant_*.csv'))+sorted(glob.glob('ic_tolerant2_*.csv'))],ignore_index=True)
D=D[(D.week>='1945-01-01')&(D.week<='1983-12-31')]
# a print must fall inside its volume's own years (from the label, e.g. v17_1961_62 -> 1961-1962, one year of slack each side): misdated pages out
import re as _re
def _yrs(lab):
    m=_re.search(r'_(19\d\d)_(\d\d)',str(lab)); 
    if not m: m2=_re.search(r'_(19\d\d)',str(lab)); return (int(m2.group(1))-1,int(m2.group(1))+2) if m2 else (1940,1990)
    a=int(m.group(1)); b=int(m.group(1)[:2]+m.group(2)); return (a-1,b+1)
lo=D.volume.map(lambda l:_yrs(l)[0]); hi=D.volume.map(lambda l:_yrs(l)[1])
bad=(D.week.dt.year<lo)|(D.week.dt.year>hi); print('prints outside their volume years dropped:',int(bad.sum())); D=D[~bad]
D['week']=D.week.dt.normalize()
# own prints: median where a state-week has several (two issues print the same week in the 1946-54 layouts)
# the first-pass reader anchors dates on the exact heading, the second pass on any date on the page: where both read a cell, the first pass rules
D['pass']=D.pass1.astype(bool)
own1=D[D['pass']].groupby(['state','week']).ic.median(); own2=D[~D['pass']].groupby(['state','week']).ic.median()
own=own1.combine_first(own2).rename('own')
imp=D.dropna(subset=['chg']).copy(); imp['prev']=imp.ic-imp.chg; imp['pweek']=imp.week-pd.Timedelta(days=7)
imp1=imp[imp['pass']].groupby(['state','pweek']).prev.median(); imp2=imp[~imp['pass']].groupby(['state','pweek']).prev.median()
implied=imp1.combine_first(imp2).rename('implied'); implied.index.names=['state','week']
# third print: the 1956-83 pages print the change from a YEAR AGO, so IC(t) - chg_yr(t) is a print of IC(t-52 weeks)
if 'chg_yr' in D.columns:
    imy=D.dropna(subset=['chg_yr']).copy(); imy['prev']=imy.ic-imy.chg_yr; imy['pweek']=imy.week-pd.Timedelta(days=364)
    yr=imy.groupby(['state','pweek']).prev.median().rename('implied_yr'); yr.index.names=['state','week']
else: yr=None
P=pd.concat([own,implied]+([yr] if yr is not None else []),axis=1)
def digit_fix(a,b):
    """a and b differ by a dropped/added digit or a factor 10: return the value consistent with b's magnitude"""
    if pd.isna(a) or pd.isna(b) or b<=0: return np.nan
    for f in (10,100,0.1,0.01):
        if abs(a*f-b)<=max(3,0.01*b): return a*f
    return np.nan
rows=[]
for (st,wk),r in P.iterrows():
    o,i=r['own'],r['implied']; y=r.get('implied_yr',np.nan)
    cands=[(v,s) for v,s in ((o,'own'),(i,'implied'),(y,'implied_yr')) if pd.notna(v) and v>0]
    def agree(a,b): return abs(a-b)<=max(3,0.005*max(a,b))
    if len(cands)>=2:
        # any two prints that agree confirm the cell; the third, if it disagrees, is the OCR error
        pairs=[(a,b) for k,a in enumerate(cands) for b in cands[k+1:] if agree(a[0],b[0])]
        if pairs:
            v=pairs[0][0][0] if pairs[0][0][1]=='own' else (pairs[0][1][0] if pairs[0][1][1]=='own' else pairs[0][0][0]); rows.append((st,wk,v,'both'))
        elif pd.notna(o) and pd.notna(i):
            fx=digit_fix(o,i)
            if pd.notna(fx): rows.append((st,wk,fx,'repaired'))
            else: rows.append((st,wk,np.nan,'conflict'))
        else: rows.append((st,wk,np.nan,'conflict'))
    elif len(cands)==1: rows.append((st,wk,cands[0][0],cands[0][1]))
R=pd.DataFrame(rows,columns=['state','week','ic','source'])
# plausibility: within [0.1x, 10x] of the state's rolling median of confirmed values
R=R.sort_values(['state','week'])
def plaus(g):
    ref=g[g.source.isin(['both','repaired'])].set_index('week').ic
    if len(ref)<5: return g
    med=ref.rolling(26,min_periods=5,center=True).median().reindex(g.week,method='nearest').values
    bad=(g.ic.values>10*med)|(g.ic.values<0.1*med)
    g=g.copy(); g.loc[bad,'source']='implausible'; g.loc[bad,'ic']=np.nan; return g
R=R.groupby('state',group_keys=False).apply(plaus)
R.to_csv('ic_weekly_state_1945_1983_long.csv',index=False)
W=R.dropna(subset=['ic']).pivot_table(index='week',columns='state',values='ic')
W.to_csv('ic_weekly_state_1945_1983_wide.csv')
cov=W.notna().sum(axis=1)
print('state-weeks with a value:',int(W.notna().sum().sum()),'| weeks:',len(W),'| weeks with >=40 states:',int((cov>=40).sum()),'| >=45:',int((cov>=45).sum()))
print('sources:',R.source.value_counts().to_dict())
print('coverage by year (median states per week):'); print(cov.groupby(cov.index.year).median().astype(int).to_dict())
