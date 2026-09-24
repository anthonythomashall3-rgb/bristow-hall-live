import json,glob,statistics,csv
def load(sha):
    p=glob.glob(f'live_data/store/normalized/sha256/{sha[:2]}/{sha}.json')
    return json.load(open(p[0]))['records'] if p else None
def asof(sid):
    for tag in ('.DEEPASOF','.ASOF'):
        if tag in sid: return sid.split(tag)[-1]
    return None
# collect all vintage receipts -> source_id -> set(sha)
srcs={}
for f in glob.glob('live_data/store/receipts/*vintages*/*.json'):
    d=json.load(open(f)); srcs.setdefault(d['source_id'],set()).add(d['normalized_sha256'])
# base -> substrings matching its source keys (merge main+deep)
BASES={
 'ICSA':'fred_icsa_api_vintages','IURSA':'fred_iursa_api_vintages','UNRATE':'fred_unrate_api_vintages',
 'PAYEMS':'fred_payems_api_vintages','HOUST':'fred_houst_api_vintages','PERMIT':'fred_permit_api_vintages',
 'INDPRO':'fred_indpro_api_vintages','TCU':'fred_tcu_api_vintages','CMRMTSPL':'fred_cmrmtspl_api_vintages',
 'GDPC1':'fred_gdpc1_api_vintages','GACDFSA066MSFRBPHI':'fred_gacdfsa066msfrbphi_api_vintages',
 'W875RX1':'fred_w875rx1_api_vintages','SAHMREALTIME':'fred_sahmrealtime_api_vintages',
 'UMCSENT':'fred_umcsent_api_vintages','NFCI':'fred_nfci_api_vintages',
}
META={
 'ICSA':('SA','ICNSA','current_only',True,'weekly claims; SA factors re-estimated annually'),
 'IURSA':('SA','IURNSA','absent',True,'insured unemployment rate SA'),
 'UNRATE':('SA','UNRATENSA','absent',True,'household survey SA'),
 'PAYEMS':('SA','PAYNSA','absent',True,'establishment survey SA + benchmark'),
 'HOUST':('SA','HOUSTNSA','absent',True,'housing starts, volatile SA'),
 'PERMIT':('SA','PERMITNSA','absent',True,'building permits, volatile SA'),
 'INDPRO':('SA','IPB50001N','absent',True,'industrial production SA'),
 'TCU':('SA','none','absent',True,'capacity utilization, SA-only published'),
 'CMRMTSPL':('SA','CMRMTSPLNSA','absent',True,'real mfg+trade sales SA'),
 'GDPC1':('SA','none','absent',True,'GDP SA annual rate; NSA effectively unpublished'),
 'GACDFSA066MSFRBPHI':('SA','none','absent',True,'Philly coincident model index, filtered/SA'),
 'W875RX1':('SA','none','absent',True,'real PI ex transfers SA'),
 'SAHMREALTIME':('SA-derived','none','absent',True,'derived from UNRATE(SA); inherits seasonal channel'),
 'UMCSENT':('NA','n/a','n/a',False,'Michigan sentiment published NSA -> already as-of-honest'),
 'NFCI':('NA','n/a','n/a',False,'financial index, not seasonally adjusted'),
}
def revstats(records):
    first={};last={};fa={};la={};vints=set()
    for r in records:
        v=r.get('value')
        if v in (None,'','.'): continue
        try: v=float(v)
        except: continue
        op=r['observation_period']; a=asof(r['series_id'])
        if a is None: continue
        vints.add(a)
        if op not in fa or a<fa[op]: fa[op]=a; first[op]=v
        if op not in la or a>la[op]: la[op]=a; last[op]=v
    revs=[];pct=[]
    for op in first:
        d=last[op]-first[op]; revs.append(d)
        if first[op]!=0: pct.append(abs(d)/abs(first[op])*100)
    ar=[abs(x) for x in revs]
    return dict(nobs=len(first),vints=len(vints),
        mad=statistics.mean(ar) if ar else 0,
        rms=(statistics.mean([x*x for x in revs])**0.5) if revs else 0,
        p90=sorted(ar)[min(int(0.9*len(ar)),len(ar)-1)] if ar else 0,
        med_pct=statistics.median(pct) if pct else 0,
        share=round(sum(1 for x in ar if x>1e-9)/len(ar)*100,1) if ar else 0)
rows=[]
for base,pat in BASES.items():
    recs=[]
    for sid,shas in srcs.items():
        if sid.startswith(pat):
            for s in shas:
                r=load(s)
                if r: recs+=r
    st=revstats(recs); m=META[base]
    rows.append([base,pat,m[0],m[1],m[2],m[3],st['vints'],st['nobs'],
        round(st['mad'],4),round(st['rms'],4),round(st['p90'],4),round(st['med_pct'],3),st['share'],m[4]])
with open('research/sa_revision_audit_v1.csv','w',newline='') as fh:
    w=csv.writer(fh)
    w.writerow(['series_id','store_source_prefix','sa_status','nsa_sibling','sibling_in_store','seasonal_channel','n_vintages','n_obs_periods','within_lane_rev_mad','within_lane_rev_rms','within_lane_rev_p90','within_lane_rev_med_pct','pct_obs_revised','note'])
    for r in rows: w.writerow(r)
for r in rows:
    print(f"{r[0]:<20}{r[2]:<11}sib={r[4]:<12}vint={r[6]:<5}nobs={r[7]:<6}mad={r[8]:<11}rev%med={r[11]:<8}revised%={r[12]}")
print('WROTE research/sa_revision_audit_v1.csv')
