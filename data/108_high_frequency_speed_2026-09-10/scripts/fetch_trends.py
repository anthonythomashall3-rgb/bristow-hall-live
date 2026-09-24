# Google Trends via pytrends: 'unemployment' and 'file for unemployment' (US), daily windows Jan-Jun of 2008, 2020 and every
# year 2004-2026 (each window normalized on its own), and weekly 5-year windows for the whole span. Writes google_trends/*.csv
# and out/fetch_trends.log. Google rate-limits: sleeps between calls and retries on 429.
import sys,time,os,json
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
L=open('out/fetch_trends.log','a')
def log(s): L.write(s+'\n'); L.flush()
try:
    from pytrends.request import TrendReq
except Exception as e: log(f'pytrends import failed: {e}'); sys.exit(1)
pt=TrendReq(hl='en-US',tz=0,timeout=(10,30))
def pull(kw,tf,name):
    for k in range(4):
        try:
            pt.build_payload([kw],geo='US',timeframe=tf); df=pt.interest_over_time()
            if len(df): df.to_csv(f'google_trends/{name}.csv'); log(f'{name}: {len(df)} rows {df.index.min().date()}..{df.index.max().date()}'); return True
            log(f'{name}: empty'); return False
        except Exception as e:
            log(f'{name}: try {k} {type(e).__name__} {str(e)[:80]}'); time.sleep(20*(k+1))
    return False
for kw,tag in [('unemployment','unemp'),('file for unemployment','file'),('unemployment benefits','benefits')]:
    for y in range(2004,2027):
        end=f'{y}-06-30' if y<2026 else '2026-09-09'
        if not os.path.exists(f'google_trends/{tag}_daily_{y}H1.csv'): pull(kw,f'{y}-01-01 {end}',f'{tag}_daily_{y}H1'); time.sleep(6)
        if y<2026 and not os.path.exists(f'google_trends/{tag}_daily_{y}H2.csv'): pull(kw,f'{y}-07-01 {y}-12-31',f'{tag}_daily_{y}H2'); time.sleep(6)
    for a in range(2004,2027,4):
        b=min(a+4,2026); tf=f'{a}-01-01 {b}-09-09' if b==2026 else f'{a}-01-01 {b}-12-31'
        if not os.path.exists(f'google_trends/{tag}_weekly_{a}_{b}.csv'): pull(kw,tf,f'{tag}_weekly_{a}_{b}'); time.sleep(6)
log('done')
