"""Leg C (weekly state breadth, the lab's 13/104/25/50/2/52 machine with real-time seasonal factors) run on the Department's
own weekly releases 1945-1983 as read from the HathiTrust volumes (26_dol_weekly_claims_1946-1983/parsed, tolerant reader
and cross-week reconciliation of 5 Sep 2026).  These pages ARE the first prints.  Nothing in the machine is changed:
sa_realtime (factors re-estimated each December from data then available), breadth(13,104,25), peak_calls(...,50,2,52),
publication 7 days after the week.  Warm-up: the lab reports its record five years after its file begins (1986 -> 1991);
the same rule here gives 1950 on, so 1948-11 is inside the warm-up and 1953 is the first scorable peak."""
import sys, os, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
ODD=os.path.expanduser('~/mnt/Onset Detector Data'); LAB=ODD+'/24_bristow_rule_lab/workspace/lab'
sys.path.insert(0,LAB+'/weekly'); from sa_realtime import sa_realtime
def mo(t): return pd.Timestamp(t.year,t.month,1)
src=open(LAB+'/weekly/final_caller.py').read(); exec("def peak_calls"+src.split("def peak_calls")[1].split("def trough_calls")[0])
R=pd.read_csv(ODD+'/26_dol_weekly_claims_1946-1983/parsed/ic_weekly_state_1945_1983_long.csv',parse_dates=['week'])
R=R[R.source.isin(['both','own','implied'])].dropna(subset=['ic'])
W=R.pivot_table(index='week',columns='state',values='ic').sort_index()
# spike filter on single-source cells: log deviation from the centred 5-week median beyond 0.7
single=R[R.source!='both'].pivot_table(index='week',columns='state',values='ic').reindex_like(W).notna()
L=np.log(W); med=L.rolling(5,center=True,min_periods=3).median(); spike=((L-med).abs()>0.7)&single
W=W.mask(spike); print('spikes removed',int(spike.sum().sum()))
W=W.loc[:,W.notna().mean()>0.5]; W=W.drop(columns=[c for c in ('Virgin Islands','Puerto Rico') if c in W.columns])
grid=pd.date_range(W.index.min(),W.index.max(),freq='W-SAT'); W=W.reindex(W.index.union(grid)).reindex(grid)
present=W.notna()
SA=pd.DataFrame({c:sa_realtime(W[c].interpolate(limit=8),first_year=1950,minobs=200) for c in W.columns})
SA=SA.where(present.reindex(SA.index).fillna(False))          # breadth counts observed states only
def breadth(sm,Lk,thsq):
    K=SA.rolling(sm,min_periods=max(4,sm//2)).mean()*100.0
    S=K-K.rolling(Lk,min_periods=Lk//2).min()
    cov=S.notna().sum(axis=1)
    return ((S>=thsq).sum(axis=1)/cov.where(cov>=20)*100.0).dropna()
B=breadth(13,104,25.)
calls=peak_calls(B,50.,2,52,'first_above')
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07']; TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11']
def me(t): return t+pd.offsets.MonthEnd(0)
print('leg C calls on the volumes (published, dated):'); rows=[]
for pub,d in calls:
    hit=None
    for p,q in zip(PK,TR):
        if pd.Timestamp(p+'-01')-pd.DateOffset(months=6)<=d<=pd.Timestamp(q+'-01'): hit=p; break
    lag=(pub-me(pd.Timestamp(hit+'-01'))).days if hit else None
    print(f"  {pub:%Y-%m-%d}  dated {d:%Y-%m}  {'-> '+hit+f' lag {lag:+d} d' if hit else 'QUIET-PERIOD CALL' if pub>=pd.Timestamp('1950-01-01') else 'warm-up'}")
cov=B.notna(); print('breadth series',B.index[0].date(),'->',B.index[-1].date(),'| states in panel',SA.shape[1])
print('breadth max in each recession window and max in quiet 1950-83:')
for p,q in zip(PK,TR):
    w=B[(B.index>=pd.Timestamp(p+'-01')-pd.DateOffset(months=6))&(B.index<=pd.Timestamp(q+'-01'))]; print(f"  {p}: max {w.max() if len(w) else float('nan'):5.1f}  first>=50 {w[w>=50].index[0].date() if (w>=50).any() else '-'}")
q=pd.Series(True,index=B.index)
for p,t in zip(PK,TR): q[(B.index>=pd.Timestamp(p+'-01')-pd.DateOffset(months=9))&(B.index<=pd.Timestamp(t+'-01')+pd.DateOffset(months=18))]=False
qb=B[q&(B.index>='1950-01-01')]; print('  quiet: max',round(float(qb.max()),1),'weeks>=50:',int((qb>=50).sum()),'of',len(qb))
B.to_csv('LEGC_VOLUMES_breadth_1945_1983.csv')
