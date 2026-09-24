#!/usr/bin/env python3
"""CH-R64 — endpoint-filter & lookahead-leak census of method_source/ (read-only).
Emits research/leak_audit_v1.csv + _v1.json. No store writes, no code edits, no network."""
import csv, json

# kind vocabulary:
#  FULLSAMPLE_STAT  = statistic computed over the whole record, applied to earlier dates
#  EXPOST_LABEL     = baseline membership decided by ex-post NBER (USRECD) labels
#  OUTCOME_EXCLUSION= window excluded because its *outcome* misbehaves (desired-2022 leak)
#  CHOSEN_PARAM     = module constant chosen/tuned on the full record, applied to all dates
#  FIT_PARAM        = parameter fit (OLS) on data later than its application date
#  SA_HIDDEN        = publisher seasonal-adjustment re-estimation embeds future data
#  FILTER_CLEAN     = trend/smoothing filter inspected and found CAUSAL (no lookahead)

R = []  # file,line,kind,description,estimated_magnitude,fixable,notes
def add(f,l,k,desc,mag,fix,notes=""): R.append(dict(
    file=f,line=l,kind=k,description=desc,estimated_magnitude=mag,fixable=fix,notes=notes))

# ---- A. full-sample statistics applied to earlier dates (the dominant real leak) ----
add("method_source/index_v1.py","130-133","FULLSAMPLE_STAT",
    "Per-member baseline MU/SD (mean,sd over ALL is_baseline days) z-scores EVERY date "
    "incl. 1976. mu/sd from the whole record leak into the earliest z-values.","HIGH","yes",
    "Fix = expanding-window standardization (alfred_replay.py:163-167 already does this as-of). "
    "CH-R59 measured direction: expanding vs full-sample ordering rho=0.976, one swap (1981-82/2001).")
add("method_source/index_v1.py","211-212","FULLSAMPLE_STAT",
    "exp_mu/exp_sd over the full daily line, then feeds the PUBLISHED 'sigma above expansion' "
    "severity table (peak-index ordering of the 7 episodes) L227-231.","HIGH","yes",
    "This is the headline severity-ordering number. Same expanding fix; ordering effect measured small.")
add("method_source/recpage_build.py","84-85","FULLSAMPLE_STAT",
    "lmu/lsd = full-sample mean/sd of the long 1957+ monthly line; SIG_L standardizes ALL "
    "dates to sigma units -> feeds recessions-page peak-sigma + damage grades.","HIGH","yes",
    "Same class as index_v1:130. L139 'baseline mean 0 by construction' follows from this leak.")
add("method_source/nowcast_harness.py","678-679","FULLSAMPLE_STAT",
    "EXP_MU_FINAL/EXP_SD_FINAL = mean/std of headline grid over all base_mask days; reused "
    "L680/740/840/877 to convert readings for every date.","MED-HIGH","yes",
    "Harness = validation/nowcast-eval feed; still full-sample. base_mask itself is EXPOST_LABEL (see A6).")

# ---- B. baseline membership from ex-post labels + outcome-guided exclusion ----
add("method_source/index_v1.py","116-117","OUTCOME_EXCLUSION",
    "EXCL excludes 2023-01..2025-06 as '2022-24 miss + aftermath (ambiguous)'. The exact "
    "window whose OUTCOME misbehaves is removed from the baseline -> outcome-guided calibration.","MED-HIGH","yes",
    "CLAUDE.md flags desired-2022 status as NOT construction evidence. Shifts exp_mu/exp_sd. "
    "Same EXCL duplicated at alfred_replay.py:138 and (via excluded_derived) census/watch.")
add("method_source/index_v1.py","114-122","EXPOST_LABEL",
    "is_baseline()/in_recession() use USRECD (NBER final dating, known only ex-post) to decide "
    "which days define the expansion baseline. Even in-sample the labels are hindsight.","MED","partial",
    "Inherent to any full-history baseline. Replicated recpage_build.isbase, census_build NBER windows, "
    "nowcast_harness base_mask (L677). Fix needs a real-time recession label or a label-free baseline.")

# ---- C. chosen constants tuned on the full record, applied to all dates (registry=inherited) ----
add("method_source/index_v1.py","156-161","CHOSEN_PARAM",
    "CHANNELS fixed weights 0.30/0.25/0.20/0.10/0.15 + membership. Chosen on full history, "
    "applied to every date. registry provenance=inherited; alias alfred_replay.py::CH.","HIGH","yes",
    "CH5: realized labor weight 0.75-0.80 vs nominal 0.30 -> weights do not describe the data they weight.")
add("method_source/watch_build.py","51,63,64","CHOSEN_PARAM",
    "Onset Watch sigma thresholds THR=1.0 (open), BAR=5.0 (confirm), REC_BAR=7.5 (detector). "
    "Set bar-crossings directly; chosen ex-post (DEC-023/026), registry=inherited.","HIGH","yes",
    "Pace gates G30/G60/G90 are DERIVED from BAR (L67-72, excluded_derived) -> NOT leaks.")
add("method_source/energy_build.py","34","CHOSEN_PARAM",
    "Detector BAR_E=7.5, RESET=2.0 gate the recession-detection upcross/re-arm on the full "
    "record. Chosen ex-post; registry=inherited.","HIGH","yes",
    "Header L29 asserts 'nothing tuned' but the level itself was selected against known episodes.")
add("method_source/watch_build.py","53,73","CHOSEN_PARAM",
    "DRAIN=1.5 (retired re-arm, still reported), FIZZLE_DAYS=45. Chosen constants.","LOW","yes","")
add("method_source/census_build.py","70,59","CHOSEN_PARAM",
    "CAT_FLOORS [5,8,11,14] + CAT_W=3.0 + FLOOR set the census damage-grade cut points; "
    "CUT/DAMAGE_CUTOFF/MAJOR_D derived from them (excluded_derived).","MED","yes",
    "Move severity-grade boundaries; chosen on the completed episode set.")
add("method_source/forecaster_site.py","94-117","CHOSEN_PARAM",
    "WARN_LANES thresholds + REGISTERED frozen AUC baselines (§57.3). Comment itself notes a "
    "band '6/6 at EVERY threshold 0.09-0.85' -> threshold read precision off an uncalibrated scale.","MED","yes",
    "Forecaster proper is expanding/training-only by design (good); these are the display constants.")

# ---- D. parameters fit on data later than application (edge only) ----
add("method_source/nowcast_live.py","B_*/BHAT_END","FIT_PARAM",
    "Frozen OLS bridge vectors (B_INDPRO/CMRMT/HOUST/PHILLY/UNRATE/W875) + BHAT_END revision-"
    "bias offsets, fit over the full sample (§57.4 'not re-derivable'), applied at the live edge.","LOW-MED","partial",
    "Only affects UNPUBLISHED months >= nowcast_from; published history byte-identical (index_v1:141-147). "
    "Z_CLIP=+/-0.5 bounds it. A genuine fit-leak but quarantined to the edge.")

# ---- E. seasonal-adjustment hidden as-of leak (CH-R44 fold-in) ----
add("(input series, all builds)","n/a","SA_HIDDEN",
    "13 SA-live members (ICSA,IURSA,UNRATE->UNRATEv,PAYEMS,HOUST,PERMIT,INDPRO,GDP-class...) carry "
    "FRED SA factors re-estimated annually -> each SA obs embeds later data. Enters labor/realactivity/"
    "housing channels.","MED","partial",
    "CH-R44 (sa_revision_audit_v1.csv): ICSA 33.7% obs revised, seasonal factors volatile. "
    "Fix = NSA + own frozen adjustment (CH-R44 rec, high acq priority); INDPRO/GDP %rev confounded by rebasing.")

# ---- F. filters inspected and found CAUSAL (recorded, NOT leaks) ----
add("method_source/watch_build.py","93-107","FILTER_CLEAN",
    "sm_d = trailing 21-day compressed mean; e12_d = trailing 365-day positive sum/30.44. "
    "Both strictly backward -> last obs uses only past. No lookahead.","NONE","n/a",
    "Endpoint effect = window truncation at series START only. This is the causal analogue of the "
    "HP-endpoint problem OvN warn about; the risk here migrated into the full-sample z-baseline (A1-A4).")
add("method_source/nowcast_live.py","53,301","FILTER_CLEAN",
    "Revision-bias b_hat(t) = EXPANDING mean over obs 24-120mo old, clipped +/-0.5. Expanding = "
    "uses only past obs at each t.","NONE","n/a","Applied only to NFCI's live edge.")
add("method_source/nowcast_harness.py","73-89","FILTER_CLEAN",
    "_window_extreme (drawdown peak over trailing 370d / min over look) is a trailing extremum.","NONE","n/a","")
add("method_source/index_v1.py,census/energy/recpage","(compress)","FILTER_CLEAN",
    "compress()/fourth-root testimony beyond 4-sigma is a per-value MONOTONE map, no cross-date "
    "coupling.","NONE","n/a","")
add("method_source/index_v1.py","56-95","FILTER_CLEAN",
    "yoy()/drawdown() transforms are per-observation vs own past (12mo / running peak). Causal.","NONE","n/a","")

# structural finding: NO HP filter / band-pass / two-sided smoother exists in method_source.
STRUCT = ("No HP filter, band-pass, or two-sided/centered smoother exists anywhere in method_source. "
          "The Orphanides-van Norden end-of-sample-trend risk did NOT enter as a filter; it re-appears "
          "as the FULL-SAMPLE z-baseline (rows A1-A4), which is the dominant lookahead leak in the "
          "published build. The as-of replay engine (alfred_replay.py:163-167) re-estimates the baseline "
          "expanding-only and is leak-free on rows A1-A4 -- so the leak is confined to the published "
          "index_v1/recpage/nowcast_harness path, exactly the gap CH-R28/CH-R59 exploited.")

for i,r in enumerate(R,1): r["id"]=f"L{i:02d}"

cols=["id","file","line","kind","description","estimated_magnitude","fixable","notes"]
with open("research/leak_audit_v1.csv","w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader()
    for r in R: w.writerow({c:r[c] for c in cols})

mag_rank={"HIGH":0,"MED-HIGH":1,"MED":2,"LOW-MED":3,"LOW":4,"NONE":5}
ranked=sorted([r for r in R if r["kind"]!="FILTER_CLEAN"],
              key=lambda r:mag_rank.get(r["estimated_magnitude"],9))
json.dump({
 "batch":"CH-R64_ENDPOINT_AND_LEAK_AUDIT","class":"read-only §20","scope":"method_source/ (+contrib feed)",
 "structural_finding":STRUCT,
 "kind_counts":{k:sum(1 for r in R if r["kind"]==k) for k in
    ["FULLSAMPLE_STAT","EXPOST_LABEL","OUTCOME_EXCLUSION","CHOSEN_PARAM","FIT_PARAM","SA_HIDDEN","FILTER_CLEAN"]},
 "registry_cross_ref":"all 37 parameter_registry.v1 entries provenance=inherited (unmeasured); "
    "the CHOSEN_PARAM/FIT_PARAM rows above are the subset that are ALSO lookahead leaks.",
 "leaks":R,
 "ranked_by_magnitude":[{"id":r["id"],"file":r["file"],"kind":r["kind"],
    "mag":r["estimated_magnitude"],"one_line":r["description"][:90]} for r in ranked],
 "do_not":"No fixes applied. S8 sitting decides expensive-to-fix/small-effect trade-offs.",
}, open("research/leak_audit_v1.json","w"), indent=2)

print("rows:",len(R),"| leaks:",len(ranked),"| clean-filters:",len(R)-len(ranked))
print("HIGH:",[r["id"]+" "+r["file"].split("/")[-1] for r in R if r["estimated_magnitude"]=="HIGH"])
