#!/usr/bin/env python3
"""B-EXT-1948 VALIDATION-ONLY lane.

Adopts CH-R102 verdict: 1948 lane = DIFFERENT INSTRUMENT (3/17 members). This
harness runs the existing index_v1 detector UNCHANGED and evaluates its own
headline() over the pre-1976 range. No refit, no threshold move, no store write.

Method (frozen-baseline validation, never fitted):
  1. exec method_source/index_v1.py verbatim (NOWCAST_DISABLE=1) -> production
     namespace with headline(), zval(), exp_mu/exp_sd, in_recession(), CHANNELS.
     Per-member MU/SD and exp_mu/exp_sd are computed by that module over its full
     member history + 1976+ line baseline respectively -- IDENTICAL whether START
     is 1976 or 1948 for MU/SD, and we deliberately keep exp_mu/exp_sd FROZEN at
     the production 1976+ value (using it, not refitting) for the extended lane.
  2. call the SAME headline() over 1948-01-01..1960-12-31; sigma = (h-exp_mu)/exp_sd.
  3. crossing detector = existing nowcast_harness rule: first day of >=5 consecutive
     days with sigma >= theta. theta in {0.5, 1.0} are EXISTING code thresholds
     (census span 0.5-sigma; alfred/onset 1.0-sigma). No new threshold.
"""
import os, sys, csv, json, datetime as dt, tempfile, hashlib
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
ARCHIVE = REPO / "data_archive" / "current_revised_and_spatial"
SRC = (REPO / "method_source" / "index_v1.py").read_text()
CURRENT_SERIES = ["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU",
    "GACDFSA066MSFRBPHI","NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST",
    "PERMIT","UMCSENT","W875RX1","GS10","GS1","USRECD","RRSFS","MORTGAGE30US",
    "PAYEMS","CCSA","DBAA","DAAA"]

os.environ["NOWCAST_DISABLE"] = "1"
ns = {"__name__": "__ext1948__", "__file__": str(REPO/"method_source"/"index_v1.py")}
with tempfile.TemporaryDirectory(prefix="rmv2-ext1948-") as tmp:
    root = Path(tmp); raw = root / "raw"; raw.mkdir()
    for s in CURRENT_SERIES:
        (raw / (s + ".csv")).symlink_to(ARCHIVE / (s + ".csv"))
    (raw / "vintages").symlink_to(ARCHIVE / "vintages")
    os.environ["INDEX_OUT"] = str(root / "index_v1_out.json")
    cwd = os.getcwd(); os.chdir(root)
    try:
        exec(compile(SRC, str(REPO/"method_source"/"index_v1.py"), "exec"), ns)
    finally:
        os.chdir(cwd)

headline = ns["headline"]; zval = ns["zval"]; CHANNELS = ns["CHANNELS"]
exp_mu = ns["exp_mu"]; exp_sd = ns["exp_sd"]; in_recession = ns["in_recession"]
S = ns["S"]

def drange(a, b):
    d = a
    while d <= b:
        yield d; d += dt.timedelta(days=1)

# ---- extended daily line 1948-01-01 .. 1960-12-31 (covers all 3 added recessions) ----
A, B = dt.date(1948,1,1), dt.date(1960,12,31)
line_ext = {}
sigma_ext = {}
for d in drange(A, B):
    h = headline(d)
    if h is not None:
        line_ext[d] = h
        sigma_ext[d] = (h - exp_mu) / exp_sd

# ---- per-date channel-weight coverage at anchors (step 2) ----
def coverage(d):
    mem_present = {}
    chan_present = []
    for name, (w, members) in CHANNELS.items():
        got = [m for m in members if zval(m, d) is not None]
        mem_present[name] = got
        if got:
            chan_present.append(name)
    nmem = sum(len(v) for v in mem_present.values())
    wshare = sum(w for name,(w,ms) in CHANNELS.items() if mem_present[name])
    return {"n_members": nmem, "channels_nonempty": sorted(chan_present),
            "weight_share": round(wshare,3),
            "members_by_channel": {k: v for k,v in mem_present.items() if v}}

anchors = ["1948-01-01","1950-01-01","1953-01-01","1957-01-01","1976-06-01"]
anchor_cov = {a: coverage(dt.date.fromisoformat(a)) for a in anchors}

# ---- crossing detector (existing rule: first day of >=5 consecutive days sigma>=theta) ----
def crossings(theta):
    days = sorted(sigma_ext)
    events = []  # (start_date, run_len)
    i = 0; n = len(days)
    while i < n:
        if sigma_ext[days[i]] >= theta:
            j = i
            # require >=5 CONSECUTIVE calendar days at/above theta
            while j+1 < n and (days[j+1]-days[j]).days == 1 and sigma_ext[days[j+1]] >= theta:
                j += 1
            run = (days[j]-days[i]).days + 1
            if run >= 5:
                events.append((days[i], run))
            i = j+1
        else:
            i += 1
    return events

# NBER onset (business-cycle peak = last month of expansion) for the 3 added recessions
NBER = {
  "1948-49": (dt.date(1948,11,1), dt.date(1949,10,1)),
  "1953-54": (dt.date(1953,7,1),  dt.date(1954,5,1)),
  "1957-58": (dt.date(1957,8,1),  dt.date(1958,4,1)),
}

def month_in_recession(y, m):
    d = dt.date(y, m, 15)
    return in_recession(d)

report = {}
for theta in (0.5, 1.0):
    ev = crossings(theta)
    fires = {}
    for nm,(peak,trough) in NBER.items():
        # a fire is "for" this recession if its start lies in [peak-18mo, trough]
        lo = peak - dt.timedelta(days=548)
        cand = [e for e in ev if lo <= e[0] <= trough]
        if cand:
            first = min(cand, key=lambda e: e[0])[0]
            lead_days = (peak - first).days
            fires[nm] = {"fired": True, "first_cross": first.isoformat(),
                         "nber_peak": peak.isoformat(),
                         "lead_days": lead_days,
                         "lead_months_approx": round(lead_days/30.44,1)}
        else:
            fires[nm] = {"fired": False, "nber_peak": peak.isoformat()}
    # false positives: crossing onsets 1948-01..1957-12 whose start month is NON-recession
    # and not inside any of the 3 recession run-up windows [peak-18mo, trough]
    runup = []
    for nm,(peak,trough) in NBER.items():
        runup.append((peak - dt.timedelta(days=548), trough))
    fp = []
    for start, run in ev:
        if not (dt.date(1948,1,1) <= start <= dt.date(1957,12,31)):
            continue
        if month_in_recession(start.year, start.month):
            continue
        if any(a <= start <= b for a,b in runup):
            continue
        fp.append({"start": start.isoformat(), "run_days": run})
    report[f"{theta:.1f}sigma"] = {
        "n_crossing_events_full_window": len(ev),
        "all_crossing_starts": [ (e[0].isoformat(), e[1]) for e in ev ],
        "recession_fires": fires,
        "false_positives_1948_1957": {"count": len(fp), "events": fp},
    }

# ---- above-threshold base rate 1948-1957 (honest lead caveat) ----
w4857 = [d for d in sigma_ext if dt.date(1948,1,1) <= d <= dt.date(1957,12,31)]
nonrec = [d for d in w4857 if not in_recession(d)]
base_rate = {}
for theta in (0.5, 1.0, 2.0):
    ab = sum(1 for d in w4857 if sigma_ext[d] >= theta)
    abn = sum(1 for d in nonrec if sigma_ext[d] >= theta)
    base_rate[f"{theta:.1f}sigma"] = {
        "all_days_above_pct": round(100*ab/len(w4857), 1),
        "nonrecession_days_above_pct": round(100*abn/len(nonrec), 1),
    }
sig_vals = sorted(sigma_ext[d] for d in w4857)
base_rate["sigma_min_median_max_1948_1957"] = [round(sig_vals[0],2), round(sig_vals[len(sig_vals)//2],2), round(sig_vals[-1],2)]

# ---- peak sigma per added recession (context) ----
peaks = {}
for nm,(peak,trough) in NBER.items():
    w = [sigma_ext[d] for d in sigma_ext if peak - dt.timedelta(days=90) <= d <= trough + dt.timedelta(days=90)]
    peaks[nm] = {"peak_sigma": round(max(w),2) if w else None,
                 "span": [peak.isoformat(), trough.isoformat()]}

out = {
  "schema_version": "recession-monitor-v2.ext1948-validation-lane.v1",
  "batch": "B-EXT-1948_SPINE",
  "lane_label": "validation_only_1948_analog_lane",
  "information_set_mode": "validation_only",
  "distinct_third_lane": True,
  "never_merged_into_headline": True,
  "never_fitted": True,
  "carries_no_realtime_claim": True,
  "ch_r102_verdict_adopted": "1948 lane = DIFFERENT INSTRUMENT (3/17 members at 1948-01); {UNRATEv,INDPRO,BAAAAA}",
  "detector": "index_v1.headline() UNCHANGED; frozen 1976+ expansion baseline exp_mu/exp_sd (NOT refit); crossing = existing >=5-consecutive-day rule at existing 0.5-sigma / 1.0-sigma thresholds",
  "frozen_baseline": {"exp_mu": exp_mu, "exp_sd": exp_sd},
  "eval_window": [A.isoformat(), B.isoformat()],
  "line_days": len(line_ext),
  "anchor_coverage": anchor_cov,
  "added_recessions_peak_sigma": peaks,
  "base_rate_1948_1957": base_rate,
  "lead_caveat": ("Reported lead_days = earliest in-window (>=peak-18mo) crossing start. "
    "Because the 1948-1957 non-recession above-threshold base rate is high "
    f"({base_rate['0.5sigma']['nonrecession_days_above_pct']}% at 0.5-sigma, "
    f"{base_rate['1.0sigma']['nonrecession_days_above_pct']}% at 1.0-sigma), these earliest "
    "in-window crossings are contaminated by false positives and are NOT clean early-warning "
    "leads. This high FP base rate is itself the DIFFERENT-INSTRUMENT signature (CH-R102): a "
    "3-member analog machine standardized on a 1976+ modern-era baseline is not a like-for-like "
    "detector in the early-postwar regime. VALIDATION ONLY; no threshold moved (0.5/1.0-sigma "
    "are existing code thresholds); NOT fitted."),
  "detector_results": report,
}
outp = REPO / "research" / "ext1948" / "validation_lane.v1.json"
outp.write_text(json.dumps(out, indent=1, sort_keys=True))
print("WROTE", outp)
print("exp_mu=%.4f exp_sd=%.4f line_days=%d" % (exp_mu, exp_sd, len(line_ext)))
for a in anchors:
    c = anchor_cov[a]; print(a, "n_members=%d wshare=%.2f chans=%s" % (c["n_members"], c["weight_share"], c["channels_nonempty"]))
for theta in ("0.5sigma","1.0sigma"):
    r = report[theta]
    print("---", theta, "n_events=%d fp=%d" % (r["n_crossing_events_full_window"], r["false_positives_1948_1957"]["count"]))
    for nm,f in r["recession_fires"].items():
        print("   ", nm, f)
for nm,p in peaks.items():
    print("peak_sigma", nm, p["peak_sigma"])
