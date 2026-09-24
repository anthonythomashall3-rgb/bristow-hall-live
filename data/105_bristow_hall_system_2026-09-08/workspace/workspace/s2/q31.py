# q31.py - THE HUB READ ACROSS THE STATES: the share of states whose three-month mean unemployment rate (first prints,
# BLS LAUS releases 1994-2026) stands 0.3667 above its twelve-month low (the hub's line, per state), at the breadth line
# 0.60 (state breadth's line), with the hub's own vacancy hold (the vacancy gap at its line in two of the prior nine
# months and in the latest print known on the day). No new number. Fires on the state release day; re-arms when the
# share falls below 0.60. Every fire 1994-2026 is listed, inside or outside a recession window (six months before the
# peak month to the trough month). Also the same object without the hold, and the share's path 2024-2026.
# Run: PYTHONPATH=. python3 s2/q31.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk46.py').read().split(_MARK)[0])
pw=pickle.load(open('cache/w46_carry.pkl','rb'))
H=os.path.expanduser('~/Projects/Onset Detector Data/bristow-hall-harvest/data/bls_laus/state_ur_first_prints_refmonth_fixed.csv')
d=pd.read_csv(H); d=d[(d.geo_level=='state')&(d.series_id=='state_ur')]
d['obs_period']=pd.to_datetime(d['obs_period']); d['vintage_date']=pd.to_datetime(d['vintage_date'])
d=d.sort_values(['geo_code','obs_period','vintage_date']).drop_duplicates(['geo_code','obs_period'],keep='first')
W=d.pivot(index='obs_period',columns='geo_code',values='value').sort_index(); REL=d.groupby('obs_period')['vintage_date'].max()
m3=W.rolling(3,min_periods=3).mean(); low=m3.rolling(12,min_periods=12).min().shift(1); gap=(m3-low)
share=((gap>=pw['sahm']-EPS).sum(axis=1)/gap.notna().sum(axis=1)).where(gap.notna().sum(axis=1)>=40).dropna()
G=vgap2_asof(pw['vk'],pw['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
PKm=[pd.Timestamp(x) for x in PK]; TRm=[pd.Timestamp(x) for x in TR]
def in_rec(t): return any(PKm[i]-pd.DateOffset(months=6)<=pd.Timestamp(t.year,t.month,1)<=TRm[i] for i in range(len(PKm)))
def hold_ok(m,day,back=pw['hback'],vl=pw['vl']):
    w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=vl-EPS]
    if len(hit)<2: return False
    known=pubs[(pubs.index<=m)&(pubs<=day)]
    return len(known)>0 and float(G.get(known.index.max(),np.nan))>=vl-EPS
for hold in (True,False):
    fires=[]; armed=True
    for m,v in share.items():
        day=REL[m]
        if armed and v>=0.60-EPS:
            if (not hold) or hold_ok(m,day): fires.append((day.date().isoformat(),m.strftime('%Y-%m'),round(float(v),2),'in' if in_rec(m) else 'OUTSIDE')); armed=False
        elif not armed and v<0.60-EPS: armed=True
    print(('WITH the vacancy hold' if hold else 'without the hold')+':',fires)
s=share[share.index>='2024-06-01']; print('share 2024-06..:',{m.strftime('%Y-%m'):round(float(v),2) for m,v in s.items()})
s=share[(share.index>='2001-10-01')&(share.index<='2003-12-01')]; print('share 2001-10..2003:',{m.strftime('%Y-%m'):round(float(v),2) for m,v in s.items()})
s=share[(share.index>='2009-04-01')&(share.index<='2011-12-01')]; print('share 2009-04..2011:',{m.strftime('%Y-%m'):round(float(v),2) for m,v in s.items()})
s=share[(share.index>='2020-03-01')&(share.index<='2021-12-01')]; print('share 2020-03..2021:',{m.strftime('%Y-%m'):round(float(v),2) for m,v in s.items()})
