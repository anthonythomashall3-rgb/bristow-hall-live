#!/usr/bin/env python3
"""The full transmission panel. Deterministic: fixed identifier list, one GET each, cosd pinned so
FRED returns full history rather than its default graph window. Written unchanged.

FOUR ROUTES a shock must pass through to become a recession, whatever the shock is. A channel built
on the route rather than the cause is a channel for a recession that has not happened yet.
"""
import csv, os, time, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, 'data'); os.makedirs(DATA, exist_ok=True)
URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=1776-07-04&coed=9999-12-31'
S = [
 # ---- ROUTE 1: someone stops being paid ----
 ('DRALACBS','payments','delinquency rate, all loans, all commercial banks'),
 ('DRCCLACBS','payments','delinquency rate, credit card loans'),
 ('DRBLACBN','payments','delinquency rate, business loans'),
 ('DRCLACBS','payments','delinquency rate, consumer loans'),
 ('DRSFRMACBS','payments','delinquency rate, single-family residential mortgages'),
 ('DRCRELEXFACBS','payments','delinquency rate, commercial real estate'),
 ('CORALACBN','payments','charge-off rate, all loans'),
 ('CORCACBS','payments','charge-off rate, consumer loans'),
 ('CORBLACBS','payments','charge-off rate, business loans'),
 # ---- ROUTE 2: firms stop committing ----
 ('AMTMUO','commitments','manufacturers unfilled orders, all manufacturing'),
 ('AMDMUO','commitments','manufacturers unfilled orders, durable goods'),
 ('UMTMUO','commitments','unfilled orders, total manufacturing'),
 ('ANDENO','commitments','nondefence capital goods orders excluding aircraft -- the core investment commitment'),
 ('NEWORDER','commitments','new orders, nondefence capital goods ex aircraft'),
 ('AUTHNOTT','commitments','housing units authorised but NOT STARTED -- intention withdrawn'),
 ('AMTMNO','commitments','manufacturers new orders, all manufacturing'),
 ('BUSINV','commitments','total business inventories'),
 ('ISRATIO','commitments','inventories to sales ratio'),
 # ---- ROUTE 3: physical activity stops ----
 ('TRUCKD11','physical','truck tonnage index'),
 ('RAILFRTCARLOADSD11','physical','rail freight carloads'),
 ('RAILFRTINTERMODALD11','physical','rail intermodal traffic'),
 ('TSIFRGHTC','physical','freight transportation services index'),
 ('IPUTIL','physical','electric and gas utility output, 1939 on'),
 ('IPG2211S','physical','electric power generation'),
 ('IPMINE','physical','mining production'),
 ('CAPUTLB50001SQ','physical','capacity utilisation, total industry'),
 ('TCU','physical','capacity utilisation, total industry, monthly'),
 ('DCOILWTICO','physical','crude oil price, daily'),
 # ---- ROUTE 4: credit reprices ----
 ('BAMLH0A0HYM2','credit','ICE BofA high yield option-adjusted spread'),
 ('BAMLC0A0CM','credit','ICE BofA investment grade option-adjusted spread'),
 ('NFCI','credit','Chicago Fed national financial conditions index'),
 ('ANFCI','credit','adjusted national financial conditions index'),
 ('NFCICREDIT','credit','financial conditions, credit subindex'),
 ('NFCILEVERAGE','credit','financial conditions, leverage subindex'),
 ('STLFSI4','credit','St Louis Fed financial stress index'),
 ('DRTSCILM','credit','net share of banks tightening standards, commercial and industrial loans'),
 ('DRTSCLCC','credit','net share tightening standards, credit cards'),
 ('SUBLPDCLCT','credit','banks reporting stronger demand for consumer loans'),
 # ---- real-time employment proxies ----
 ('ICSA','realtime','initial claims, seasonally adjusted weekly'),
 ('CCSA','realtime','continued claims, weekly'),
 ('IURSA','realtime','insured unemployment rate, weekly'),
 ('TEMPHELPS','realtime','temporary help employment'),
 ('AWHAETP','realtime','average weekly hours, total private'),
 ('AWOTMAN','realtime','average weekly overtime hours, manufacturing'),
 # ---- expectations / commitments to hire ----
 ('UMCSENT','expect','Michigan consumer sentiment'),
 ('USACSCICP02STSAM','expect','OECD consumer confidence, United States'),
 ('USSLIND','expect','leading index for the United States'),
 ('USALOLITONOSTSAM','expect','OECD composite leading indicator, United States'),
]
rows = []
for sid, route, note in S:
    p = os.path.join(DATA, sid + '.csv')
    try:
        with urllib.request.urlopen(URL % sid, timeout=60) as r: body = r.read()
        ln = body.decode('utf-8','replace').strip().split('\n')
        n = len(ln)-1
        first = ln[1].split(',')[0] if n>0 else ''
        last = ln[-1].split(',')[0] if n>0 else ''
        if not first[:4].isdigit(): st, n, first, last = 'INVALID_ID', 0, '', ''
        else: open(p,'wb').write(body); st='ok'
    except Exception as e:
        st, n, first, last = 'FAIL %s'%str(e)[:40], 0, '', ''
    rows.append(dict(id=sid, route=route, file=sid+'.csv', n=n, first=first, last=last,
                     status=st, source=URL%sid, gathered='2026-09-15', note=note))
    print('%-22s %-12s %-11s %s .. %s'%(sid, route, st, first, last), flush=True)
    time.sleep(0.1)
with open(os.path.join(HERE,'MANIFEST_transmission.csv'),'w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ok=sum(1 for r in rows if r['status']=='ok')
print('\nsaved %d of %d'%(ok,len(rows)))
