# The daily index AS A USER WOULD HAVE SEEN IT on each day of March 2020: a window from 1 July 2019 to that day (daily
# granularity, normalized to the window's own maximum, so the ordinary level keeps its resolution before the surge).
import time,os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from pytrends.request import TrendReq
import pandas as pd
pt=TrendReq(hl='en-US',tz=0,timeout=(10,30))
L=open('out/fetch_trends_asof.log','a')
for kw,tag in [('unemployment','unemp'),('file for unemployment','file')]:
    for dd in range(6,24):
        name=f'google_trends/asof/{tag}_asof_2020-03-{dd:02d}.csv'
        if os.path.exists(name): continue
        os.makedirs('google_trends/asof',exist_ok=True)
        for k in range(3):
            try:
                pt.build_payload([kw],geo='US',timeframe=f'2019-07-01 2020-03-{dd:02d}'); df=pt.interest_over_time()
                df.to_csv(name); L.write(f'{name}: {len(df)} rows, last {df.index.max().date()} = {df.iloc[-1,0]}\n'); L.flush(); break
            except Exception as e: L.write(f'{name}: try {k} {str(e)[:60]}\n'); L.flush(); time.sleep(30)
        time.sleep(5)
L.write('done\n')
