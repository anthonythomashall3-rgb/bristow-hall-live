import csv,json,time,urllib.request
from pathlib import Path
from datetime import datetime,timezone
env=Path('live_data/config/local.env'); key=None
for line in env.read_text().splitlines():
    if line.startswith('FRED_API_KEY'): key=line.split('=',1)[1].strip().strip('"').strip("'")
rows=list(csv.DictReader(open('data_vault/catalog/metric_catalog.csv')))
fred=[r for r in rows if r['provider']=='fred']
OUT=Path('research/_bmeta1_fred_meta.json')
if OUT.exists():
    meta=json.load(open(OUT)); out=meta['series']; errs=meta.get('errors',[])
else:
    out={}; errs=[]
asof=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def save():
    meta={'schema':'fred_series_metadata.v1','fetched_asof':asof,
      'endpoint':'https://api.stlouisfed.org/fred/series','n_ok':len(out),'n_err':len(errs),
      'errors':errs,'series':out}
    OUT.write_text(json.dumps(meta,indent=1))
todo=[r for r in fred if r['series_id'] not in out]
print("resume: done",len(out),"todo",len(todo),flush=True)
errs=[e for e in errs if e[0] not in out]
for i,r in enumerate(todo):
    sid=r['provider_series_id']
    url=f"https://api.stlouisfed.org/fred/series?series_id={sid}&api_key={key}&file_type=json"
    ok=False
    for attempt in range(4):
        try:
            d=json.load(urllib.request.urlopen(url,timeout=25))
            s=d['seriess'][0]
            out[r['series_id']]={'provider_series_id':sid,
                'seasonal_adjustment':s.get('seasonal_adjustment'),
                'seasonal_adjustment_short':s.get('seasonal_adjustment_short'),
                'frequency_short':s.get('frequency_short')}
            ok=True; break
        except Exception as e:
            last=str(e)[:80]; time.sleep(1.5*(attempt+1))
    if not ok: errs.append([r['series_id'],sid,last])
    time.sleep(0.5)
    if i%25==0: save(); print("...",i,"/",len(todo),flush=True)
save()
print("DONE ok",len(out),"err",len(errs),flush=True)
