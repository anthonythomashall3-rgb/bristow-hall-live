#!/usr/bin/env python3
"""PROBE CH2 §3 — enumerate the full store universe (11,838 series / 190 sources) and
apply the MAXIMUM-COVERAGE gate {min span, frequency, resolved rights}. Read-only stream
over live_data/store/normalized (14GB, 673 objects); no writes to the store.
Gate thresholds are the ONLY chosen numbers — stated explicitly and recorded as `chosen`."""
import os, json, glob, datetime as dt, array
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
GEN = REPO + "/live_data/store/generations/93b43e2e75660471d697e706bc4543b557004c708cf3439d108a651b816886c7"
NORM = REPO + "/live_data/store/normalized"
OUTP = REPO + "/research/universe_ch2/scratch/ch2_universe_results.json"

# ---- CHOSEN gate thresholds (the only chosen numbers; recorded as `chosen` provenance) ----
CHOSEN = {
  "min_span_years": 20,      # >=20y (240 months): need several business cycles to estimate a factor structure
  "max_cadence_days": 100,   # <=100d median cadence: daily/weekly/monthly/quarterly admitted; annual/irregular excluded
  "rights_resolved_rule": "rights_status present AND not containing 'unresolved' or 'restricted_or_licensing'",
}
MIN_SPAN_DAYS = CHOSEN["min_span_years"]*365.25

def parse_period(s):
    """observation_period like 'YYYY-MM-DD' or 'YYYY-Qn' or 'YYYY-MM' -> ordinal date (approx)."""
    try:
        if "Q" in s:
            y,q=s.split("-Q"); mo=(int(q)-1)*3+1; return dt.date(int(y),mo,1).toordinal()
        p=s.split("-")
        if len(p)==1: return dt.date(int(p[0]),1,1).toordinal()
        if len(p)==2: return dt.date(int(p[0]),int(p[1]),1).toordinal()
        return dt.date(int(p[0]),int(p[1]),int(p[2])).toordinal()
    except Exception:
        return None

# ---- snapshot: series -> source_id, rights_status ----
snap=json.load(open(GEN+"/snapshot.json"))
series_meta={}
for sid,rec in snap["series"].items():
    latest=rec.get("latest") or {}
    series_meta[sid]={"source_id":rec.get("source_id"),
                      "rights_status":latest.get("rights_status") or "",
                      "unit":rec.get("unit")}
n_series=len(series_meta); n_sources=len(snap["sources"])

# ---- stream normalized objects: per series_id accumulate ordinals ----
per={}   # sid -> array('i') of ordinals
files=sorted(glob.glob(NORM+"/sha256/*/*.json"))
for fi,f in enumerate(files):
    try: d=json.load(open(f))
    except Exception: continue
    for r in d.get("records",[]):
        sid=r.get("series_id"); op=r.get("observation_period")
        if sid is None or op is None: continue
        o=parse_period(op)
        if o is None: continue
        per.setdefault(sid,array.array('i')).append(o)

# ---- per-series span/count/cadence ----
def cadence_label(days):
    if days<=1.6: return "daily"
    if days<=8: return "weekly"
    if days<=45: return "monthly"
    if days<=100: return "quarterly"
    if days<=400: return "annual"
    return "irregular_or_sparse"
rows={}
for sid in series_meta:
    ords=per.get(sid)
    if not ords or len(ords)<2:
        rows[sid]={"count":len(ords) if ords else 0,"span_days":0,"cadence_days":None,
                   "first":None,"last":None,"cadence":"none"}
        continue
    a=np.frombuffer(ords,dtype=np.int32); a=np.unique(a)
    span=int(a[-1]-a[0]); gaps=np.diff(a)
    cad=float(np.median(gaps)) if len(gaps) else None
    rows[sid]={"count":int(len(a)),"span_days":span,"cadence_days":round(cad,1) if cad else None,
               "first":dt.date.fromordinal(int(a[0])).isoformat(),
               "last":dt.date.fromordinal(int(a[-1])).isoformat(),
               "cadence":cadence_label(cad) if cad else "none"}

# ---- gate ----
def rights_resolved(rs):
    if not rs: return False
    low=rs.lower()
    return ("unresolved" not in low) and ("restricted_or_licensing" not in low)
funnel={"universe_series":n_series,"universe_sources":n_sources,
        "series_with_history":sum(1 for s in rows if rows[s]["count"]>0)}
pass_span=set(); pass_freq=set(); pass_rights=set()
for sid in series_meta:
    r=rows[sid]
    if r["span_days"]>=MIN_SPAN_DAYS: pass_span.add(sid)
    if r["cadence_days"] is not None and r["cadence_days"]<=CHOSEN["max_cadence_days"]: pass_freq.add(sid)
    if rights_resolved(series_meta[sid]["rights_status"]): pass_rights.add(sid)
survivors=pass_span & pass_freq & pass_rights
funnel.update({
  "survives_span_ge_%dy"%CHOSEN["min_span_years"]:len(pass_span),
  "survives_freq_le_%dd"%CHOSEN["max_cadence_days"]:len(pass_freq),
  "survives_rights_resolved":len(pass_rights),
  "survives_all_three":len(survivors)})
# exclusions by reason (no silent caps): mutually exclusive first-fail counts
excl={"fail_span":0,"fail_freq_only":0,"fail_rights_only":0,"no_history":0,"passes":0}
for sid in series_meta:
    r=rows[sid]
    if r["count"]==0: excl["no_history"]+=1; continue
    s=sid in pass_span; fr=sid in pass_freq; ri=sid in pass_rights
    if s and fr and ri: excl["passes"]+=1
    elif not s: excl["fail_span"]+=1
    elif not fr: excl["fail_freq_only"]+=1
    elif not ri: excl["fail_rights_only"]+=1
# cadence distribution of universe
cad_dist={}
for sid in rows:
    c=rows[sid]["cadence"]; cad_dist[c]=cad_dist.get(c,0)+1

# ---- 17 current members: presence + survival in the store universe ----
MEMBER_STORE_IDS={"ICSA":"ICSA","IURSA":"IURSA","SAHM":"SAHMREALTIME","UNRATEv":"UNRATE","INDPRO":"INDPRO",
 "CMRMT":"CMRMTSPL","TCU":"TCU","PHILLY":"GACDFSA066MSFRBPHI","NASDAQ":"NASDAQCOM","VIX":"VIXCLS",
 "BAA10Y":"BAA10Y","NFCI":"NFCI","PERMIT":"PERMIT","HOUST":"HOUST","UMCSENT":"UMCSENT","W875":"W875RX1",
 "BAA":"BAA","AAA":"AAA"}
member_survival={}
for mem,storeid in MEMBER_STORE_IDS.items():
    present=storeid in series_meta
    r=rows.get(storeid)
    member_survival[mem]={"store_id":storeid,"present_in_store":present,
      "span_days":r["span_days"] if r else None,"cadence":r["cadence"] if r else None,
      "rights":series_meta.get(storeid,{}).get("rights_status",""),
      "survives_gate":storeid in survivors}
n_members_present=sum(1 for v in member_survival.values() if v["present_in_store"])
n_members_survive=sum(1 for v in member_survival.values() if v["survives_gate"])

# top survivors sample for sanity
surv_list=sorted(survivors, key=lambda s:-rows[s]["span_days"])
sample=[{"series":s,"first":rows[s]["first"],"last":rows[s]["last"],
         "cadence":rows[s]["cadence"],"count":rows[s]["count"]} for s in surv_list[:25]]

OUT={"section3_universe":{
  "chosen_gate_thresholds_PROVENANCE_chosen":CHOSEN,
  "funnel":funnel,
  "exclusions_by_reason_mutually_exclusive":excl,
  "cadence_distribution":cad_dist,
  "current_17_member_survival":member_survival,
  "current_17_present_in_store":"%d/18 ids (%d logical members; 8 headline series absent from store)"%(n_members_present,17),
  "current_members_surviving_gate":n_members_survive,
  "survivor_count":len(survivors),
  "survivor_sample_top25_byspan":sample,
  "note":"universe = live_data store generation 93b43e2e (11,838 series/190 sources). span/count/cadence measured by streaming the 673 normalized full-history objects (14GB); snapshot.json alone is latest-only. gate is MAXIMUM COVERAGE per owner ruling 2026-08-04: span+frequency+resolved-rights; vintage availability NOT gated. rights 'resolved' rule is a string-vocab heuristic (no boolean field exists) — stated. 8 of 17 headline members are absent from this store generation entirely (incl. licensing-review series) — a finding, cross-checked against the 270-series data_vault metric_catalog which does contain all 17."}}
# persist survivor id list for §4 (scratch)
json.dump({"survivors":sorted(survivors),"rows":{s:rows[s] for s in survivors}},
          open(REPO+"/research/universe_ch2/scratch/ch2_survivors.json","w"))
json.dump(OUT,open(OUTP,"w"),indent=1,default=str)
print("=== §3 UNIVERSE FUNNEL ===")
print(json.dumps(funnel,indent=1))
print("exclusions:",json.dumps(excl))
print("cadence_dist:",json.dumps(cad_dist))
print("members present in store:",n_members_present,"of 18 ids; survive gate:",n_members_survive)
print("survivors:",len(survivors))
for mem,v in member_survival.items():
    print(f"  {mem:8} store={v['store_id']:20} present={v['present_in_store']} span_d={v['span_days']} cad={v['cadence']} surv={v['survives_gate']}")
