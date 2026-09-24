import subprocess, re, os, sys, pandas as pd
BASE='https://api.imf.org/external/sdmx/2.1/data/IMF.STA,PI,2.0.0/'
OUT='/home/claude/lab/imf'
os.makedirs(OUT, exist_ok=True)

def get(key):
    url=f'{BASE}{key}?startPeriod=1940-01&endPeriod=2026-12'
    r=subprocess.run(['curl','-sS','-A','Mozilla/5.0','--max-time','90',url],
                     capture_output=True,text=True)
    return r.stdout

def parse(xml):
    """Return {(idx,tr): DataFrame} for monthly series."""
    out={}
    for part in xml.split('<Series ')[1:]:
        idx=re.search(r'PRODUCTION_INDEX="([^"]+)"',part)
        tr =re.search(r'TYPE_OF_TRANSFORMATION="([^"]+)"',part)
        if not idx or not tr: continue
        obs=re.findall(r'TIME_PERIOD="([^"]+)"\s+OBS_VALUE="([^"]+)"',part)
        if not obs: continue
        d=[]
        for t,v in obs:
            m=re.match(r'(\d{4})-M(\d{2})$',t)
            if not m: continue
            d.append((f'{m.group(1)}-{m.group(2)}-01', float(v)))
        if d: out[(idx.group(1),tr.group(1))]=pd.DataFrame(d,columns=['observation_date','value'])
    return out

COUNTRIES=['KOR','JPN','BRA','CAN','ESP','FRA','USA','DEU','ITA','NLD','BEL',
           'GBR','AUT','FIN','PRT','GRC','IRL','LUX','SVK','SVN','EST','LVA','LTU']
rows=[]
for c in COUNTRIES:
    xml=get(f'{c}...M')
    got=parse(xml)
    for (idx,tr),df in got.items():
        if tr not in ('IX','SA_IX'): continue
        p=f'{OUT}/{c}_{idx}_{tr}.csv'
        df.to_csv(p,index=False)
        rows.append((c,idx,tr,len(df),df.observation_date.iloc[0][:7],df.observation_date.iloc[-1][:7]))
for r in rows: print(*r,sep='\t')
