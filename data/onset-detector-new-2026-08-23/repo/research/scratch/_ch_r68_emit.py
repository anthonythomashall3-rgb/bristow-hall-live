#!/usr/bin/env python3
"""CH-R68 final emit: accuracy_defects_v1.csv + accuracy_reconciliation_v1.json. Read-only."""
import json, collections, csv

FC_TOK=("SPF","GDPNOW","ATSIX","RECPRO","ANXIOUS","GREENBOOK","LIVINGSTON","NOWCAST","FORECAST","SEP_")
def is_fc(sid,mode):
    if mode=="substituted_diagnostic": return True
    s=sid.upper(); return any(t in s for t in FC_TOK)

rows=[]
fp_series=collections.Counter(); pad_series=set(); miss_series=set()
raw_series=set(); mixed=[]; tot=collections.Counter()
fut_treasury=0; fut_other=0; nonmono=0
fp_examples={}
for line in open("research/_ch_r68_groups2.jsonl"):
    g=json.loads(line)
    if "file_error" in g: continue
    tot["groups"]+=1; tot["records"]+=g["n"]
    sid=g["series"]; mode=g["mode"]; src=g["source"]; md=g["maxdec"]
    ks=g.get("kinds",[])
    # D1 float precision noise
    if md>=13:
        fp_series[sid]+=1
        rows.append(("float_precision_noise","MED",sid,mode,src,1,
            f"value carries {md} decimal places — float round-trip suspected (publisher-native float not excluded)",
            f"vintage={g['vintage']} maxdec={md} vmin={g['vmin']} vmax={g['vmax']}"))
        fp_examples.setdefault(sid.split('.')[0],(sid,md))
    # D2 padding
    elif g.get("nbad",0)>0:
        pad_series.add(sid)
        rows.append(("false_precision_padding","LOW",sid,mode,src,g["nbad"],
            "trailing-zero / fixed-width float repr — value exact but publisher decimal string not preserved; `decimals` untracked",
            f"vintage={g['vintage']} maxdec={md}"))
    # D3 missing period (M/Q only)
    if ks==["M"] or ks==["Q"]:
        ndist=g["n"]-g.get("unparsed",0)-g.get("ndup",0); mk,xk=g.get("minkey"),g.get("maxkey")
        if mk is not None:
            miss=(xk-mk+1)-ndist
            if miss>0:
                miss_series.add(sid)
                rows.append(("missing_period_gap","LOW",sid,mode,src,miss,
                    f"{ks[0]} series missing {miss} interior period(s) vs contiguous grid",
                    f"vintage={g['vintage']} span={g['minlbl']}..{g['maxlbl']}"))
    # D4 null-period raw capture
    if g.get("unparsed",0)>0:
        raw_series.add(sid)
        rows.append(("null_period_raw_capture","LOW",sid,mode,src,g["unparsed"],
            "observation_period null/unparsed — landing raw_capture placeholder, carries no usable observation",
            f"vintage={g['vintage']}"))
    # triage counters (non-defects)
    if g.get("future",0)>0:
        if "TREASURY.AUCTION" in sid: fut_treasury+=1
        elif is_fc(sid,mode): pass
        else: fut_other+=1

# mixed-kind from formats file
fmt=json.load(open("research/_ch_r68_formats.json"))
for sid in fmt.get("mixed_examples",{}):
    rows.append(("mixed_period_kind","LOW",sid,"(multi)","(nber_macrohistory)",1,
        "series carries >1 period granularity (e.g. monthly + annual) — layout parse anomaly",
        "see research/_ch_r68_formats.json"))

# ---- write CSV ----
order={"HIGH":0,"MED":1,"LOW":2}
rows.sort(key=lambda r:(order[r[1]],r[0],r[2]))
with open("research/accuracy_defects_v1.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["defect_class","severity","series_id","mode","source_id","count","what_is_wrong","evidence"])
    for r in rows: w.writerow(r)

# ---- reconciliation JSON ----
summary={
 "batch":"CH-R68_ACCURACY_RECONCILIATION",
 "scope":"read-only, offline, no store/catalog/ledger writes, no network",
 "store_census":{"normalized_files":901,"records":tot["records"],"groups_series_vintage_mode":tot["groups"],
    "distinct_series_id":17115,"distinct_source_id":319,
    "modes":{"current_revised":7643845,"archive_snapshot_asof":8735905,"substituted_diagnostic":148789},
    "record_period_kinds":fmt["record_period_kinds"]},
 "headline":"sha256 integrity is intact but does not certify accuracy. No value corruption or impossible values found in the checkable set. The one systemic, real finding is a precision-representation defect: the ingestion path does NOT uniformly preserve the publisher's decimal string — some adapters serialize Python floats, producing both 13-20dp float-noise tails (58 series) and trailing-zero padding (575 series). Values remain numerically correct for macro magnitudes; the defect is false/lost precision and an untracked `decimals` field.",
 "defect_classes":{
   "float_precision_noise":{"severity":"MED","groups":143,"distinct_series":len(fp_series),
     "families":["CFPB.CCT (39)","OFR.FSI (9)","CLEVELAND.INFLATION_NOWCAST (8)","SPF_ANXIOUS_INDEX (1)"],
     "worst_example":"CLEVELAND.INFLATION_NOWCAST.CPI.NOWCAST 2017-04-01 = '-0.240131159996015' (15 dp)",
     "note":"these are derived/nowcast/index outputs; publisher-native float precision is NOT excluded — resolvable by parsing the stored source_bytes (offline follow-up), not by hash."},
   "false_precision_padding":{"severity":"LOW","groups":621,"distinct_series":len(pad_series),
     "examples":["DTB3 '3.7300000000' (2dp published, 10dp stored)","W875RX1","M2SL","CLAIMSx.DEEPASOF* vintages"],
     "note":"value exact; trailing zeros imply false precision and confirm the parse drops the publisher decimal string."},
   "missing_period_gap":{"severity":"LOW","distinct_series":sorted(miss_series),
     "note":"1-month interior gap 2024-01..2026-06, replicated across vintages; publisher non-publication vs ingest drop UNRESOLVED offline."},
   "null_period_raw_capture":{"severity":"LOW","distinct_series":sorted(raw_series),
     "note":"raw_capture landing placeholders with null observation_period; not real observations — should not be counted as series."},
   "mixed_period_kind":{"severity":"LOW","series":list(fmt.get("mixed_examples",{}).keys()),
     "note":"single NBER macrohistory series mixes granularities — layout parse anomaly."}
 },
 "triaged_NOT_defects":{
   "duplicate_periods":"ZERO across all 52,452 groups (clean).",
   "out_of_domain_values":"ZERO for bounded-domain series (UNRATE/participation/SAHM/NFCI etc. all within plausible ranges).",
   "descending_storage_order":"7,231 current_revised groups store observations newest-first; storage order not guaranteed ascending. NOT corruption but a real CONSUMER HAZARD — any code assuming sorted order must sort first.",
   "future_dated_treasury_auctions":f"{fut_treasury} groups dated up to 2026-08-13 with value=None — announced/scheduled auctions, legitimate forward-dating, not measurement corruption.",
   "between_series_format_heterogeneity":"period format varies by frequency (D/M/Q) across series but is internally consistent within each series (only 1 truly mixed series). Expected, not a defect.",
   "future_dated_non_treasury_measurement":fut_other
 },
 "what_the_tests_could_NOT_detect":[
   "ACCURACY vs publisher: a wrong-but-plausible value (stale vintage silently substituted, wrong unit multiplier that is internally consistent) is INVISIBLE offline — requires a networked re-fetch / second channel (a separate later batch, per the brief).",
   "CROSS-SOURCE value reconciliation: measured 0 series_ids carry two independently-acquired source copies — the store assigns each series_id a single owning source_id by design. The only same-quantity overlaps are (a) alias pairs deliberately kept as DISTINCT non-asserted identities (CLAIMSx vs ICSA, native vs FRED-MD W875RX1 — the identity wall of CH-R42 / B-LAND-3C, out of scope for a read-only probe), (b) vintage vs current (revisions legitimately differ), (c) forecast vs actual (differ by nature). No clean exact-duplicate copy exists to diff.",
   "Vintage FROZEN-INVARIANT (methodology Tier-1 #1): not run — needs a capture-time snapshot to diff current bytes against; recommended follow-up.",
   "DAILY calendar completeness: skipped — a business-day/holiday calendar is required; a naive min-step grid produced 194M phantom gaps and was discarded. Only M/Q completeness is reported.",
   "UNIT/SCALE errors beyond bounded-domain series: catalog units are 257/268 'unresolved', so there is no authoritative expected-unit to assert against for most series.",
   "Whether float_precision_noise is OUR round-trip vs the PUBLISHER's native float — needs source_bytes parse."
 ],
 "recommended_followups":[
   "PRECISION FIX: make adapters carry the publisher decimal string + a `decimals` field; stop float→str serialization (methodology checklist #3/#17). Highest value; fixes both float_precision_noise and false_precision_padding at the root.",
   "NETWORK double-capture batch: re-fetch a rotating sample + 100% of the 58 float-noise series through a second channel and compare decimal strings (methodology #7).",
   "VINTAGE frozen-invariant test in the nightly (methodology Tier-1 #1).",
   "Triage the 2 BLS EIUIQ/EIUIR monthly gaps against the publisher release calendar.",
   "Add an ascending-order (or sort-on-read) guarantee, or document newest-first as the contract."
 ],
 "defect_csv":"research/accuracy_defects_v1.csv",
 "total_defect_rows":len(rows),
 "defect_row_counts_by_class":dict(collections.Counter(r[0] for r in rows)),
}
json.dump(summary,open("research/accuracy_reconciliation_v1.json","w"),indent=1)
print("defect rows",len(rows),"classes",summary["defect_row_counts_by_class"])
print("fp_series",len(fp_series),"pad_series",len(pad_series))
