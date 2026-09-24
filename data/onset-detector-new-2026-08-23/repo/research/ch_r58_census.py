#!/usr/bin/env python3
"""CH-R58 — REAL-TIME CHANNEL EXPANSION CENSUS (window 3, read-only, §20-class).
Reuses CH3-R2's matrix build (research/ch3_factor.py) WITHOUT clobbering its v1 outputs:
we exec only the head of that script (up to the full-solution eig_counts call), capturing
X (288x121 transformed matrix), kept (base order), meta, eig_counts(). Then classifies every
base by real-time route a/b/c/d, scores channel diversity, and simulates Horn/Kaiser as the
instrumentable set is expanded. Outputs research/ only. No store/catalog/network."""
import json, csv, re
import numpy as np
np.random.seed(20260806)
REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"

# ---- 1. reproduce CH3-R2 matrix by exec'ing the head of ch3_factor.py (no output clobber) ----
src=open(REPO+"/research/ch3_factor.py").read()
marker='full_counts, ev_full, Xs_full = eig_counts(X,label="full")'
head=src[:src.index(marker)+len(marker)]
ns={}
exec(compile(head,"ch3_head","exec"),ns)
X=ns["X"]; kept=ns["kept"]; meta=ns["meta"]; eig_counts=ns["eig_counts"]
full_counts=ns["full_counts"]; VINT_BASES=ns["VINT_BASES"]
pos={b:i for i,b in enumerate(kept)}
NB=len(kept)
assert X.shape[1]==NB
print(f"[repro] kept={NB} obs={X.shape[0]} FULL Horn/Kaiser={full_counts['horn_parallel_95']}/{full_counts['kaiser_eig_over1']}")

# ---- 2. factor loadings per base from CH3-R2 CSV (top_factor + load_f0..f7) ----
loadrows={r["base"]:r for r in csv.DictReader(open(REPO+"/research/ch3_factor_structure_v1.csv"))}
NF=8
def loads(b):
    r=loadrows[b]; return [float(r[f"load_f{j}"]) for j in range(NF)]
def topf(b): return int(loadrows[b]["top_factor"])

# ---- 3. never/negligible-revised certification (route b: no vintage lane needed) ----
NEVER_CLASSES={"never_revised","negligible_revision"}
neverrev_bases=set()
r25={}
for r in csv.DictReader(open(REPO+"/research/revision_certification_v2_roster.csv")):
    base=r["series_id"].split(".")[0]
    r25.setdefault(base,r["class_r25"])
    if r["class_r25"] in NEVER_CLASSES: neverrev_bases.add(base)
# R26 survey adds daily-block never-revised by fred_id
r26={}; r26_rights={}
for r in csv.DictReader(open(REPO+"/research/hf_universe_survey_v1.csv")):
    fid=r["fred_id"].strip()
    if not fid: continue
    r26[fid]=r["revision_class"]; r26_rights[fid]=r["rights_rung"]
    if r["revision_class"] in ("never-revised","never/negligible","negligible-revised") and r["rights_rung"] in ("public","public_index","public_index_truncated"):
        neverrev_bases.add(fid)
# rights-blocked (route d) fred_ids
rightsblocked={fid for fid,rung in r26_rights.items() if rung.startswith(("PROPRIETARY","LICENSED","MIXED"))}

# ---- 4. cached-bytes route a: RTDSM 118 vars (Philly Fed real-time), FRED-MD, ALFRED roster ----
rtdsm=[m["var"] for m in json.load(open(REPO+"/research/_ch_r39_model.json"))]
rtdsm_up={v.upper() for v in rtdsm}
alfred_cached={r["series_id"].split(".")[0] for r in csv.DictReader(open(REPO+"/research/revision_certification_v2_roster.csv"))}

# ---- 5. classify every one of the 121 bases ----
covered_factors=sorted({topf(b) for b in kept if b in VINT_BASES})  # factors the 18 lanes already cover
rows=[]
for b in kept:
    lane = b in VINT_BASES
    cls25=r25.get(b,"")
    nrev = b in neverrev_bases
    if lane:
        route="LANE_EXISTS"; note="already a real-time channel (has archive_snapshot_asof lane)"; depth="see deep_vintage_window"
    elif nrev:
        route="b_never_revised"; note="real-time BY CONSTRUCTION; needs NO vintage lane"; depth="full current_revised history"
    elif b in rtdsm_up:
        route="a_cached_rtdsm"; note="Philly Fed real-time vintages cached (CH-R24)"; depth="RTDSM vintage span"
    elif b in alfred_cached and cls25 in ("moderately_revised","heavily_revised","rebasing_artifact","no_overlap"):
        route="c_alfred_obtainable"; note=f"revised ({cls25}); ALFRED vintage lane obtainable (route known, public)"; depth="ALFRED vintage floor"
    elif b in rightsblocked:
        route="d_rights_blocked"; note="proprietary/licensed"; depth="n/a"
    else:
        route="c_alfred_obtainable"; note="FRED current_revised; ALFRED lane obtainable, revision unverified"; depth="ALFRED vintage floor"
    tf=topf(b); ld=loads(b)
    uncovered = tf not in covered_factors
    # diversity score: 1.0 if top-loads an uncovered factor, else max |load| on any uncovered factor
    unc_load=max((abs(ld[j]) for j in range(NF) if j not in covered_factors), default=0.0)
    div = 1.0+unc_load if uncovered else unc_load
    rows.append({"base":b,"rep_series":loadrows[b]["rep_series"],"lane_status":("has_lane" if lane else "no_lane"),
        "route_class":route,"cost_note":note,"depth_reachable":depth,"revision_class_r25":cls25,
        "top_factor":tf,"top_factor_uncovered_by_lanes":uncovered,"max_uncovered_loading":round(unc_load,3),
        "diversity_score":round(div,3),
        **{f"load_f{j}":ld[j] for j in range(NF)}})

# ---- 6. write census CSV ----
cols=["base","rep_series","lane_status","route_class","cost_note","depth_reachable","revision_class_r25",
      "top_factor","top_factor_uncovered_by_lanes","max_uncovered_loading","diversity_score"]+[f"load_f{j}" for j in range(NF)]
with open(REPO+"/research/realtime_expansion_census_v1.csv","w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader()
    for r in sorted(rows,key=lambda x:(-x["diversity_score"],x["base"])): w.writerow(r)

# ---- 7. simulation: Horn/Kaiser as instrumentable set is expanded ----
inst=[b for b in kept if b in VINT_BASES]                       # 18 lane bases
def counts(cols_bases):
    idx=[pos[b] for b in cols_bases]
    return eig_counts(X[:,idx])[0]
def brief(c): return {"n_series":c["n_series"],"horn":c["horn_parallel_95"],"kaiser":c["kaiser_eig_over1"],"elbow":c["scree_elbow"]}

# route-b candidates in universe, not already lane, ranked by diversity
cand_b=[r for r in rows if r["route_class"]=="b_never_revised"]
cand_b.sort(key=lambda x:-x["diversity_score"])
cand_b_bases=[c["base"] for c in cand_b]

steps=[]
steps.append(("baseline_18_lanes", brief(counts(inst)), inst[:]))
for k in (5,10):
    add=cand_b_bases[:k]
    steps.append((f"+top{k}_neverrevised", brief(counts(inst+add)), add))
steps.append((f"+all_neverrevised({len(cand_b_bases)})", brief(counts(inst+cand_b_bases)), cand_b_bases))
# top-20 combined program = 18 lanes + top-20 diversity candidates that ARE PCA-simulable
# (route b only; route a/c bases have no data column in this universe — flagged as unsimulable)
simulable=[r["base"] for r in sorted(rows,key=lambda x:-x["diversity_score"])
           if r["route_class"]=="b_never_revised"][:20]
steps.append((f"+top20_combined_simulable({len(simulable)})", brief(counts(inst+simulable)), simulable))
steps.append(("full_121_ceiling", brief(counts(kept)), "ALL"))

# incremental greedy trajectory over never-revised (add one at a time, report every add)
traj=[]
cur=inst[:]
traj.append({"n_added":0,"set":"18_lanes",**brief(counts(cur))})
for i,b in enumerate(cand_b_bases,1):
    cur=cur+[b]
    c=brief(counts(cur)); traj.append({"n_added":i,"added":b,"top_factor":topf(b),**c})

# ---- route-class tallies ----
from collections import Counter
route_tally=Counter(r["route_class"] for r in rows)

sim={
 "CH_R58_realtime_expansion_simulation":{
  "problem":"real-time monitor is starved by vintage-lane coverage, not economics. Count reachable channels and cost.",
  "matrix":{"n_bases_universe":NB,"n_obs":int(X.shape[0]),"window":"2000-01..2024-12 monthly, 288 rows"},
  "full_universe_ref":{"horn":full_counts["horn_parallel_95"],"kaiser":full_counts["kaiser_eig_over1"],"elbow":full_counts["scree_elbow"],
      "note":"CH3-R2 ceiling on all 121 bases (uses revised data -> NOT real-time attainable)."},
  "instrumentable_baseline":{"n_lane_bases":len(inst),"bases":inst,"covered_factors":covered_factors},
  "route_class_tally":dict(route_tally),
  "route_legend":{"LANE_EXISTS":"already instrumented (18)","b_never_revised":"needs NO lane, real-time by construction (cheapest)",
      "a_cached_rtdsm":"Philly Fed real-time bytes already cached","c_alfred_obtainable":"revised; ALFRED lane obtainable (public route)",
      "d_rights_blocked":"proprietary/licensed"},
  "expansion_steps":[{"step":s,"result":r,"added_bases":(a if a=="ALL" else a)} for s,r,a in steps],
  "greedy_neverrevised_trajectory":traj,
  "n_neverrevised_in_universe_not_yet_counted":len(cand_b_bases),
  "reconciliation_rtdsm_vs_diversity":{
     "rtdsm_vars_cached":len(rtdsm),
     "finding":"RTDSM 118 vars are Philly Fed real-time NIPA vintages (routput/rcon/rinv/... = GDP output components) plus a few (ADS index, ATSIX inflation-expectations). CH-R39 ranked them by value-per-cost. On CHANNEL DIVERSITY they cluster on the already-covered output/GDP factor (INDPRO/GDPC1/CMRMT territory), so most buy little NEW channel. Where CH-R39's value-per-cost ranking and diversity disagree, diversity is the right criterion for THIS question (owner asked for distinct channels, not more series). RTDSM's diversity payoff is bounded because its variables are collinear NIPA aggregates.",
     "caveat":"RTDSM/route-a/route-c bases have NO current_revised data column in the 121-base universe, so they are NOT PCA-simulable here without landing. The simulation therefore quantifies the ROUTE-B (never-revised, zero-cost) frontier exactly, and treats route-a/c as a qualitative upper bound."},
  "NO_ADOPTION":"reachable-frontier measurement only. S2 owner sitting selects members/channels; it is ON HOLD by owner order. No channel selected here."}}
json.dump(sim,open(REPO+"/research/realtime_expansion_simulation_v1.json","w"),indent=1,default=str)

print("[census] route tally:",dict(route_tally))
print("[sim] steps:")
for s,r,a in steps: print(f"   {s:38s} n={r['n_series']:3d} Horn={r['horn']} Kaiser={r['kaiser']} elbow={r['elbow']}")
print(f"[sim] never-revised-in-universe not yet counted: {len(cand_b_bases)}")
# find plateau
hk=[(t['n_added'],t['horn'],t['kaiser']) for t in traj]
print("[sim] greedy Horn trajectory (n_added,horn):",[(n,h) for n,h,k in hk])
print("DONE ch_r58_census")
