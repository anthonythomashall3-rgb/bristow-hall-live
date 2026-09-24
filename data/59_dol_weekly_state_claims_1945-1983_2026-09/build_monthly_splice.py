"""Monthly state initial-claims panel from the weekly release, and the 1945-2026 splice for the international runner
(6 September 2026, replacing the 5 September files).  ic_monthly_state_1945_1983_from_weekly.csv: the mean of the
weeks ending in each month (at least two weeks), weekly-average units, from weekly_ic_1945_1983.csv.
us_state_ic_monthly_1945_2026_spliced.csv: that panel where it exists, otherwise the ETA 5159 monthly total (c1)
divided by weekdays/5 - the SAME weekly-average units throughout.  The 5 September splice put 5159 monthly TOTALS
after weekly averages, a 4.3x step at January 1971 in every state; the runner's opener (year-on-year log change,
z-scored on quiet months) saw a spurious rise through 1971 (inside the 1969-70 episode's aftermath, so no call was
made and no quiet month was affected, but the file was wrong)."""
import pandas as pd, numpy as np
R="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/"
W=pd.read_csv(R+'26_dol_weekly_claims_1946-1983/parsed/weekly_ic_1945_1983.csv',index_col=0,parse_dates=True)
g=W.groupby(W.index.to_period('M')); M=g.mean().where(g.count()>=2); M.index=M.index.to_timestamp(); M=M.dropna(how='all')
M.to_csv('ic_monthly_state_1945_1983_from_weekly.csv')
d=pd.read_csv(R+'24_bristow_rule_lab/workspace/lab/dol/ar5159.csv',low_memory=False); d['m']=pd.to_datetime(d['rptdate'],errors='coerce').dt.to_period('M').dt.to_timestamp(); d=d.dropna(subset=['m'])
d['c1']=pd.to_numeric(d['c1'],errors='coerce'); A=d.dropna(subset=['c1']).pivot_table(index='m',columns='st',values='c1',aggfunc='sum').sort_index().where(lambda x:x>0)
def wk(m): return np.busday_count(m.date(),(m+pd.offsets.MonthEnd(0)+pd.Timedelta(days=1)).date())/5.0
A=A.div(pd.Series([wk(m) for m in A.index],index=A.index),axis=0)
cols=sorted(set(M.columns)|set(A.columns)); idx=M.index.union(A.index)
S=M.reindex(index=idx,columns=cols).combine_first(A.reindex(index=idx,columns=cols))
S.to_csv('us_state_ic_monthly_1945_2026_spliced.csv')
r=(np.log(M.reindex(columns=cols))-np.log(A.reindex(index=M.index,columns=cols))).loc['1971-01':'1983-04'].stack()
print(f"monthly from weekly {M.shape} {M.index.min():%Y-%m}..{M.index.max():%Y-%m}; splice {S.shape} {S.index.min():%Y-%m}..{S.index.max():%Y-%m}; release vs 5159/(weekdays/5) 1971-83 on {len(r)} cells: median log ratio {r.median():+.3f}, IQR {r.quantile(.25):+.3f}..{r.quantile(.75):+.3f}")
print('seam check AL 1970-11..1971-03:',S.loc['1970-11':'1971-03','AL'].round(0).tolist())
