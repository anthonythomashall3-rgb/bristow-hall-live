# trends_live.py - THE SEARCH WEEK'S DAILY FEED (collection 108; v3.29 form, 10 September 2026, evening: one feed per
# labour term). For each term the stitched history google_trends/live/<tag>_stitched_daily.csv is extended by a 250-day
# daily pull from Google Trends, scaled onto the history by the mean ratio over their overlap (at least 28 days) and
# appended day by day; on Google's refusal the history stands and the caller states its last day. Prints one line per
# term; the runner (bhs_run.sh) treats "appended" as new data. Run from the collection root with the venv:
#     .venv/bin/python scripts/trends_live.py
import os,sys,time,datetime
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import pandas as pd, numpy as np
TERMS=[('unemployment','unemp'),('layoffs','layoffs'),('laid off','laidoff')]
try:
    from pytrends.request import TrendReq
except Exception as e:
    print(f'search week: pytrends missing ({e})'); sys.exit(1)
pt=TrendReq(hl='en-US',tz=0,timeout=(10,30)); rc=0
for kw,tag in TERMS:
    F=f'google_trends/live/{tag}_stitched_daily.csv'
    if not os.path.exists(F): print(f'search week ({tag}): no stitched history file; run search_week.py first'); rc=1; continue
    H=pd.read_csv(F,index_col=0,parse_dates=True).iloc[:,0].astype(float).sort_index()
    df=None; err=''
    for k in range(3):
        try:
            end=datetime.date.today(); start=end-datetime.timedelta(days=250)
            pt.build_payload([kw],geo='US',timeframe=f'{start.isoformat()} {end.isoformat()}'); df=pt.interest_over_time(); break
        except Exception as e: err=str(e)[:80]; time.sleep(20*(k+1))
    if df is None or not len(df): print(f'search week ({tag}): pull failed ({err or "empty"}); history through {H.index.max().date()}'); rc=1; continue
    d=df.iloc[:,0].astype(float); d=d[~df.get('isPartial',pd.Series(False,index=df.index)).astype(bool)] if 'isPartial' in df else d
    o=d.index.intersection(H.index)
    if len(o)<28 or d.loc[o].mean()<=0: print(f'search week ({tag}): overlap too short ({len(o)} days); history through {H.index.max().date()}'); rc=1; continue
    fac=H.loc[o].mean()/d.loc[o].mean(); new=(d*fac)[d.index>H.index.max()]
    if len(new)==0: print(f'search week ({tag}): nothing new (history through {H.index.max().date()})'); continue
    H2=pd.concat([H,new]).sort_index(); H2.to_csv(F,header=[tag])
    print(f'search week ({tag}): {len(new)} day(s) appended, through {new.index.max().date()} (scale {fac:.3f} on {len(o)} overlap days)')
    time.sleep(5)
sys.exit(rc)
