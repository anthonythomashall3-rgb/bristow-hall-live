import csv, json, os, glob, datetime, statistics
ROOT='.'
OBS='prefetch/alfred_obs'

# ---------- classifier (name-convention; catalog SA field is 100% 'unresolved') ----------
def classify(sid):
    s=sid.upper()
    # special/non-economic
    if s in ('USREC','USRECD','USRECDM','USRECM'): return('SPECIAL_NBER',0.99,'NBER recession dummy; changes only on re-dating')
    if s.endswith('MDLR'): return('SPECIAL_FORECAST',0.9,'SEP/longer-run projection (forecast class)')
    if s=='GDPNOW': return('SPECIAL_FORECAST',0.95,'Atlanta Fed nowcast (forecast class)')
    if s in ('SAHMREALTIME',): return('SPECIAL_REALTIME',0.95,'real-time Sahm; never-revised by construction')
    if s in ('SAHMCURRENT',): return('SA',0.85,'Sahm on revised (SA) UNRATE')
    if s=='FEDTARMDLR': return('SPECIAL_FORECAST',0.9,'fed funds target longer-run (SEP)')
    # SA families
    if s.startswith('LNS') or s.startswith('LNU') and s.startswith('LNS'): return('SA',0.9,'CPS seasonally adjusted (LNS)')
    if s.startswith('LNS'): return('SA',0.9,'CPS SA (LNS)')
    if s.startswith('LES'): return('SA',0.85,'CPS earnings SA (LES)')
    if s.endswith('WSA') or s=='IC4WSA': return('SA',0.9,'claims SA moving avg')
    if s in ('USINFO','USLAH','USGOOD','USSERV','USTRADE','USCONS','USMINE','USPBS','USFIRE','USEHS','USLEISURE'): return('SA',0.85,'CES industry employment SA')
    if s.startswith('CES') and s not in (): return('SA',0.8,'CES establishment SA (annual benchmark)')
    if s in ('CIVPART','UNRATE','PAYEMS','EMRATIO','MSACSR','HOUST','PERMIT','UMCSENT','ICSA','CCSA','IURSA','INDPRO','RSAFS','PCE','UNEMPLOY'): return('SA',0.9,'known SA series')
    # population control (level-break trap, NSA level)
    if s=='CNP16OV': return('POP_CONTROL',0.85,'CPS population control; Jan level break, unrevised history')
    # NSA explicit
    if s.endswith('NS') or s.endswith('NSA') or 'NSA' in s: return('NSA',0.9,'name ends NS/NSA')
    if s in ('CPIAUCNS','ICNSA','CCNSA','PPIACO','WPU0561','GFDEBTN','MSPUS','B4701C0A222NBEA','MTSDS133FMS'):
        return('NSA',0.85,'NSA/nonseasonal accounting or price')
    # market prices / rates / spreads (no seasonal adjustment concept)
    MKT=('DGS','GS','TB','DTB','DFF','FEDFUNDS','DEX','DTWEX','DCOIL','MCOIL','OILPRICE','WTISPLC','DCPF','DCPN','CPFF','CPF','T10Y','T5Y','T1Y','DPRIME','DAAA','DBAA','AAA','BAA','BAML','DHHNGSP','DHH','MORTGAGE','SOFR','IRLT','VXO','VIX','NASDAQ','GAS','WGS','SP500','WPU')
    for p in MKT:
        if s.startswith(p): return('MKT',0.85,'market price/rate/spread ('+p+')')
    return('UNKNOWN',0.0,'no rule')

# ---------- gather 73 certified never/negligible ----------
rows=[]
with open('revision_certification_v2_roster.csv') as f:
    R={r['series_id']:r for r in csv.DictReader(f)}
for sid,r in R.items():
    if r['class_r25'] in ('never_revised','negligible_revision'):
        sa,conf,reason=classify(sid)
        rows.append(dict(src='roster',series=sid,cert_class=r['class_r25'],sa_class=sa,sa_conf=conf,sa_reason=reason,
                         n_alfred_vintages=r['n_alfred_vintages'],early_v=r['early_vintage'],late_v=r['late_vintage'],
                         roster_share_revised=r['share_revised'],roster_mean_abs=r['mean_abs_rev']))
with open('revision_certification_v3_fredmd_panel.csv') as f:
    for r in csv.DictReader(f):
        if r['class'] in ('never_revised','negligible_revision','never','negligible'):
            sa,conf,reason=classify(r['column'])
            rows.append(dict(src='fredmd',series=r['column'],cert_class=r['class'],sa_class=sa,sa_conf=conf,sa_reason=reason,
                             n_alfred_vintages='',early_v='',late_v='',roster_share_revised=r['share_revised'],roster_mean_abs=r['mean_abs_rev']))

from collections import Counter
print("N certified never/negligible:",len(rows))
print("sa_class tally:",dict(Counter(x['sa_class'] for x in rows)))

# ---------- offline trailing-5y-window test on cached SA-suspects ----------
def load_vint(sid,v):
    p=f"{OBS}/{sid}__{v}.json"
    if not os.path.exists(p): return None
    d=json.load(open(p))
    out={}
    for o in d['observations']:
        try: out[o['date']]=float(o['value'])
        except: pass
    return out
def yrs_before(vdate, lo, hi):
    y,m,dd=map(int,vdate.split('-'))
    return (f"{y-hi:04d}-{m:02d}-01", f"{y-lo:04d}-{m:02d}-01")

SUSPECT=[x for x in rows if x['sa_class'] in ('SA','POP_CONTROL')]
tw=[]
for x in SUSPECT:
    sid,ev,lv=x['series'],x['early_v'],x['late_v']
    E=load_vint(sid,ev); L=load_vint(sid,lv)
    rec=dict(series=sid,sa_class=x['sa_class'],cert_class=x['cert_class'],early_v=ev,late_v=lv)
    if not E or not L:
        rec.update(testable=False,note='vintages not cached offline'); tw.append(rec); continue
    lo,hi=yrs_before(ev,1,5)  # obs 1-5yr old at EARLY vintage
    win=[d for d in E if lo<=d<hi and d in L]
    if not win:
        rec.update(testable=False,note='no overlap in trailing-5y window'); tw.append(rec); continue
    changed=[d for d in win if abs(E[d]-L[d])>1e-9]
    diffs=[abs(E[d]-L[d]) for d in win]
    rec.update(testable=True, window=f"{lo[:7]}..{hi[:7]}", n_window=len(win),
               frac_changed=round(len(changed)/len(win),4),
               mean_abs_change=round(sum(diffs)/len(diffs),5),
               max_abs_change=round(max(diffs),5))
    tw.append(rec)
print("\n=== trailing-5y-window offline test (obs 1-5yr old at early vintage) ===")
for r in tw:
    if r.get('testable'): print(f"  {r['series']:14} {r['sa_class']:11} n={r['n_window']:3} frac_changed={r['frac_changed']:.3f} mean_abs={r['mean_abs_change']:.4f} max={r['max_abs_change']:.4f} [{r['window']}]")
    else: print(f"  {r['series']:14} {r['sa_class']:11} NOT TESTABLE: {r['note']}")

# ---------- free-tier propagation ----------
FREE27="DCOILWTICO DEXJPUS DEXUSEU T10Y3M PPIACO GFDEBTN CPIAUCNS MSACSR DFF DGS30 CPFF DGS20 FEDFUNDS DCPF3M TB3MS DTB3 DGS10 DGS6MO DGS2 GS1 GS10 IRLTLT01USM156N DGS3 CIVPART DGS7 DGS5 ICNSA".split()
free_sa=[b for b in FREE27 if classify(b)[0] in ('SA','POP_CONTROL')]
print("\n=== free tier (27) SA members:",free_sa)
print("=== free tier survives: 27 -> ", 27-len(free_sa), " (Horn/Kaiser lift of removed members: MSACSR step8 4/7->4/7; CIVPART step24 5/9->5/9 = ZERO)")

# ---------- rebasing relabel (CH-R21 shares) ----------
rebase={'INDPRO':0.419,'CMRMTSPL':0.394,'GDPC1':0.986,'W875RX1':0.997}
# CH-R44 medians
chr44={'INDPRO':0.667,'GDPC1':0.746}
print("\n=== rebasing relabel (CH-R44 fig = rebase-confounded upper bound; CH-R21 rebase-net share) ===")
for k,v in rebase.items():
    ub=chr44.get(k)
    print(f"  {k:10} CH-R44_upper_bound={('%.3f'%ub) if ub else 'n/a':>7}  CH-R21_rebase_net_share={v}")

# ---------- write outputs ----------
out_csv='never_revised_recertify_v1.csv'
cols=['src','series','cert_class','sa_class','sa_conf','sa_reason','n_alfred_vintages','early_v','late_v','roster_share_revised','roster_mean_abs']
with open(out_csv,'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for x in rows: w.writerow({k:x.get(k,'') for k in cols})
summary=dict(
  probe='CH-R67_NEVER_REVISED_RECERTIFY', kind='read_only_20class', network=False, store_writes=0,
  catalog_sa_field='100% unresolved (268/268) — store cannot certify SA partition from metadata; ACQUISITION NEEDED: FRED seasonal_adjustment field',
  n_certified_never_negligible=len(rows),
  sa_class_tally=dict(Counter(x['sa_class'] for x in rows)),
  sa_suspect_series=sorted([x['series'] for x in rows if x['sa_class'] in ('SA','POP_CONTROL')]),
  trailing_window_test=dict(
     method='two cached vintages (early,late); obs 1-5yr old at EARLY vintage; frac changed by LATE vintage',
     caveat='FULL rolling annual 5y-rewrite test needs intermediate vintages ~13mo apart = NOT cached, network-blocked. ACQUISITION NEEDED.',
     results=tw),
  free_tier_propagation=dict(before=27, sa_members=free_sa, after=27-len(free_sa),
     horn=5, kaiser=9, horn_kaiser_change='NONE — MSACSR(step8) and CIVPART(step24) each added 0 factor lift; Horn 5 reached at DGS30 step10, Kaiser 9 at DGS10 step17'),
  rebasing_relabel={k:dict(chr44_upper_bound=chr44.get(k), chr21_rebase_net_share=v) for k,v in rebase.items()},
)
json.dump(summary, open('never_revised_recertify_v1.json','w'), indent=2)
print("\nWROTE",out_csv,"and never_revised_recertify_v1.json")
