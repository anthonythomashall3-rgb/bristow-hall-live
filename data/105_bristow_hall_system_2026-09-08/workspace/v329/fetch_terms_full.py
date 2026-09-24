# Full Google Trends histories for labour search terms beside "unemployment" (10 September 2026, evening): daily half-year
# windows 2004H1-2026H2 and overlapping four-year weekly windows, each normalized to its own maximum, in the layout
# collection 108's search_week.py stitches ({tag}_daily_{YYYY}H{1,2}.csv, {tag}_weekly_{from}_{to}.csv).
import time,os,sys,datetime
from pytrends.request import TrendReq
import pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__)))
TERMS={'layoffs':'layoffs','laid off':'laidoff'}
if len(sys.argv)>1: TERMS={k:v for k,v in TERMS.items() if v in sys.argv[1:]}
pt=TrendReq(hl='en-US',tz=0,timeout=(10,30))
L=open('fetch_terms_full.log','a')
def pull(kw,tf,name):
    if os.path.exists(name) or os.path.exists(name+'.empty'): return
    for k in range(5):
        try:
            pt.build_payload([kw],geo='US',timeframe=tf); df=pt.interest_over_time()
            if df is None or not len(df):
                L.write(f'{name}: empty (no daily volume); skipped\n'); L.flush(); open(name+'.empty','w').write(''); time.sleep(6); return
            df.to_csv(name); L.write(f'{name}: {len(df)} rows {df.index.min().date()}..{df.index.max().date()}\n'); L.flush(); time.sleep(6); return
        except Exception as e:
            L.write(f'{name}: try {k} {str(e)[:80]}\n'); L.flush(); time.sleep(40*(k+1))
today=datetime.date.today()
for kw,tag in TERMS.items():
    os.makedirs(tag,exist_ok=True)
    wins=[(2004,2007),(2007,2010),(2010,2013),(2013,2016),(2016,2019),(2019,2022),(2022,2026)]
    for a,b in wins:
        end=f'{b}-12-31' if b<today.year else today.isoformat()
        pull(kw,f'{a}-01-01 {end}',f'{tag}/{tag}_weekly_{a}_{b}.csv')
    for y in range(2004,today.year+1):
        for h,(m0,m1) in ((1,('01-01','06-30')),(2,('07-01','12-31'))):
            end=f'{y}-{m1}'
            if y==today.year and h==2: end=today.isoformat()
            if y==today.year and h==1 and today.month<7: end=today.isoformat()
            if pd.Timestamp(f'{y}-{m0}')>pd.Timestamp(today): continue
            pull(kw,f'{y}-{m0} {end}',f'{tag}/{tag}_daily_{y}H{h}.csv')
L.write('done\n'); L.close(); open('done.txt','w').write('done')
