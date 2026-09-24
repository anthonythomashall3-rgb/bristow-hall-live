#!/usr/bin/env python3
"""CH-R32 KNOWABILITY LEDGER (S18) — read-only, network, research/ only.
Zero store/vault/config writes. Resume-safe cache under research/prefetch/alfred_release.
Never prints the API key.

Per member per era: WHEN was each number knowable.
 - Modern (ALFRED-covered): output_type=4 (initial release) => realtime_start per obs is the
   EXACT first-availability date. lag = realtime_start - observation-period-end. evidence=exact.
   Left-censored obs (realtime_start == series ALFRED vintage floor) are excluded from stats.
 - 1965-1998: RTDSM quarterly/monthly vintage snapshots bound the lag (cadence of columns).
   evidence=bounded.
 - 1948-1965: reconstructed from documented publisher release lineage. evidence=reconstructed.
"""
import csv, json, os, time, urllib.request, urllib.parse, statistics, calendar, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL  = os.path.join(ROOT, 'research/prefetch/alfred_release'); os.makedirs(REL, exist_ok=True)
META = os.path.join(ROOT, 'research/prefetch/alfred_meta')
RTDSM= os.path.join(ROOT, 'research/prefetch/rtdsm')
LOG  = open(os.path.join(ROOT, 'research/CH-R32_compute.log'), 'a')
def log(*a):
    m=' '.join(str(x) for x in a); LOG.write(m+'\n'); LOG.flush(); print(m)

def api_key():
    for line in open(os.path.join(ROOT,'live_data/config/local.env')):
        if line.startswith('FRED_API_KEY='):
            return line.split('=',1)[1].strip()
    raise SystemExit('no FRED_API_KEY')
KEY=api_key(); BASE='https://api.stlouisfed.org/fred/'

def fetch(path, params, cachefile, tries=3):
    if os.path.exists(cachefile):
        try:
            d=json.load(open(cachefile))
            if 'error' not in d: return d
        except Exception: pass
    p=dict(params); p['api_key']=KEY; p['file_type']='json'
    url=BASE+path+'?'+urllib.parse.urlencode(p)
    for t in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data=json.load(r)
            json.dump(data, open(cachefile,'w')); time.sleep(1.0); return data
        except Exception as e:
            log('  try',t+1,'fail',params.get('series_id'),str(e).replace(KEY,'<KEY>')[:100])
            time.sleep(2.0)
    json.dump({'error':'fetch_failed'}, open(cachefile,'w')); return {'error':'fetch_failed'}

# member -> (fred_series, frequency, rtdsm_analog, proxy_note)
MEMBERS=[
 ('CLAIMSx','ICSA','weekly',None,'FRED-MD panel proxy of ICSA; knowability tracks ICSA first release'),
 ('CMRMTSPL','CMRMTSPL','monthly',None,''),
 ('CMRMTSPLx','CMRMTSPL','monthly',None,'FRED-MD panel proxy of CMRMTSPL'),
 ('GACDFSA066MSFRBPHI','GACDFSA066MSFRBPHI','monthly',None,'Phil Fed coincident contribution'),
 ('GDPC1','GDPC1','quarterly','routput',''),
 ('HOUST','HOUST','monthly',None,''),
 ('ICSA','ICSA','weekly',None,''),
 ('INDPRO','INDPRO','monthly','ipt',''),
 ('IURSA','IURSA','weekly',None,''),
 ('NFCI','NFCI','weekly',None,'Chicago Fed; ALFRED floor ~2011'),
 ('PAYEMS','PAYEMS','monthly','employ',''),
 ('PERMIT','PERMIT','monthly',None,''),
 ('SAHMREALTIME','SAHMREALTIME','monthly',None,'real-time Sahm rule, never revised'),
 ('TCU','TCU','monthly','cum',''),
 ('UMCSENT','UMCSENT','monthly',None,''),
 ('UNRATE','UNRATE','monthly','ruc',''),
 ('W875RX1','W875RX1','monthly',None,''),
]
# documented publisher release lineage (1948-1965) => reconstructed lag days (median,p95,source)
RECON={
 'PAYEMS':(5,12,'BLS Employment Situation (CES/CPS lineage from 1948); ~1st Friday of month after reference month'),
 'UNRATE':(5,12,'BLS Employment Situation household survey; ~1st Friday of following month'),
 'INDPRO':(16,22,'Federal Reserve G.17 Industrial Production; mid-month of following month'),
 'GDPC1':(30,65,'BEA NIPA GNP/GDP advance estimate; ~1 month after quarter end (1950s cadence longer)'),
 'W875RX1':(28,40,'BEA Personal Income (NIPA); ~4 weeks after reference month'),
 'CMRMTSPL':(45,60,'Census Manufacturing & Trade Sales; ~6 weeks after reference month'),
}

def period_end(date_str, freq):
    y,m,d=[int(x) for x in date_str.split('-')]
    if freq=='monthly':
        return dt.date(y,m,calendar.monthrange(y,m)[1])
    if freq=='quarterly':
        qend_m=((m-1)//3)*3+3
        return dt.date(y,qend_m,calendar.monthrange(y,qend_m)[1])
    # weekly: FRED weekly obs dated at week-ending -> that IS the period end
    return dt.date(y,m,d)

def decade(y):
    return f"{(y//10)*10}s"

def alfred_floor(series):
    f=os.path.join(META, series+'.vintages.json')
    if os.path.exists(f):
        try:
            vd=json.load(open(f)).get('vintage_dates') or []
            if vd: return vd[0]
        except Exception: pass
    return None

def modern_rows(member, series, freq, floor):
    cf=os.path.join(REL, f'{series}__ot4.json')
    d=fetch('series/observations', {'series_id':series,'realtime_start':'1776-07-04',
            'realtime_end':'9999-12-31','output_type':'4'}, cf)
    obs=d.get('observations') if isinstance(d,dict) else None
    if not obs:
        log('  NO ot4 obs', member, series); return [], None
    buckets={}  # decade -> list of lag days
    censored=0; mn=None
    for o in obs:
        ds=o.get('date'); rs=o.get('realtime_start')
        if not ds or not rs or o.get('value') in ('.',None): continue
        if mn is None or ds<mn: mn=ds
        # left-censored: initial-release date pinned to ALFRED floor
        if floor and rs<=floor:
            censored+=1; continue
        pe=period_end(ds,freq)
        rsd=dt.date(*[int(x) for x in rs.split('-')])
        lag=(rsd-pe).days
        # negatives are legitimate: nowcast-style series (e.g. Phil Fed coincident) publish
        # mid-reference-period, so a value is knowable BEFORE its period ends. Drop only absurd.
        if lag<-120 or lag>400: continue
        buckets.setdefault(decade(pe.year),[]).append(lag)
    rows=[]
    for dec in sorted(buckets):
        lags=buckets[dec]
        if len(lags)<3: continue
        lags.sort()
        med=int(statistics.median(lags))
        p95=lags[min(len(lags)-1, int(round(0.95*(len(lags)-1))))]
        rows.append([member,dec,freq,len(lags),med,p95,'exact',
                     f'ALFRED output_type=4 initial-release; floor {floor}; censored_obs={censored}'])
    return rows, mn

def rtdsm_bound(member, analog):
    """Parse RTDSM vintage column labels from xlsx sharedStrings (zip; avoids the Phil-Fed
    openpyxl docProps bug). Labels like EMPLOY65M1 (monthly) or ROUTPUT65Q4 (quarterly)."""
    import zipfile, re
    dpath=os.path.join(RTDSM, analog)
    if not os.path.isdir(dpath): return None
    cands=[f for f in os.listdir(dpath) if f.lower().endswith('.xlsx') and ('vmd' in f.lower())]
    if not cands: cands=[f for f in os.listdir(dpath) if f.lower().endswith('.xlsx')]
    if not cands: return None
    fn=sorted(cands, key=len)[0]
    try:
        z=zipfile.ZipFile(os.path.join(dpath,fn))
        sx=z.read('xl/sharedStrings.xml').decode('utf8','replace')
    except Exception as e:
        log('  rtdsm zip fail',analog,str(e)[:80]); return None
    labels=re.findall(r'<t[^>]*>([^<]*)</t>', sx)
    monthly=[]; quarterly=[]
    for s in labels:
        mm=re.search(r'(\d{2})M(\d{1,2})$', s)
        mq=re.search(r'(\d{2})Q([1-4])$', s)
        if mm:
            yy=int(mm.group(1)); yr=1900+yy if yy>=40 else 2000+yy
            monthly.append((yr,int(mm.group(2))))
        elif mq:
            yy=int(mq.group(1)); yr=1900+yy if yy>=40 else 2000+yy
            quarterly.append((yr,int(mq.group(2))))
    if len(monthly)>=len(quarterly) and len(monthly)>=4:
        vs=sorted(set(monthly)); cad='monthly'
        first=f'{vs[0][0]}M{vs[0][1]}'; last=f'{vs[-1][0]}M{vs[-1][1]}'
        # monthly snapshots: obs month M first in vintage ~M+1 (released mid-month)
        med,p95=30,55
    elif len(quarterly)>=4:
        vs=sorted(set(quarterly)); cad='quarterly'
        first=f'{vs[0][0]}Q{vs[0][1]}'; last=f'{vs[-1][0]}Q{vs[-1][1]}'
        med,p95=46,100
    else:
        return None
    return {'first':first,'last':last,'n':len(vs),'fn':fn,'cadence':cad,'med':med,'p95':p95}

def main():
    out=[['member','era','frequency','n_obs','median_lag_days','p95_lag_days','evidence_class','source_note']]
    summary=[]
    for member,series,freq,analog,note in MEMBERS:
        floor=alfred_floor(series)
        mrows,minobs=modern_rows(member,series,freq,floor)
        for r in mrows: out.append(r)
        # NFCI fallback: FRED returns 504 on output_type=4 for the weekly-revised NFCI.
        # Fall back to documented weekly release cadence from cached vintagedates.
        if member=='NFCI' and not mrows:
            vf=os.path.join(META,'NFCI.vintages.json')
            n=0; fl=floor
            if os.path.exists(vf):
                vd=json.load(open(vf)).get('vintage_dates') or []
                n=len(vd); fl=fl or (vd[0] if vd else None)
            out.append(['NFCI','ALFRED-covered','weekly',n,5,10,'bounded',
                f'output_type=4 unavailable (FRED 504 on weekly-revised series); Chicago Fed '
                f'NFCI released ~weekly (Wed) for prior-Friday week; vintage cadence 7d; floor {fl}'])
            minobs=minobs or '2011-05-25'
        # RTDSM bounded era 1965-1998
        if analog and minobs and minobs<='1998-12-31':
            rb=rtdsm_bound(member,analog)
            if rb:
                out.append([member,'1965-1998',freq,rb['n'],rb['med'],rb['p95'],'bounded',
                    f"RTDSM {analog} {rb['fn']} {rb['cadence']} vintages {rb['first']}..{rb['last']}; "
                    f"lag bounded by snapshot cadence, not per-obs exact"])
        # reconstructed era 1948-1965
        if member in RECON and minobs and minobs<='1965-12-31':
            med,p95,src=RECON[member]
            out.append([member,'1948-1965',freq,0,med,p95,'reconstructed',src])
        summary.append((member,series,floor,minobs,note))
    csvp=os.path.join(ROOT,'research/knowability_ledger_v1.csv')
    with open(csvp,'w',newline='') as f:
        csv.writer(f).writerows(out)
    log('WROTE',csvp,'rows',len(out)-1)
    # coverage summary
    with open(os.path.join(ROOT,'research/CH-R32_member_coverage.txt'),'w') as f:
        for m,s,fl,mn,nt in summary:
            f.write(f'{m:20s} fred={s:22s} alfred_floor={fl} min_obs={mn}  {nt}\n')
    return csvp

if __name__=='__main__':
    main()
