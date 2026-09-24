#!/usr/bin/env python3
"""Deterministic fetch of the high-frequency channels the rule needs to keep working forever.

No judgement is exercised at run time. The list below is declared in full, each identifier is
requested once, what comes back is written verbatim to data/<ID>.csv, and what does not come back is
written to out/FAILED.csv with the reason. Nothing is inferred, filled, interpolated or renamed.

WHY THESE. The rule's existing legs read the channels through which the recessions that have already
happened arrived: labour, housing, credit, orders, energy, trade, money. A recession that starts
somewhere new -- a payments outage, a pandemic, a supply seizure, an abrupt displacement of work --
will not announce itself in a monthly series published forty days late. It will appear first in what
is measured weekly or daily. These are those series, grouped by the channel they would carry, and
they are collected now so that the channel exists before it is needed rather than after.
"""
import os, re, csv, json, time, urllib.request, urllib.error
BASE=os.path.expanduser('~/mnt/Onset Detector Data')
if not os.path.isdir(BASE): BASE=os.path.expanduser('~/Projects/Onset Detector Data')
HERE=os.path.join(BASE,'186_realtime_channels_2026-09-15')
DATA,OUT=os.path.join(HERE,'data'),os.path.join(HERE,'out')
os.makedirs(DATA,exist_ok=True); os.makedirs(OUT,exist_ok=True)
CFG=os.path.join(BASE,'onset-detector-new-2026-08-23','live_data','config','local.env')
txt=open(CFG).read()
KEY=re.search(r'^FRED_API_KEY=([^\r\n]+)',txt,re.M).group(1).strip().strip('"').strip("'")
POOL=re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)',txt,re.M)
KEYS=[KEY]+([k.strip() for k in POOL.group(1).strip().strip('"').strip("'").split(',') if k.strip()] if POOL else [])
KEYS=list(dict.fromkeys(KEYS))
SERIES={
 'financial_seizure':['NFCI','ANFCI','NFCICREDIT','NFCIRISK','NFCILEVERAGE','NFCINONFINLEVERAGE',
    'STLFSI4','VIXCLS','BAMLH0A0HYM2','BAMLC0A0CM','BAMLH0A3HYC','TEDRATE','SOFR','EFFR','OBFR',
    'RRPONTSYD','WALCL','WLCFLPCL','WORAL','SP500','DJIA','NASDAQCOM','DTWEXBGS','DEXCAUS'],
 'rates_term':['T10Y2Y','T10Y3M','DGS2','DGS3MO','DGS1','DGS10','DGS30','MORTGAGE30US','MORTGAGE15US',
    'DPRIME','DFF','DTB3','DTB6','DAAA','DBAA'],
 'credit_stock_weekly':['TOTBKCR','BUSLOANS','TOTCI','REALLN','CCLACBW027SBOG','DPSACBW027SBOG',
    'H8B1058NCBCMG','CONSUMER','TLAACBW027SBOG','TOTLL'],
 'credit_quality':['DRSFRMACBS','DRCCLACBS','DRALACBS','DRBLACBS','CORCACBS','CORBLACBS','DRTSCILM','DRTSCIS'],
 'labour_weekly':['ICSA','IC4WSA','CCSA','ICNSA','CCNSA','IURSA','IURNSA'],
 'labour_monthly':['JTSJOL','JTSLDL','JTSQUL','JTSHIL','JTSTSL','AWHMAN','AWHAETP','CES0500000003','USTEMPHELPS'],
 'activity_weekly':['WEI','BBKMCOIX','BBKMLEIX','CFNAI','CFNAIDIFF','ADSINDEX'],
 'freight_supply':['TRUCKD11','RAILFRTCARLOADSD11','RAILFRTINTERMODALD11','TSIFRGHT','IPG2211S','IPUTIL','IPMINE'],
 'orders_capex':['NEWORDER','AMTMNO','AMTMUO','ACOGNO','DGORDER','MNFCTRIRSA','BUSINV','ISRATIO'],
 'housing':['HOUST','PERMIT','HOUST1F','PERMIT1','HSN1F','MSACSR','EXHOSLUSM495S','CSUSHPINSA',
    'TTLCONS','PRRESCONS','TLNRESCONS','COMPUTSA','UNDCONTSA','AUTHNOTT'],
 'consumer':['UMCSENT','MICH','RSAFS','RSXFS','PCEDG','PSAVERT','TOTALSA','DSPIC96','PCEC96'],
 'business_formation_weekly':['BUSAPPWNSAUS','BABATOTALSAUS','BFHBA4QUS','BUSAPPSAUS'],
 'uncertainty':['USEPUINDXD','USEPUNEWSINDXD','EMVOVERALLEMV','WLEMUINDXD','GEPUCURRENT'],
 'energy':['DCOILWTICO','DCOILBRENTEU','DHHNGSP','GASREGW','WTISPLC','PNGASEUUSDM'],
 'trade_external':['NETEXP','BOPGSTB','IEABC','EXPGS','IMPGS','DTWEXAFEGS'],
 'fiscal_public':['FYFSD','MTSDS133FMS','W006RC1Q027SBEA','GFDEBTN','FDHBFIN'],
 'productivity_price':['PCEPILFE','CPIAUCSL','CPILFESL','PPIACO','ULCNFB','OPHNFB'],
}
def get(sid,key):
    u=('https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s'
       '&file_type=json&observation_start=1900-01-01'%(sid,key))
    with urllib.request.urlopen(u,timeout=60) as r:
        return json.load(r)
ok,bad=[],[]
ki=0
for ch,ids in SERIES.items():
    for sid in ids:
        p=os.path.join(DATA,sid+'.csv')
        if os.path.exists(p) and os.path.getsize(p)>80:
            ok.append((sid,ch,'cached',os.path.getsize(p))); continue
        err=None
        for attempt in range(len(KEYS)*2):
            k=KEYS[ki%len(KEYS)]; ki+=1
            try:
                d=get(sid,k); obs=d.get('observations',[])
                rows=[(o['date'],o['value']) for o in obs if o['value'] not in ('.','')]
                if not rows: err='empty'; break
                with open(p,'w',newline='') as f:
                    w=csv.writer(f); w.writerow(['date','value']); w.writerows(rows)
                ok.append((sid,ch,'%s..%s'%(rows[0][0],rows[-1][0]),len(rows))); err=None; break
            except urllib.error.HTTPError as e:
                err='HTTP %s'%e.code
                if e.code in (429,403): time.sleep(2); continue
                break
            except Exception as e:
                err=type(e).__name__+':'+str(e)[:60]; time.sleep(1)
        if err: bad.append((sid,ch,err))
        time.sleep(0.12)
with open(os.path.join(OUT,'MANIFEST_realtime.csv'),'w',newline='') as f:
    w=csv.writer(f); w.writerow(['series','channel','range','n']); w.writerows(ok)
with open(os.path.join(OUT,'FAILED.csv'),'w',newline='') as f:
    w=csv.writer(f); w.writerow(['series','channel','reason']); w.writerows(bad)
print('fetched %d   failed %d'%(len(ok),len(bad)))
for s,c,r in bad: print('  FAIL %-22s %-24s %s'%(s,c,r))
