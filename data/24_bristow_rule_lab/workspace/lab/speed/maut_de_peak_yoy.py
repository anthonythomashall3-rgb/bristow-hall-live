"""German truck-toll index, peak side, read year over year on the UNADJUSTED daily values (no
seasonal model, no turn-of-year artefact from the adjustment): weekly means, the 4-week mean's
log change on the same weeks a year earlier; a peak episode begins the first week the change
stands at or below -x log points for r weeks after 26 weeks above it; published +7 days.
Reachable: the 2020 peak (Feb 2020) and every quiet week from 2009; the 2008 peak is inside
the first year.  Result (2 September 2026): the Januaries stay - a negative; see the log."""
import pandas as pd, numpy as np
x=pd.read_excel('/home/claude/lab/acq/maut/lkw_maut_daily_2026-08-22.xlsx',sheet_name='csv-42191-b01',header=0)
x.columns=['stat','geo','date','week','weekday','adj','value']; x['date']=pd.to_datetime(x['date']); x['value']=pd.to_numeric(x['value'],errors='coerce')
raw=x[x.adj.str.contains('unbereinigt')].set_index('date')['value'].dropna().sort_index()
W=raw.resample('W-SUN').mean().dropna(); N=np.log(W.rolling(4).mean())*100.0
yoy=(N-N.shift(52)).dropna()
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
PK=pd.Timestamp('2020-02-01'); TR=pd.Timestamp('2020-04-01')
if __name__=='__main__':
    for xth in (2.,3.,5.,8.):
        for r in (1,2,4):
            cond=(yoy<=-xth).rolling(r).sum()>=r
            starts=[]; below=0
            for t,v in cond.items():
                if v:
                    if below>=26: starts.append(t)
                    below=0
                else: below+=1
            pk=[s for s in starts if -3<=md(s,PK)<=md(TR,PK)+3]; other=[s for s in starts if s not in pk]
            end=(PK+pd.DateOffset(months=1))-pd.Timedelta(days=1)
            print(f'x {xth:3.0f} r {r}: 2020 peak {"called "+(pk[0]+pd.Timedelta(days=7)).strftime("%Y-%m-%d")+f" ({(pk[0]+pd.Timedelta(days=7)-end).days:+d} d)" if pk else "not called"}; other {[s.strftime("%Y-%m") for s in other]}')
