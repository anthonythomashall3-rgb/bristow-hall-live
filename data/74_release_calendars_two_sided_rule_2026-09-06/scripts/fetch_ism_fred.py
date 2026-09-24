"""Fetch the discontinued ISM manufacturing series from the FRED API (NAPM = PMI composite, NAPMEI employment, NAPMNOI new orders,
NAPMPI production; FRED stopped updating them in 2016 when ISM withdrew) — the key is read from live_data/config/local.env and never printed."""
import os, sys, json, urllib.request, urllib.parse, csv
env=os.path.expandvars("$HOME/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env")
key=None
for line in open(env):
    line=line.strip()
    if 'FRED' in line and '=' in line and not line.startswith('#'):
        k,v=line.split('=',1); v=v.strip().strip('"').strip("'")
        if len(v)>=16: key=v; break
if not key: print("no FRED key found"); sys.exit(1)
out=os.path.expandvars("$HOME/mnt/Onset Detector Data/74_release_calendars_two_sided_rule_2026-09-06/data/fred_ism")
for sid in ['NAPM','NAPMEI','NAPMNOI','NAPMPI','NAPMII','NAPMSDI']:
    q=urllib.parse.urlencode(dict(series_id=sid,api_key=key,file_type='json',observation_start='1948-01-01'))
    try:
        r=urllib.request.urlopen("https://api.stlouisfed.org/fred/series/observations?"+q,timeout=60); d=json.load(r)
        obs=[(o['date'],o['value']) for o in d.get('observations',[]) if o['value'] not in ('.','')]
        with open(f"{out}/{sid}.csv",'w',newline='') as f:
            w=csv.writer(f); w.writerow(['date',sid]); w.writerows(obs)
        print(sid,'rows',len(obs),'span',obs[0][0] if obs else None,'->',obs[-1][0] if obs else None)
    except Exception as e:
        print(sid,'FAILED',str(e)[:80])
