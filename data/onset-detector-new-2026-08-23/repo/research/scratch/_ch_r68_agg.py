#!/usr/bin/env python3
"""CH-R68 pass 2 — aggregate per-group stats into defect list + summary.
Reads research/_ch_r68_groups.jsonl. No store writes."""
import json, collections, csv, re

GROUPS="research/_ch_r68_groups.jsonl"
defects=[]   # dicts: class,severity,series,mode,source,detail,evidence
file_errs=[]

# domain sanity rules keyed by substring of series_id (case-insensitive)
# (lo,hi) plausible bounds; None = unbounded
def domain_bounds(sid):
    s=sid.upper()
    # unemployment / participation / rates in percent 0..100
    for t in ("UNRATE","U6RATE","CIVPART","EMRATIO","IURSA","IC4WSA"):
        if t in s: return ("pct",0,100)
    if s.startswith("SAHM") or "SAHM" in s: return ("pp",-5,25)   # sahm gap, percentage points
    if "NFCI" in s or "STLFSI" in s or "ANFCI" in s: return ("fci",-10,25)
    return (None,None,None)

freq_lbl={1:"D",7:"W",30:"M",31:"M",28:"M",29:"M",90:"Q",91:"Q",92:"Q",89:"Q",365:"A",366:"A",364:"A"}

nrec=0; ngroups=0
series_modes=collections.Counter()
maxdec_hist=collections.Counter()
future_groups=0; dup_groups=0; nonmono_groups=0; artifact_groups=0; impossible_groups=0
freq_counter=collections.Counter()

with open(GROUPS) as f:
    for line in f:
        g=json.loads(line)
        if "file_error" in g: file_errs.append(g); continue
        ngroups+=1; nrec+=g["n"]
        sid=g["series"]; mode=g["mode"]; src=g["source"]
        series_modes[(sid,mode)]+=1
        maxdec_hist[min(g["maxdec"],18)]+=1
        # frequency inference from modal gap
        modal=None
        if g["gaps"]:
            modal=g["gaps"][0][0]
        fl=freq_lbl.get(modal,None) if modal is not None else None
        if fl: freq_counter[fl]+=1
        # --- hard defects ---
        if g["dup"]>0:
            dup_groups+=1
            defects.append(dict(cls="duplicate_period",sev="HIGH",series=sid,mode=mode,source=src,
                detail=f"{g['dup']} duplicate observation_period(s) in group",n=g["dup"],
                evidence=f"vintage={g['vintage']} n={g['n']} range={g['min']}..{g['max']}"))
        if g["nonmono"]>0:
            nonmono_groups+=1
            defects.append(dict(cls="nonmonotonic_date",sev="MED",series=sid,mode=mode,source=src,
                detail=f"{g['nonmono']} out-of-order (descending) date step(s)",n=g["nonmono"],
                evidence=f"vintage={g['vintage']} range={g['min']}..{g['max']}"))
        if g["future"]>0:
            future_groups+=1
            defects.append(dict(cls="future_dated_obs",sev="HIGH",series=sid,mode=mode,source=src,
                detail=f"{g['future']} observation(s) dated after 2026-08-06",n=g["future"],
                evidence=f"vintage={g['vintage']} max={g['max']}"))
        if g["nbad"]>0:
            artifact_groups+=1
            defects.append(dict(cls="float_roundtrip_artifact",sev="MED",series=sid,mode=mode,source=src,
                detail=f"{g['nbad']} value(s) show float round-trip artifact (…99999/…000000 tail)",n=g["nbad"],
                evidence=f"vintage={g['vintage']} maxdec={g['maxdec']}"))
        # --- domain impossible values ---
        kind,lo,hi=domain_bounds(sid)
        if kind and g["vmin"] is not None:
            bad=[]
            if g["vmin"]<lo: bad.append(f"min={g['vmin']}<{lo}")
            if g["vmax"]>hi: bad.append(f"max={g['vmax']}>{hi}")
            if bad:
                impossible_groups+=1
                defects.append(dict(cls="out_of_domain_value",sev="HIGH",series=sid,mode=mode,source=src,
                    detail=f"{kind} series value outside plausible [{lo},{hi}]: "+", ".join(bad),n=1,
                    evidence=f"vintage={g['vintage']} vmin={g['vmin']} vmax={g['vmax']} units={g['units']}"))

summary=dict(
    total_groups=ngroups, total_records=nrec, distinct_series_mode=len(series_modes),
    file_errors=file_errs,
    maxdec_histogram={str(k):v for k,v in sorted(maxdec_hist.items())},
    inferred_frequency_counts=dict(freq_counter),
    groups_with_duplicate_period=dup_groups,
    groups_with_nonmonotonic_date=nonmono_groups,
    groups_with_future_dates=future_groups,
    groups_with_float_artifact=artifact_groups,
    groups_with_out_of_domain=impossible_groups,
    total_defect_rows=len(defects),
)
json.dump(summary, open("research/_ch_r68_agg_summary.json","w"), indent=1)
# write defects csv
with open("research/_ch_r68_defects_partial.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["cls","sev","series","mode","source","n","detail","evidence"])
    w.writeheader()
    for d in defects: w.writerow(d)
print(json.dumps(summary,indent=1))
