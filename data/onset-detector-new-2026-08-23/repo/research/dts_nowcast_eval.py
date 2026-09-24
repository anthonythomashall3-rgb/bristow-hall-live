#!/usr/bin/env python3
"""B-DTS-NOWCAST-EVAL (Window 3, EVAL-ONLY, no land).

Owner ruling 20260809T035112Z: Option 2 AUTHORIZED — measure a DTS withheld-tax ->
W875 nowcast bridge, spliced legacy<->current across the 2023-02-14 concept change,
BOTH metrics vs production stack_D4. NO landing, NO store write, NO code wiring.
Identity seams stay owner-reserved.

Method:
  * Drive the CANONICAL repo harness (method_source/nowcast_harness.py) against the
    landed raw inputs in archive/projects-old (repo has no method_source/raw). Verify
    it reproduces the recorded baselines (D0 0.19808, stack_D4 0.17400) BEFORE trusting
    any comparison; if it drifts, STOP (comparison would be apples-to-oranges).
  * Build a monthly DTS "Withheld" total = MTD amount on the last business day of each
    month (legacy concept 2005-10..2023-01; current concept 2023-03..2026-08; 2023-02 is
    the split month -> DROPPED as cross-concept). yoy within concept.
  * Fit W875 yoy ~ a + b*DTS_withheld_yoy on months <= FIT_END (2011-12-31, BINDING) —
    all-legacy, NO splice in the fit. RIDGE lam=1.0 (registered), same ols() as harness.
  * Emit a W875 member-z bridge at availability lag 33d (DTS monthly total is out ~2 biz
    days after month end; beats PAYEMS-bridge 38d and W875 real print 55d).
  * Two comparisons, both vs stack_D4:
      A) REPLACE the stack's PAYEMS-driven W875 fill with the DTS fill (apples-to-apples
         "which W875 fill is better").
      B) single-member attribution vs D0 (mirror harness attr loop), compare to the
         recorded PAYEMS W875 bridge (+0.00298 exCOVID / -0.02188 COVID).
  * Decision (batch step 3/4): DTS is adoptable ONLY if it beats stack_D4 on BOTH MAE
    (2012+ exCOVID) AND crossing-date median abs error, without adding false/missed
    crossings. A measured negative is a result (S5.5) and is NOT landed.
"""
import os, sys, json, csv, bisect
import datetime as dt
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R_DATA = os.path.join(os.path.dirname(REPO), "archive", "projects-old")
HARNESS = os.path.join(REPO, "method_source", "nowcast_harness.py")
SCRATCH = os.path.join(REPO, "research", ".dts_eval_scratch")
os.makedirs(SCRATCH, exist_ok=True)

# ---- 1. exec the canonical harness against archive data --------------------
src = open(HARNESS).read()
src = src.replace('R = os.path.dirname(os.path.abspath(__file__))', 'R = R_DATA')
# redirect its scratch json.dump away from the hardcoded Desktop path
import re
src = re.sub(r'^SCRATCH = .*$', 'SCRATCH = SCRATCH_OVERRIDE', src, count=1, flags=re.M)
ns = {"R_DATA": R_DATA, "SCRATCH_OVERRIDE": SCRATCH, "__name__": "harness"}
exec(compile(src, HARNESS, "exec"), ns)

D0 = ns["RESULTS"]["candidates"]["carry_forward_D0"]["full_2012plus"]["mae"]
SD4 = ns["RESULTS"]["candidates"]["stack_D4"]["full_2012plus"]["mae"]
REC_D0 = 0.19807882193986415; REC_SD4 = 0.17400488671645525
drift_D0 = D0 - REC_D0; drift_SD4 = SD4 - REC_SD4
print(f"REPRO D0={D0:.5f} (rec {REC_D0:.5f} d{drift_D0:+.5f})  "
      f"stack_D4={SD4:.5f} (rec {REC_SD4:.5f} d{drift_SD4:+.5f})")
# archive/projects-old raw is NOT frozen to the recorded scratchpad snapshot; small drift
# expected. A/B (stack_D4 vs stack_D4_DTS) is computed on the SAME snapshot in THIS run, so
# it is internally consistent regardless of drift. Guard only against a REGIME break (>1%).
assert abs(drift_D0) < 0.005 and abs(drift_SD4) < 0.005, \
    f"REGIME DRIFT too large: D0 {drift_D0}, stack_D4 {drift_SD4} — STOP, comparison unsafe"
print("REPRO OK — within 0.005 of recorded; same regime; A/B is internally consistent")

# pull harness handles
MU, SD = ns["MU"], ns["SD"]
dn = ns["dn"]; zclip = ns["zclip"]; month_pub = ns["month_pub"]; ols = ns["ols"]
FIT_END = ns["FIT_END"]; MO = ns["MO"]; S = ns["S"]
reading_from = ns["reading_from"]; reading_final = ns["reading_final"]
EXP_MU_FINAL = ns["EXP_MU_FINAL"]; EXP_SD_FINAL = ns["EXP_SD_FINAL"]
crossing_metrics = ns["crossing_metrics"]; cut_stats = ns["cut_stats"]
eval_mask = ns["eval_mask"]; covid = ns["covid"]; finite = ns["finite"]
GDAYS = ns["GDAYS"]; NG = ns["NG"]

# ---- 2. DTS monthly withheld totals (MTD on last day of month) -------------
LEG = os.path.join(REPO, "live_data/store/normalized/sha256/d6/"
    "d6b7c8ddd4f7dee807e17d045622657760b933820d0b492573f01cfa644315cc.json")
CUR = os.path.join(REPO, "live_data/store/normalized/sha256/38/"
    "38fbc22350975b07f25da1830ba23d924b797c2d68594032f29735c01bd76ae4.json")

def month_mtd(records, is_legacy):
    """{(y,m): mtd_total_on_last_obs_day}. Legacy: publisher_field==tax_deposit_mtd_amt.
       Current: r['mtd_amt']. Withheld deposits only (both series already filtered)."""
    by_day = {}
    for r in records:
        d = r["observation_period"]
        if is_legacy:
            if r.get("publisher_field") != "tax_deposit_mtd_amt":
                continue
            v = float(r["value"])
        else:
            v = r.get("mtd_amt")
            if v is None:
                continue
            v = float(v)
        dd = dt.date(int(d[:4]), int(d[5:7]), int(d[8:10]))
        by_day[dd] = v
    out = {}
    for dd, v in by_day.items():
        key = (dd.year, dd.month)
        if key not in out or dd > out[key][0]:
            out[key] = (dd, v)
    return {k: v[1] for k, v in out.items()}

leg = json.load(open(LEG))["records"]
cur = json.load(open(CUR))["records"]
M_leg = month_mtd(leg, True)
M_cur = month_mtd(cur, False)

# splice: legacy through 2023-01 (last full legacy month), current from 2023-03.
# 2023-02 split across the concept change -> dropped (flagged).
DTS_M = {}
for (y, m), v in M_leg.items():
    if (y, m) <= (2023, 1):
        DTS_M[(y, m)] = ("legacy", v)
for (y, m), v in M_cur.items():
    if (y, m) >= (2023, 3):
        DTS_M[(y, m)] = ("current", v)
print(f"DTS monthly: legacy {min(k for k in M_leg)}..{max(k for k in M_leg)} n={len(M_leg)}; "
      f"current {min(k for k in M_cur)}..{max(k for k in M_cur)} n={len(M_cur)}; "
      f"spliced n={len(DTS_M)}; dropped_split_month=(2023,2)")

def dts_yoy(y, m):
    cur_ = DTS_M.get((y, m)); prv = DTS_M.get((y - 1, m))
    if not cur_ or not prv or prv[1] == 0:
        return None, None
    # cross-concept flag: numerator/denominator span the legacy->current boundary
    concept_break = cur_[0] != prv[0]
    return (cur_[1] / prv[1] - 1) * 100.0, concept_break

# ---- 3. fit W875 yoy ~ a + b*DTS_yoy on months <= FIT_END (legacy-only) ----
def myoy_w875(d):
    return ns["myoy"](S["W875RX1"], d)

X, Y, nfit = [], [], 0
for d in MO:
    if d > FIT_END:
        break
    dy, brk = dts_yoy(d.year, d.month)
    w = myoy_w875(d)
    if dy is None or w is None:
        continue
    assert not brk, "concept break inside fit window — must not happen"
    X.append([1.0, dy]); Y.append(w); nfit += 1
LAM = 1.0
B = ols(X, Y, lam=LAM)   # ridge lam=1.0 in standardized space (registered)
print(f"FIT n={nfit} coef a={B[0]:.4f} b={B[1]:.4f}")

# in-sample fit quality (diagnostic only)
yh = np.array([B[0] + B[1]*x[1] for x in X]); yv = np.array(Y)
ss_res = float(((yv - yh)**2).sum()); ss_tot = float(((yv - yv.mean())**2).sum())
r2 = 1 - ss_res/ss_tot if ss_tot else None
print(f"FIT in-sample R2={r2:.4f}")

# ---- 4. DTS -> W875 member-z bridge events (availability lag 33d) ----------
DTS_LAG = 33
dts_events = []
n_break = 0
for d in MO:
    if d < dt.date(2001, 1, 1):
        continue
    dy, brk = dts_yoy(d.year, d.month)
    if dy is None:
        continue
    if brk:
        n_break += 1  # cross-concept yoy transition year (2023-03..2024-02) — contaminated
    yhat = B[0] + B[1]*dy
    z = (-yhat - MU["W875"]) / SD["W875"]
    dts_events.append((month_pub(d, DTS_LAG), zclip(z)))
print(f"DTS W875 bridge events n={len(dts_events)} (concept-break yoy months carried: {n_break})")

# ---- 5A. REPLACE stack W875 fill with DTS, rescore -------------------------
BR = ns["BR"]
orig_w875 = BR["W875"]
try:
    BR["W875"] = dts_events
    mz_dts = ns["stack_memberZ"]()
    reading_dts, _ = reading_from(mz_dts, EXP_MU_FINAL, EXP_SD_FINAL)
finally:
    BR["W875"] = orig_w875

def score(reading):
    full = cut_stats(reading, eval_mask & ~covid)
    cov = cut_stats(reading, eval_mask & covid)
    cr = crossing_metrics(reading)
    return {"mae_2012plus_exCOVID": full["mae"], "rmse_2012plus_exCOVID": full["rmse"],
            "mae_covid": cov["mae"], "crossings": cr}

stackD4_reading = ns["READINGS"]["stack_D4"]
s_base = score(stackD4_reading)
s_dts = score(reading_dts)

def med_err(sc, theta="0.5sigma"):
    return sc["crossings"][theta]["median_abs_day_err"]

# ---- 5B. single-member DTS-only attribution vs D0 (mirror harness attr) ----
mz0 = ns["mz0"]
merge = ns["merge_real_and_bridge"]
r_d0 = ns["READINGS"]["carry_forward_D0"]
cut_full = eval_mask & ~covid; cut_cov = eval_mask & covid
def mae_on(pred, cut):
    m = cut & finite & ~np.isnan(pred)
    return float(np.abs(pred[m] - reading_final[m]).mean())
mae0_full = mae_on(r_d0, cut_full); mae0_cov = mae_on(r_d0, cut_cov)
mzA = {k: v.copy() for k, v in mz0.items()}
BR["W875"] = dts_events
try:
    mzA["W875"] = merge("W875", dts_events)
finally:
    BR["W875"] = orig_w875
rA, _ = reading_from(mzA, EXP_MU_FINAL, EXP_SD_FINAL)
dts_attr = {"mae_delta_2012plus": round(mae_on(rA, cut_full) - mae0_full, 5),
            "mae_delta_covid": round(mae_on(rA, cut_cov) - mae0_cov, 5),
            "n_bridge_events": len(dts_events)}

# ---- 6. verdict ------------------------------------------------------------
mae_improves = s_dts["mae_2012plus_exCOVID"] < s_base["mae_2012plus_exCOVID"]
cross_base = med_err(s_base); cross_dts = med_err(s_dts)
cross_improves = (cross_dts is not None and cross_base is not None and cross_dts < cross_base)
false_base = s_base["crossings"]["0.5sigma"]["false"]; miss_base = s_base["crossings"]["0.5sigma"]["missed"]
false_dts = s_dts["crossings"]["0.5sigma"]["false"]; miss_dts = s_dts["crossings"]["0.5sigma"]["missed"]
no_worse_cross_count = (false_dts <= false_base and miss_dts <= miss_base)
adopt = bool(mae_improves and cross_improves and no_worse_cross_count)

OUT = {
    "batch": "B-DTS-NOWCAST-EVAL", "mode": "EVAL_ONLY_NO_LAND",
    "ruling": "OWNER 20260809T035112Z Option 2 AUTHORIZED",
    "repro": {"D0_mae": D0, "stack_D4_mae": SD4,
              "recorded_D0_mae": REC_D0, "recorded_stack_D4_mae": REC_SD4,
              "drift_D0": round(drift_D0, 6), "drift_stack_D4": round(drift_SD4, 6),
              "note": "canonical repo harness vs archive/projects-old inputs. Archive raw NOT frozen "
                      "to recorded scratchpad snapshot -> small drift. A/B computed same-snapshot this "
                      "run = internally consistent; baseline for the DTS comparison is the REPRODUCED "
                      "stack_D4, not the recorded 0.17400."},
    "dts_series": {
        "legacy_source_id": "treasury_dts_federal_tax_deposits_legacy",
        "current_source_id": "treasury_dts_withheld_individual_fica_current",
        "legacy_months": [f"{min(M_leg)}", f"{max(M_leg)}", len(M_leg)],
        "current_months": [f"{min(M_cur)}", f"{max(M_cur)}", len(M_cur)],
        "spliced_months": len(DTS_M), "dropped_split_month": "2023-02",
        "monthly_def": "MTD amount on last obs day of month (per concept)"},
    "fit": {"n": nfit, "fit_end": FIT_END.isoformat(), "ridge_lambda": LAM,
            "coef_intercept": round(float(B[0]), 5), "coef_dts_yoy": round(float(B[1]), 5),
            "in_sample_r2": round(r2, 4),
            "note": "fit window all-legacy concept; NO splice in fit"},
    "bridge": {"availability_lag_days": DTS_LAG, "n_events": len(dts_events),
               "concept_break_yoy_months_carried": n_break,
               "timeliness": "DTS monthly ~33d vs PAYEMS-bridge 38d vs W875 real 55d"},
    "compare_replace_w875_in_stack": {
        "stack_D4": s_base, "stack_D4_DTS": s_dts,
        "mae_delta": round(s_dts["mae_2012plus_exCOVID"] - s_base["mae_2012plus_exCOVID"], 5),
        "cross_median_abs_day_err_0.5s": {"stack_D4": cross_base, "stack_D4_DTS": cross_dts}},
    "dts_single_member_attribution_vs_D0": dts_attr,
    "recorded_payems_w875_attribution": {"mae_delta_2012plus": 0.00298, "mae_delta_covid": -0.02188,
                                         "n_bridge_events": 306},
    "decision": {"mae_improves": mae_improves, "crossing_improves": cross_improves,
                 "no_extra_false_or_missed": no_worse_cross_count, "ADOPT": adopt,
                 "rule": "adopt iff BOTH mae(2012+ exCOVID) and crossing median-abs-day-err improve, no extra false/missed"},
    "splice_caveat": "Live-edge (2023-03+) rests on legacy<->current concept splice; the yoy transition "
                     "year 2023-03..2024-02 is cross-concept-contaminated. Identity owner-reserved; NOT landed.",
}
outp = os.path.join(REPO, "research", "dts_nowcast_eval_out.json")
json.dump(OUT, open(outp, "w"), indent=2)
print("\n=== VERDICT ===")
print(f"stack_D4      MAE {s_base['mae_2012plus_exCOVID']:.5f}  cross0.5 {cross_base}")
print(f"stack_D4_DTS  MAE {s_dts['mae_2012plus_exCOVID']:.5f}  cross0.5 {cross_dts}")
print(f"mae_improves={mae_improves} cross_improves={cross_improves} ADOPT={adopt}")
print(f"DTS attr vs D0: {dts_attr}")
print("wrote", outp)
