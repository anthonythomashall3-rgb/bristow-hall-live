# The daily index AS A USER WOULD HAVE SEEN IT on 10-16 March 2020, for labour search terms beside "unemployment"
# (10 September 2026, evening; Anthony: "find more data to speed up the 2020 call"). A window from 1 July 2019 to that
# day, daily granularity, normalized to the window's own maximum - the same construction as fetch_trends_asof_2020.py.
import time,os,sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from pytrends.request import TrendReq
import pandas as pd
pt=TrendReq(hl='en-US',tz=0,timeout=(10,30))
L=open('out/fetch_trends_asof_terms.log','a')
TERMS=[('layoffs','layoffs'),('laid off','laidoff'),('furlough','furlough'),('unemployment office','unempoffice'),('jobless','jobless'),('unemployment insurance','ui'),('unemployment claim','claim'),('lost my job','lostjob')]
DAYS=[10,11,12,13,16]
for kw,tag in TERMS:
    for dd in DAYS:
        name=f'google_trends/asof_terms/{tag}_asof_2020-03-{dd:02d}.csv'
        if os.path.exists(name): continue
        os.makedirs('google_trends/asof_terms',exist_ok=True)
        for k in range(4):
            try:
                pt.build_payload([kw],geo='US',timeframe=f'2019-07-01 2020-03-{dd:02d}'); df=pt.interest_over_time()
                df.to_csv(name); L.write(f'{name}: {len(df)} rows, last {df.index.max().date()} = {df.iloc[-1,0]}\n'); L.flush(); break
            except Exception as e: L.write(f'{name}: try {k} {str(e)[:80]}\n'); L.flush(); time.sleep(45*(k+1))
        time.sleep(8)
L.write('done\n'); L.close()
open('out/fetch_trends_asof_terms.done','w').write('done')
