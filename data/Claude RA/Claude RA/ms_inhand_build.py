#!/usr/bin/env python3
"""M-S (Michaillat-Saez) recession indicator, IN-HAND rebuild — verification pass.

lambda(t) = min(uhat, vhat), where
  u3 = 3-mo trailing MA of U3; v3 = 3-mo trailing MA of vacancy rate (100*JTSJOL/CLF16OV)
  uhat_t = u3_t - min(u3 over past 12 months incl. current)
  vhat_t = max(v3 over past 12 months incl. current) - v3_t
Thresholds (M-S 2024): 0.3 = recession likely started; 0.8 = certain.

IN-HAND: at each JOLTS vintage date V (ALFRED, first vintage 2010-08-11):
  JTSJOL column with vintage <= V (that vintage's own column),
  UNRATE vintage = latest ALFRED UNRATE vintage <= V,
  CLF16OV = current vintage (CONVENTION: denominator revisions second-order; noted in memo).
Pre-2010 in-hand impossible from ALFRED (no JOLTS vintages) -> publication-lag
reconstruction from BLS JOLTS news releases is the only path (memo plan).
"""
import json, bisect, os, sys
from collections import OrderedDict
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine"))
import monthwin as MW

UP = os.environ.get("BH_DATA", os.path.dirname(os.path.abspath(__file__)))

# --- JOLTS vintages (wide) ---
jd = json.load(open(f"{UP}/vintages/JTSJOL_allvintages.json"))["observations"]
jolts = {}  # vintage 'YYYYMMDD' -> {date: value}
for row in jd:
    dt = row["date"][:7]
    for k, v in row.items():
        if k == "date" or v == ".":
            continue
        jolts.setdefault(k.split("_")[1], {})[dt] = float(v)
jvints = sorted(jolts)

# --- UNRATE vintages (wide, chunked) ---
import glob
unr = {}
for f in sorted(glob.glob(f"{UP}/vintages/UNRATE_rt_*.json")):
    _d = json.load(open(f))
    if "observations" not in _d:      # UNRATE_rt_2024_2028.json is an API 400 error file
        continue
    for row in _d["observations"]:
        dt = row["date"][:7]
        for k, v in row.items():
            if k == "date" or v == ".":
                continue
            unr.setdefault(k.split("_")[1], {})[dt] = float(v)
uvints = sorted(unr)

# --- CLF16OV current ---
clf = {r["date"][:7]: float(r["value"])
       for r in json.load(open(f"{UP}/series/CLF16OV.json"))["observations"]
       if r["value"] != "."}

def lam_series(u, j):
    """u, j: dicts month->value (same vintage). Returns month->lambda.

    CALENDAR-INDEXED (fixed 2026-08-22).  The previous implementation took the
    3-month average and the 12-month lookback by ROW POSITION over a sorted list
    of the months present.  Where a month is missing — as October 2025 is, the
    household survey never having been collected during the shutdown — a
    positional window silently reaches across the hole and averages months that
    are not adjacent in time, producing a reading that looks right and is not.

    The fix changes the INDEXING and nothing else.  Both conventions the old
    code used are preserved exactly:
      * the lookback is the current month plus the previous 11 (lookback=11,
        include_current=True), which is the "past 12 months incl. current" of
        the docstring above.  Note this differs from FRED's SAHMCURRENT, which
        excludes the current month and therefore goes negative.
      * min_periods=1 preserves the short window at the very start of the JOLTS
        series, where the old positional slice silently truncated.  Making that
        window strict instead would drop a further 2,167 readings across
        2001-02 to 2002-01 in every vintage; that is a specification question,
        not a gap-handling bug, and is left for a pre-registered decision.

    Measured effect of this fix over all 193 JOLTS vintages: zero values change;
    44 readings that the old code fabricated across a hole are now correctly
    undefined, in the months 2025-11 through 2026-06 of 9 vintages.
    """
    months = sorted(set(u) & set(j) & set(clf))
    if not months:
        return {}
    v = {m: 100.0 * j[m] / clf[m] for m in months}
    U = MW.by_month({m: u[m] for m in months})
    V = MW.by_month(v)
    uh = MW.gap_from_min(U, average=3, lookback=11, include_current=True, min_periods=1)
    vh = MW.gap_from_max(V, average=3, lookback=11, include_current=True, min_periods=1)
    return {MW.m_label(t): min(uh[t], vh[t]) for t in sorted(set(uh) & set(vh))}

rows = []
for V in jvints:
    ui = bisect.bisect_right(uvints, V) - 1
    if ui < 0:
        continue
    lam = lam_series(unr[uvints[ui]], jolts[V])
    if not lam:
        continue
    last = max(lam)
    first_cross = next((m for m in sorted(lam) if lam[m] >= 0.3), None)
    # first crossing within the last 24 obs months of this vintage (fresh signal)
    # calendar-indexed: the last 24 CALENDAR months of this vintage, not the
    # last 24 rows, which would reach further back wherever a month is missing.
    cutoff = MW.m_index(last) - 23
    recent = [m for m in sorted(lam) if MW.m_index(m) >= cutoff and lam[m] >= 0.3]
    rows.append((V, last, round(lam[last], 3), first_cross, recent[0] if recent else None))

OUT = os.environ.get("BH_OUT", os.path.join(UP, "ms_inhand_v2.csv"))
with open(OUT, "w") as f:
    f.write("vintage,last_obs,lambda_last,first_cross_ever,first_cross_recent24\n")
    for r in rows:
        f.write(",".join(str(x) for x in r) + "\n")

# windows of interest
print("=== 2020 window (vintages 2020-01..2020-08) ===")
for r in rows:
    if "20200101" <= r[0] <= "20200831":
        print(r)
print("=== 2023-06..2025-02 window ===")
for r in rows:
    if "20230601" <= r[0] <= "20250228":
        print(r)
print("=== current edge (last 6 vintages) ===")
for r in rows[-6:]:
    print(r)
print(f"\ntotal vintage rows: {len(rows)}; first vintage {rows[0][0]}")
