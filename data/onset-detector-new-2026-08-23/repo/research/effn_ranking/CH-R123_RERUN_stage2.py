#!/usr/bin/env python3
"""CH-R123 RE-RUN stage 2 -- disagreement set, drop list, recommendation block, on the
CYCLE-BAND (bk18_96_K12) metric. READ-ONLY, writes research/effn_ranking/ only. Derives nothing."""
import json
D = "/Users/anthonyhall/Projects/bristow-hall/repo/research/effn_ranking"
R125 = "/Users/anthonyhall/Projects/bristow-hall/repo/research/effn_cycle/CH-R125_summary.json"

cr = json.load(open(D + "/CH-R123_RERUN_cr_cycleband_LOO.json"))["loo"]      # 293 rows, name/delta
crd = {r["name"]: r["delta"] for r in cr}
r125 = json.load(open(R125))
rt = {x["lane"]: x["delta"] for x in r125["leave_one_out_by_filter"]["bk18_96_K12"]["lanes"]}
rt_raw = {x["lane"]: x["delta"] for x in r125["leave_one_out_by_filter"]["raw"]["lanes"]}

# ---- disagreement set: the 15 rt lanes, cr-cycle delta vs rt-cycle delta ----
disagree = []
for lane, rtd in sorted(rt.items(), key=lambda kv: kv[1], reverse=True):
    crv = crd.get(lane)                      # member17 labels match bare names
    row = {"lane": lane, "rt_cycle_delta": rtd, "cr_cycle_delta": crv}
    if crv is not None:
        row["sign_disagree"] = (rtd > 0) != (crv > 0)
    disagree.append(row)

# ---- drop list: MEASURED-negative in BOTH data-times (cr-cycle AND rt-cycle) ----
drop_both = [{"lane": l, "rt_cycle_delta": rt[l], "cr_cycle_delta": crd.get(l)}
             for l in rt if rt[l] < 0 and crd.get(l) is not None and crd[l] < 0]
# rt-only drags (drag in real time regardless of cr)
rt_drags = sorted([{"lane": l, "rt_cycle_delta": rt[l]} for l in rt if rt[l] < 0],
                  key=lambda r: r["rt_cycle_delta"])

# ---- sign-flips raw->cycle (the headline correction) ----
flips = [{"lane": s["lane"], "raw_delta": s["raw_delta"], "cycle_delta": s["cycle_delta"]}
         for s in r125["signflip_vs_CH_R122_raw_primary_bk18_96_K12"] if s["sign_flip"]]

# ---- recommendation block for the director (acquisition ordering, cycle-band) ----
# Axis map: which off-cluster axis each still-relevant queued acquisition feeds, + cycle-band evidence.
rec = {
 "principle": ("Rank acquisitions by cycle-band (18-96mo) marginal effN, NOT raw effN. Raw "
   "rewarded high-frequency-noise orthogonality (housing/financial lanes inflated); at the "
   "business-cycle band the binding contributors are SENTIMENT/EXPECTATIONS (UMCSENT rt +0.197, "
   "cr top axes FEDTARMDLR/GDPNOW/FX) and, newly, LABOR-LEVEL lanes (SAHM/PAYEMS flip drag->"
   "contributor). Adding MORE housing or output-side duplicates now measures as drag."),
 "cycleband_rt_contributors_desc": sorted([l for l in rt if rt[l] > 0], key=lambda l: -rt[l]),
 "cycleband_rt_drags_asc": [r["lane"] for r in rt_drags],
 "live_queue_verdicts": [
   {"batch": "B-ACQ-REALTIME-EXPECTATIONS", "status_in_DONE": "LIVE (no row)",
    "cycleband_verdict": "TOP PRIORITY. Expectations/sentiment is the #1 cycle-band axis "
      "(UMCSENT rt-LOO +0.197 highest of 15; cr top axis family FEDTARMDLR/GDPNOW). Off the "
      "labor/output cluster (CH-R122) AND real-time by construction. RE-CONFIRMED by cycle-band, "
      "not weakened.",
    "axis": "expectations/sentiment"},
   {"batch": "B-ACQ-FIRSTRELEASE / B-VINTAGE-RETAIN / B-ALFRED-NFCI_DEEP",
    "status_in_DONE": "STOP", "cycleband_verdict": "vintage-DEPTH lanes. Cycle-band does not "
      "penalize them (they add real-time reconstructable history, not a redundant cross-section). "
      "Director decides re-run; not re-ordered by this batch.", "axis": "vintage depth"},
   {"batch": "housing breadth (more HOUST/PERMIT-like series)",
    "status_in_DONE": "n/a", "cycleband_verdict": "DOWNGRADE. HOUST flips raw +0.199 -> cycle "
      "-0.026 (drag); PERMIT decays +0.207->+0.048. Housing looked orthogonal only via "
      "high-freq noise. Do NOT queue more housing breadth for effN.", "axis": "housing"},
 ],
 "caveat_late_run": ("Most W1 acquisition batches already COMPLETE/STOP in DONE.md; this "
   "recommendation is an ordering PRINCIPLE + verdicts on the live/near-term queue, not a fresh "
   "full PASTE_ORDER re-sort. Only B-ACQ-REALTIME-EXPECTATIONS is live."),
}

out = {
 "batch_id": "CH-R123_EFFN_MARGINAL_RANKING (RE-RUN, cycle-band) stage2",
 "metric": "bk18_96_K12 (CH-R125 primary_filter)",
 "sign_flips_raw_to_cycle": flips,
 "disagreement_set_cr_vs_rt": disagree,
 "drop_list_negative_both_datatimes": drop_both,
 "rt_drags_cycleband": rt_drags,
 "recommendation_block": rec,
}
json.dump(out, open(D + "/CH-R123_RERUN_stage2.json", "w"), indent=1)
print("sign_flips raw->cycle:", [f["lane"] for f in flips])
print("drop_both (neg cr AND neg rt):", [d["lane"] for d in drop_both])
print("rt cycle drags:", [r["lane"] for r in rt_drags])
print("disagreement rows:", len(disagree), "sign-disagree:",
      [r["lane"] for r in disagree if r.get("sign_disagree")])
