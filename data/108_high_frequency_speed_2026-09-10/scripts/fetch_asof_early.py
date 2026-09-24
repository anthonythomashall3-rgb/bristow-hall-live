# as-of windows (1 July 2019 -> day) for 2-9 March 2020, the labour terms: what a user would have seen each day
import time,os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from pytrends.request import TrendReq
pt=TrendReq(hl='en-US',tz=0,timeout=(10,30))
for kw,tag in [('layoffs','layoffs'),('laid off','laidoff'),('unemployment','unemp')]:
    for dd in range(2,10):
        name=f'google_trends/asof_terms/{tag}_asof_2020-03-{dd:02d}.csv'
        if os.path.exists(name): continue
        for k in range(4):
            try:
                pt.build_payload([kw],geo='US',timeframe=f'2019-07-01 2020-03-{dd:02d}'); df=pt.interest_over_time(); df.to_csv(name); break
            except Exception as e: time.sleep(30*(k+1))
        time.sleep(6)
print('done')
