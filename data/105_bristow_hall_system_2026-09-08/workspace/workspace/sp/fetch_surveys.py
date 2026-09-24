# fetch the zero-lag surveys and the ISM (if FRED still carries them) for the confirmer scan; the key is read from local.env and never printed
import os,json,urllib.request,pandas as pd
MNT=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data'); ENV=os.path.join(MNT,'onset-detector-new-2026-08-23','live_data','config','local.env')
KEY=''
for line in open(ENV):
    if line.startswith('FRED_API_KEY='): KEY=line.strip().split('=',1)[1].strip().strip('"').strip("'")
assert KEY and len(KEY)==32
os.makedirs('cache/surveys',exist_ok=True)
for sid in ['GACDFSA066MSFRBPHI','GACDISA066MSFRBNY','NFCI','CFNAI','USSLIND','NAPM','MANEMP','TEMPHELPS','UMCSENT','MICH','CONCCONF','BAMLH0A0HYM2','T10Y3M','DGS10','RRSFS','RETAILSMSA','PERMIT','NEWORDER','DGORDER','ACOGNO','AWHMAN','ICSA']:
    url=f'https://api.stlouisfed.org/fred/series/observations?series_id={sid}&api_key={KEY}&file_type=json&observation_start=1945-01-01'
    try:
        d=json.load(urllib.request.urlopen(url,timeout=30)); obs=[(o['date'],o['value']) for o in d['observations'] if o['value']!='.']
        pd.DataFrame(obs,columns=['date','value']).to_csv(f'cache/surveys/{sid}.csv',index=False); print(sid,len(obs),obs[0][0],obs[-1][0])
    except Exception as e: print(sid,'FAILED',str(e)[:60])
