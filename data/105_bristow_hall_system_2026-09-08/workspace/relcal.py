"""Actual first-print release dates from ALFRED's vintage columns: for each observation month, the first vintage date on which a value for
that month appears. Saved as a calendar for the housing starts (HOUST, 1960-), the unemployment rate (UNRATE), job openings (JTSJOL, 2010-)."""
from mini import *
import csv
def release_calendar(series):
    rows=list(csv.reader(open(AL+series+"_all_vintages.csv"))); h=rows[0]
    vd=[pd.Timestamp(c.split('_')[-1]) for c in h[1:]]; dates=[pd.Timestamp(r[0]) for r in rows[1:]]
    out={}
    for i,m in enumerate(dates):
        for j in range(1,len(h)):
            v=rows[1+i][j]
            if v not in ('','.'):
                out[m]=(vd[j-1],float(v)); break
    return pd.DataFrame({'first_release':{m:a for m,(a,b) in out.items()},'first_print':{m:b for m,(a,b) in out.items()}}).sort_index()
if __name__=='__main__':
    for s in ['HOUST','UNRATE','JTSJOL']:
        c=release_calendar(s); c.to_csv(f'cache/relcal_{s}.csv')
        lag=(c.index.to_series().apply(lambda m:(c.loc[m,'first_release']-(m+pd.offsets.MonthEnd(0))).days))
        print(s, c.index.min().date(), c.index.max().date(), len(c), '| days after month end: median',int(lag.median()),'min',int(lag.min()),'max',int(lag.max()),'| release day-of-month median',int(c['first_release'].dt.day.median()),'range',int(c['first_release'].dt.day.min()),'-',int(c['first_release'].dt.day.max()))
        if s=='HOUST':
            print('  HOUST first-release day-of-month by decade:',{d:int(c[(c.index.year>=d)&(c.index.year<d+10)]['first_release'].dt.day.median()) for d in range(1960,2030,10)})
            print('  months whose first release came >25 days after month end:',[(m.strftime('%Y-%m'),c.loc[m,'first_release'].strftime('%Y-%m-%d')) for m in c.index if (c.loc[m,'first_release']-(m+pd.offsets.MonthEnd(0))).days>25][:40])
