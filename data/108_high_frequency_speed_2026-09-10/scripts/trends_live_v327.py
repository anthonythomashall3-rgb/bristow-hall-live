# trends_live.py - the search week's daily feed for the live system. Pulls Google Trends, United States, "unemployment",
# daily, for the last 250 days (daily granularity needs a window under nine months), stitches the pull onto the stitched
# history (google_trends/live/unemp_stitched_daily.csv, first written from 105/workspace/s2/search_week.py's stitch of the
# half-year and four-year windows) by the mean ratio over the overlap, appends the days after the history's last day and
# rewrites the file. On failure (Google's 429, network) the file is left as it is and the failure is logged; the object
# then reads through its last day, which the site states. Run with the collection's venv: .venv/bin/python scripts/trends_live.py
import os,sys,time,datetime
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import pandas as pd, numpy as np
F='google_trends/live/unemp_stitched_daily.csv'
if not os.path.exists(F): print('search week: no stitched history file; run search_week.py first'); sys.exit(1)
H=pd.read_csv(F,index_col=0,parse_dates=True).iloc[:,0].astype(float).sort_index()
today=datetime.date.today(); start=(today-datetime.timedelta(days=250)).isoformat()
try:
    from pytrends.request import TrendReq
except Exception as e: print(f'search week: pytrends missing ({e}); history through {H.index.max().date()}'); sys.exit(1)
pt=TrendReq(hl='en-US',tz=0,timeout=(10,30)); df=None
for k in range(4):
    try:
        pt.build_payload(['unemployment'],geo='US',timeframe=f'{start} {today.isoformat()}'); df=pt.interest_over_time(); break
    except Exception as e:
        err=str(e)[:70]; time.sleep(30*(k+1))
if df is None or not len(df): print(f'search week: pull failed ({err if "err" in dir() else "empty"}); history through {H.index.max().date()}'); sys.exit(1)
d=df.iloc[:,0].astype(float); d.index=pd.to_datetime(d.index)
if 'isPartial' in df.columns: d=d[~df['isPartial'].astype(bool).values]   # the current, partial day is not a datum
o=d.index.intersection(H.index); o=o[o>=d.index.min()+pd.Timedelta(days=7)]   # overlap after the pull's first week
if len(o)<28 or d.loc[o].mean()<=0: print(f'search week: overlap too short ({len(o)} days); history through {H.index.max().date()}'); sys.exit(1)
fac=H.loc[o].mean()/d.loc[o].mean(); new=d[d.index>H.index.max()]*fac
if len(new)==0: print(f'search week: nothing new (history through {H.index.max().date()})'); sys.exit(0)
pd.concat([H,new]).sort_index().to_csv(F,header=['unemployment'])
print(f'search week: {len(new)} day(s) appended, through {new.index.max().date()} (scale {fac:.3f} on {len(o)} overlap days)')
