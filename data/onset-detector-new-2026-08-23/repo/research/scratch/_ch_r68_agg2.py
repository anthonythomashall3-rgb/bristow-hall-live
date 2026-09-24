#!/usr/bin/env python3
"""CH-R68 pass 2b — final defect synthesis from groups2.jsonl. Read-only."""
import json, collections, csv

FC_TOK=("SPF","GDPNOW","ATSIX","RECPRO","ANXIOUS","GREENBOOK","LIVINGSTON","NOWCAST","FORECAST","SEP_","_FORECAST")
def _is_forecast(sid,mode):
    if mode=="substituted_diagnostic": return True
    s=sid.upper()
    return any(t in s for t in FC_TOK)

defects=[]
tot=collections.Counter()
maxdec_hist=collections.Counter()
fut_forecast=0; fut_measure=0
miss_groups=0; miss_records=0
dup_groups=0
hi_prec_groups=0  # maxdec>=13 == suspected float corruption
pad_groups=0      # nbad (trailing-zero/9run) but low maxdec == fixed-width padding
unparsed_groups=0; unparsed_recs=0
fut_measure_series=collections.Counter()

for line in open("research/_ch_r68_groups2.jsonl"):
    g=json.loads(line)
    if "file_error" in g: continue
    tot["groups"]+=1; tot["records"]+=g["n"]
    md=g["maxdec"]; maxdec_hist[min(md,18)]+=1
    sid=g["series"]; mode=g["mode"]; src=g["source"]
    # duplicates (should be ~0)
    if g.get("ndup",0)>0:
        dup_groups+=1
        defects.append(dict(cls="duplicate_period",sev="HIGH",series=sid,mode=mode,source=src,
            n=g["ndup"],detail="duplicate observation_period within group",
            evidence=f"vintage={g['vintage']} n={g['n']}"))
    # unparsed period labels
    if g.get("unparsed",0)>0:
        unparsed_groups+=1; unparsed_recs+=g["unparsed"]
        defects.append(dict(cls="unparsed_period_label",sev="MED",series=sid,mode=mode,source=src,
            n=g["unparsed"],detail="observation_period not ISO date / YYYY-MM / YYYY-Qn / YYYY",
            evidence=f"vintage={g['vintage']}"))
    # missing periods — RELIABLE only for M/Q (regular calendars); daily skipped
    # (business-day/holiday calendar makes offline daily completeness non-computable).
    kinds=g.get("kinds",[])
    if kinds==["M"] or kinds==["Q"]:
        mk,xk=g.get("minkey"),g.get("maxkey")
        ndist=g["n"]-g.get("unparsed",0)-g.get("ndup",0)
        if mk is not None and xk is not None:
            expected=xk-mk+1
            miss=expected-ndist
            if miss>0:
                miss_groups+=1; miss_records+=miss
                defects.append(dict(cls="missing_period_gap",sev="LOW",series=sid,mode=mode,source=src,
                    n=miss,detail=f"{kinds[0]} series missing {miss} period(s) in span (expected {expected}, have {ndist})",
                    evidence=f"vintage={g['vintage']} span={g['minlbl']}..{g['maxlbl']}"))
    # future-dated obs, split forecast vs measurement
    if g.get("future",0)>0:
        if g.get("fc") or _is_forecast(sid,mode):
            fut_forecast+=1
        else:
            fut_measure+=1; fut_measure_series[sid]+=g["future"]
            defects.append(dict(cls="future_dated_measurement",sev="HIGH",series=sid,mode=mode,source=src,
                n=g["future"],detail="measurement (non-forecast) obs dated after 2026-08-06",
                evidence=f"vintage={g['vintage']} maxlbl={g['maxlbl']}"))
    # precision
    if md>=13:
        hi_prec_groups+=1
        defects.append(dict(cls="suspected_float_precision",sev="MED",series=sid,mode=mode,source=src,
            n=1,detail=f"stored value carries {md} decimal places (float round-trip suspected)",
            evidence=f"vintage={g['vintage']} maxdec={md} vmin={g['vmin']} vmax={g['vmax']}"))
    elif g.get("nbad",0)>0:
        pad_groups+=1  # fixed-width zero/9 padding, harmless-value but false precision

summary=dict(
    totals=dict(tot),
    maxdec_histogram={str(k):v for k,v in sorted(maxdec_hist.items())},
    duplicate_period_groups=dup_groups,
    unparsed_period_groups=unparsed_groups, unparsed_records=unparsed_recs,
    missing_period_groups=miss_groups, missing_period_est_records=miss_records,
    future_forecast_groups=fut_forecast,
    future_measurement_groups=fut_measure,
    future_measurement_series=dict(fut_measure_series.most_common(30)),
    suspected_float_precision_groups=hi_prec_groups,
    fixed_width_padding_groups=pad_groups,
    total_defect_rows=len(defects),
    defect_class_counts=dict(collections.Counter(d["cls"] for d in defects)),
)
json.dump(summary,open("research/_ch_r68_final_summary.json","w"),indent=1)
with open("research/accuracy_defects_v1.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["cls","sev","series","mode","source","n","detail","evidence"])
    w.writeheader()
    for d in sorted(defects,key=lambda x:({"HIGH":0,"MED":1,"LOW":2}[x["sev"]],x["cls"],x["series"])):
        w.writerow(d)
print(json.dumps(summary,indent=1))
