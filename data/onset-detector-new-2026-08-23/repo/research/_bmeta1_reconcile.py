import csv,json,collections
# --- CH-R67 classifier (copied verbatim from research/_ch_r67_recertify.py) ---
def classify(sid):
    s=sid.upper()
    if s in ('USREC','USRECD','USRECDM','USRECM'): return('SPECIAL_NBER',0.99,'NBER recession dummy')
    if s.endswith('MDLR'): return('SPECIAL_FORECAST',0.9,'SEP longer-run')
    if s=='GDPNOW': return('SPECIAL_FORECAST',0.95,'nowcast')
    if s in ('SAHMREALTIME',): return('SPECIAL_REALTIME',0.95,'real-time Sahm')
    if s in ('SAHMCURRENT',): return('SA',0.85,'Sahm on revised SA UNRATE')
    if s=='FEDTARMDLR': return('SPECIAL_FORECAST',0.9,'fed funds LR')
    if s.startswith('LNS') or s.startswith('LNU') and s.startswith('LNS'): return('SA',0.9,'CPS SA LNS')
    if s.startswith('LNS'): return('SA',0.9,'CPS SA LNS')
    if s.startswith('LES'): return('SA',0.85,'CPS earnings SA')
    if s.endswith('WSA') or s=='IC4WSA': return('SA',0.9,'claims SA MA')
    if s in ('USINFO','USLAH','USGOOD','USSERV','USTRADE','USCONS','USMINE','USPBS','USFIRE','USEHS','USLEISURE'): return('SA',0.85,'CES industry SA')
    if s.startswith('CES') and s not in (): return('SA',0.8,'CES estab SA')
    if s in ('CIVPART','UNRATE','PAYEMS','EMRATIO','MSACSR','HOUST','PERMIT','UMCSENT','ICSA','CCSA','IURSA','INDPRO','RSAFS','PCE','UNEMPLOY'): return('SA',0.9,'known SA')
    if s=='CNP16OV': return('POP_CONTROL',0.85,'CPS pop control')
    if s.endswith('NS') or s.endswith('NSA') or 'NSA' in s: return('NSA',0.9,'name ends NS/NSA')
    if s in ('CPIAUCNS','ICNSA','CCNSA','PPIACO','WPU0561','GFDEBTN','MSPUS','B4701C0A222NBEA','MTSDS133FMS'): return('NSA',0.85,'NSA accounting/price')
    MKT=('DGS','GS','TB','DTB','DFF','FEDFUNDS','DEX','DTWEX','DCOIL','MCOIL','OILPRICE','WTISPLC','DCPF','DCPN','CPFF','CPF','T10Y','T5Y','T1Y','DPRIME','DAAA','DBAA','AAA','BAA','BAML','DHHNGSP','DHH','MORTGAGE','SOFR','IRLT','VXO','VIX','NASDAQ','GAS','WGS','SP500','WPU')
    for p in MKT:
        if s.startswith(p): return('MKT',0.85,'market rate/price')
    return('UNKNOWN',0.0,'no rule')

# family map
def fam_landed(short):
    if short in ('SA','SAAR','SSA'): return 'SA'
    if short in ('NSA',): return 'NSA'
    return 'UNRESOLVED'
def fam_r67(cls):
    if cls=='SA': return 'SA'
    if cls in ('NSA','MKT','POP_CONTROL'): return 'NSA'   # r67 treats rates/prices/pop-ctrl as non-SA
    return 'SPECIAL'  # SPECIAL_*/UNKNOWN: no firm SA opinion

rows=list(csv.DictReader(open('data_vault/catalog/metric_catalog.csv')))
sa_meta=json.load(open("data_vault/catalog/fred_series_metadata.v1.json"))
absent=set(sa_meta['absent']); landed=sa_meta['series']

# certified never/negligible set from CH-R67
cert=set()
try:
    for r in csv.DictReader(open('research/never_revised_recertify_v1.csv')):
        cert.add(r['series'])
except FileNotFoundError: pass

disagreements=[]; agree=0; newly=0; special=0
for r in rows:
    sid=r['series_id']; short=r['seasonal_adjustment']
    lf=fam_landed(short)
    cls,conf,reason=classify(sid); rf=fam_r67(cls)
    if lf=='UNRESOLVED':
        continue  # nothing landed to compare
    if rf=='SPECIAL':
        newly+=1; continue  # r67 had no firm SA opinion -> landed value is new info, not a conflict
    if lf==rf: agree+=1
    else:
        disagreements.append((sid,short,lf,cls,rf,round(conf,2),sid in cert))
print("landed(compared vs r67 firm opinion): agree=%d disagree=%d r67-no-opinion(new)=%d"%(agree,len(disagreements),newly))
print("\nDISAGREEMENTS (series | landed_short | landed_fam | r67_class | r67_fam | r67_conf | never_rev_cert):")
for d in sorted(disagreements,key=lambda x:(not x[6],x[0])):
    print("  %-22s %-5s %-4s vs %-12s %-4s conf=%.2f cert=%s"%(d[0],d[1],d[2],d[3],d[4],d[5],d[6]))
# voided certs = disagreements that carry a never-revised cert
voids=[d for d in disagreements if d[6]]
print("\nVOIDED never-revised certifications (landed SA disagrees with r67 basis):",len(voids))
for v in voids: print("  VOID:",v[0],"landed=",v[1],"r67_said=",v[3])
json.dump({'agree':agree,'disagreements':disagreements,'voids':[v[0] for v in voids],'newly_resolved':newly},
          open('research/_bmeta1_reconcile.json','w'),indent=1)
