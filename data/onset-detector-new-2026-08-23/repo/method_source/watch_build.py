#!/usr/bin/env python3
"""THE ONSET WATCH — zero-lag recession dating, earthquake-early-warning style.

Rules (DEC-020, adopted 2026-07-25 from the confirmed OHW2-C1 record —
research/confirm/ohw2-c1/, verdict PASS on the registered 12-row stamp table):

  OPEN     a watch opens (and stamps the provisional onset) the day the official
           reading crosses the 1.0-sigma signal line RISING — higher than five
           days earlier (one month earlier on the monthly era's grid) — provided
           the echo gate is armed: accumulated stress E12 has drained below 1.5
           sigma-months since the last confirmed episode.
  KILL     the pace gates are kill conditions: the watch dies unless E12 has
           risen >= 1.00 sigma-months within 30 days of the stamp, >= 1.90
           within 60, and >= 3.0 within 90. A reading below the signal line for
           more than 45 days kills the watch too (fizzle). After a kill a fresh
           upcross is required before a new watch.
  CONFIRM  E12 >= 5.0 while the watch lives locks the call in; confirmation
           beats any pending gate (the receipt supersedes corroboration).
           (DEC-023, 2026-07-25: the confirmation bar moved 7.5 -> 5.0. The
           ALARM2 sweep found bars 5.0-7.5 crossed with fizzle 45-90 produce
           an IDENTICAL stamp ledger — 10/10 onsets, 0 confirmed false
           alarms, day-of rate 1.00, same two killed false starts — while
           the lower bar confirms far sooner. Only the confirmation lag
           moves. The DETECTOR's recession bar stays 7.5; see REC_BAR.)
  RE-ARM   after confirmation, no new watch until E12 < 1.5.

No auxiliary sanction: the yield curve is a leading gauge elsewhere on the
site, not a precondition of the watch (DEC-020 removed the curve-sanction
dependency; with the pace gates promoted to kill conditions it cost coverage
and bought nothing).

Two eras, one rule:
  daily    1976-06 onward — index_v1_out.json "line": official reading =
           compressed 21-day mean, E12 = trailing-365-day positive sum / 30.44.
           Day-precision stamps.
  monthly  1957-06 .. 1976-05 — geo/recpage.json "longline" (the monthly
           reconstruction): E12M = trailing 12-month positive sum. Watches are
           month-precision by construction and labeled so; slope = a rising
           month, pace gates check E12M at +1/+2/+3 months, a fizzle is a full
           month below without return the following month. The monthly lane
           owns only stamps before the daily lane begins.

Backtest over the full record (1957+): every watch, its stamp, its outcome.
The state machine is a faithful port of the confirmed research machinery
(research/confirm/ohw2-c1/registration/code/ohw2/ohw2_common.py simulate())
specialized to the adopted rule-set."""
import json, csv, bisect, datetime as dt
import numpy as np

def _assert_complete_calendar(months, name="longline"):
    """A positional window (vals[i-11:i+1]) is only a 12-CALENDAR-MONTH window
    when the month list has no holes.  October 2025 has no household-survey
    value, and any series that inherits that hole will silently make positional
    windows average non-adjacent months.  Fail loudly instead.
    Added 2026-08-22 after that bug was found in ms_inhand_build.py."""
    idx = [int(str(m)[:4]) * 12 + int(str(m)[5:7]) - 1 for m in months]
    bad = [i for a, b, i in zip(idx, idx[1:], range(1, len(idx))) if b - a != 1]
    if bad:
        holes = [f"{idx[i-1]//12:04d}-{idx[i-1]%12+1:02d} -> {idx[i]//12:04d}-{idx[i]%12+1:02d}" for i in bad[:5]]
        raise ValueError(f"{name} is not a complete monthly calendar ({len(bad)} break(s): {holes}). "
                         f"Positional 12-month windows are unsafe; index by calendar month.")


# ---- adopted rule constants (DEC-020) ----
THR = 1.0            # open threshold (sigma) — final climb through the signal line
SLOPE_DAYS = 5       # daily slope confirmation: reading > reading 5 days earlier
DRAIN = 1.5          # RETIRED as the re-arm test (DEC-026); still reported in the
                     # rules blob and used by the live aftermath display below
# DEC-026 (2026-07-25): re-arm on QUIESCENCE IN THE READING, not on drainage of the
# accumulator. E12 is a twelve-month integral, so after a long or severe episode it
# can stay above any drain level for years and suppress the next watch entirely: in
# 2023-10..2025-05 it never fell below 1.5 (minimum 2.147), so 39 days at or above
# the open line were invisible and no watch could open. Quiescence in the reading is
# the honest new-episode test and is decoupled from the accumulator's memory.
COOL_SIGMA = 0.5     # the reading must sit below this ...
COOL_DAYS = 90       # ... continuously for this long before a new watch may open
BAR = 5.0            # watch confirmation bar (sigma-months) — DEC-023
REC_BAR = 7.5        # the DETECTOR's recession bar (energy.json "bar"),
                     # unchanged; used only for the live-state display below
PACE_H = 180         # pace-gate deadline (days) — DEC-025
# Pace gates are DERIVED, not fitted: G(t) = BAR*t/PACE_H is the minimum constant
# pace that reaches the confirmation bar within PACE_H days, so they track the bar
# automatically. The retired gates 1.00/1.90/3.00 were exactly this ray at the old
# bar of 7.5 with H=225 (1.00 = 7.5*30/225, 3.00 = 7.5*90/225); leaving them fixed
# when DEC-023 cut the bar to 5.0 would have silently tightened the deadline to 150.
G30, G60, G90 = tuple(round(BAR * t / PACE_H, 4) for t in (30, 60, 90))
FIZZLE_DAYS = 45     # reading below THR for more than this kills the watch

EPOCH = dt.date(1970, 1, 1).toordinal()
def d2o(d): return d.toordinal() - EPOCH
def o2d(o): return dt.date.fromordinal(int(o) + EPOCH)

def compress(v, C=4.0):
    return v if v <= C else C + (v - C) ** 0.25

# ---- daily lane: official reading (compressed 21d mean) + E12 ----
D = json.load(open("index_v1_out.json"))
mu, sd = D["exp_mu"], D["exp_sd"]
items = sorted((dt.date.fromisoformat(k), (v - mu) / sd) for k, v in D["line"].items())
days = [d for d, _ in items]
raw = np.array([v for _, v in items], dtype=float)
ords_d = np.array([d2o(d) for d in days], dtype=np.int64)
n_d = len(ords_d)
c = np.concatenate([[0.0], np.cumsum(raw)])
idx = np.arange(n_d)
lo21 = np.maximum(0, idx - 20)
sm_d = (c[idx + 1] - c[lo21]) / (idx + 1 - lo21)
sm_d = np.where(sm_d <= 4.0, sm_d, 4.0 + np.abs(sm_d - 4.0) ** 0.25)
pos = np.maximum(sm_d, 0.0)
if bool(np.all(np.diff(ords_d) == 1)):
    cp = np.concatenate([[0.0], np.cumsum(pos)])
    lo365 = np.maximum(0, idx - 365)
    e12_d = (cp[idx + 1] - cp[lo365]) / 30.44
else:  # honest fallback for a gapped grid
    e12_d = np.empty(n_d)
    j0 = 0; s = 0.0
    for i in range(n_d):
        s += pos[i]
        while ords_d[i] - ords_d[j0] > 365:
            s -= pos[j0]; j0 += 1
        e12_d[i] = s / 30.44

# ---- monthly lane: the monthly reconstruction (recpage longline) + E12M ----
R = json.load(open("geo/recpage.json"))
ords_m, sm_m = [], []
for ym, v in R["longline"]:
    ords_m.append(d2o(dt.date(int(ym[:4]), int(ym[5:7]), 1)))
    sm_m.append(float(v))
ords_m = np.array(ords_m, dtype=np.int64)
sm_m = np.array(sm_m, dtype=float)
pos_m = np.maximum(sm_m, 0.0)
n_m = len(sm_m)
_assert_complete_calendar([ym for ym, _v in R["longline"]], "watch_build longline")
e12_m = np.array([pos_m[max(0, i - 11):i + 1].sum() for i in range(n_m)])

DAILY_CUTOFF = int(ords_d[0])  # the daily lane owns stamps from here on


def _nxt_at_or_above(cond):
    """nxt[i] = smallest j >= i with cond[j], else n."""
    n = len(cond)
    nxt = np.full(n + 1, n, dtype=np.int64)
    for i in range(n - 1, -1, -1):
        nxt[i] = i if cond[i] else nxt[i + 1]
    return nxt


def make_lane(ords, sm, e12, monthly):
    lane = {"ord": ords, "sm": sm, "e12": e12, "monthly": monthly}
    n = len(ords)
    if monthly:
        ix = np.arange(n)
        lane["i30"] = np.minimum(ix + 1, n)
        lane["i60"] = np.minimum(ix + 2, n)
        lane["i90"] = np.minimum(ix + 3, n)
        up = np.zeros(n, dtype=bool)
        up[1:] = sm[1:] > sm[:-1]        # month-grid slope adaptation, labeled
    else:
        lane["i30"] = np.searchsorted(ords, ords + 30, side="left")
        lane["i60"] = np.searchsorted(ords, ords + 60, side="left")
        lane["i90"] = np.searchsorted(ords, ords + 90, side="left")
        up = np.zeros(n, dtype=bool)
        up[SLOPE_DAYS:] = sm[SLOPE_DAYS:] > sm[:-SLOPE_DAYS]
    lane["ok"] = up
    lane["nxt_bar"] = _nxt_at_or_above(e12 >= BAR)
    lane["nxtbelow"] = _nxt_at_or_above(e12 < DRAIN)
    # DEC-026: cooled[i] is true when the reading has stayed below COOL_SIGMA for a
    # continuous COOL_DAYS ending at i (three months on the month grid).
    cooled = np.zeros(n, dtype=bool)
    calm = sm < COOL_SIGMA
    if monthly:
        win = max(1, int(round(COOL_DAYS / 30.0)))
        for i in range(win - 1, n):
            cooled[i] = bool(calm[i - win + 1:i + 1].all())
    else:
        jstart = np.searchsorted(ords, ords - COOL_DAYS, side="left")
        for i in range(n):
            cooled[i] = bool(calm[jstart[i]:i + 1].all())
    lane["nxtcool"] = _nxt_at_or_above(cooled)
    above = sm >= THR
    dif = np.diff(above.astype(np.int8))
    starts = list(np.flatnonzero(dif == 1) + 1)
    ends = list(np.flatnonzero(dif == -1))
    if above[0]: starts = [0] + starts
    if above[-1]: ends = ends + [len(above) - 1]
    lane["runs"] = list(zip(starts, ends))
    return lane


def simulate(lane):
    """The adopted watch state machine (port of the confirmed OHW2 simulate()).
    Returns watch events: stamp/outcome/cause/confirm/pace30/60/90/gates."""
    ords, e12 = lane["ord"], lane["e12"]
    n = len(ords)
    monthly = lane["monthly"]
    ok = lane["ok"]
    runs = lane["runs"]
    nxt_bar, nxtb = lane["nxt_bar"], lane["nxtcool"]   # DEC-026 re-arm
    i30a, i60a, i90a = lane["i30"], lane["i60"], lane["i90"]
    events = []
    arm_from = 0
    resume = 0
    ri = 0
    nruns = len(runs)
    while ri < nruns:
        s, e = runs[ri]
        lo = max(s, arm_from, resume)
        if lo > e:
            ri += 1; continue
        seg = ok[lo:e + 1]
        if not seg.any():
            ri += 1; continue
        j = lo + int(np.argmax(seg))
        base = e12[j]
        i30, i60, i90 = int(i30a[j]), int(i60a[j]), int(i90a[j])
        p30 = float(e12[i30] - base) if i30 < n else None
        p60 = float(e12[i60] - base) if i60 < n else None
        p90 = float(e12[i90] - base) if i90 < n else None
        death, cause = n + 1, None
        if p30 is not None and p30 < G30 - 1e-12:
            death, cause = i30, "pace30"
        elif p60 is not None and p60 < G60 - 1e-12:
            death, cause = i60, "pace60"
        elif p90 is not None and p90 < G90 - 1e-12:
            death, cause = i90, "pace90"
        # fizzle: chain runs whose gaps the watch survives
        k = ri
        gap_max = 31 if monthly else 46
        while k + 1 < nruns and ords[runs[k + 1][0]] - ords[runs[k][1]] <= gap_max:
            k += 1
        fz = int(np.searchsorted(ords, ords[runs[k][1]] + FIZZLE_DAYS + 2, side="left"))
        if fz >= n:
            fz = n + 1
        cidx = int(nxt_bar[j])
        t_dead = min(death, fz)
        gates = all(v is not None and v >= g - 1e-12
                    for v, g in ((p30, G30), (p60, G60), (p90, G90)))
        if cidx < n and cidx <= t_dead:
            events.append({"stamp_i": j, "stamp_ord": int(ords[j]),
                           "outcome": "confirmed", "cause": None,
                           "confirm_i": cidx, "confirm_ord": int(ords[cidx]),
                           "pace30": p30, "pace60": p60, "pace90": p90,
                           "gates_passed": gates})
            arm_from = int(nxtb[cidx])
            resume = cidx + 1
            while ri < nruns and runs[ri][1] < max(arm_from, resume):
                ri += 1
            continue
        if t_dead > n:  # neither confirmed nor dead by data end: open watch
            events.append({"stamp_i": j, "stamp_ord": int(ords[j]),
                           "outcome": "open", "cause": None, "confirm_i": None,
                           "confirm_ord": None, "pace30": p30, "pace60": p60,
                           "pace90": p90, "gates_passed": gates})
            break
        if cause is None or fz < death:
            cause = "fizzle-month" if monthly else "fizzle45"
            t_dead = fz
        events.append({"stamp_i": j, "stamp_ord": int(ords[j]),
                       "outcome": "killed", "cause": cause, "confirm_i": None,
                       "confirm_ord": None, "pace30": p30, "pace60": p60,
                       "pace90": p90, "gates_passed": gates})
        resume = t_dead + 1
        while ri < nruns and runs[ri][0] <= t_dead:
            ri += 1
    return events


lane_d = make_lane(ords_d, sm_d, e12_d, monthly=False)
lane_m = make_lane(ords_m, sm_m, e12_m, monthly=True)
events = []
for lane, era in ((lane_m, "monthly"), (lane_d, "daily")):
    for ev in simulate(lane):
        if era == "monthly" and ev["stamp_ord"] >= DAILY_CUTOFF:
            continue  # the daily lane owns that era
        ev["era"] = era
        events.append(ev)
events.sort(key=lambda ev: ev["stamp_ord"])

# ---- outcomes vs the instrument chronology (scored-onset windows) ----
# The 1979 twin (1980 + 1981-82) shares one instrument onset: one scored onset
# covering two episodes. A watch stamped inside [onset - 365d, episode end]
# belongs to that onset.
DAT = json.load(open("geo/dating.json"))
onsets = {}
for k, rec in sorted(DAT.items()):
    if k.startswith("_") or "onset" not in rec:
        continue
    on, en = dt.date.fromisoformat(rec["onset"]), dt.date.fromisoformat(rec["end"])
    w = onsets.setdefault(on, {"keys": [], "onset": on, "end": en})
    w["keys"].append(k)
    w["end"] = max(w["end"], en)
windows = sorted(onsets.values(), key=lambda w: w["onset"])
for w in windows:
    w["key"] = "+".join(sorted(w["keys"], key=lambda k: DAT[k]["onset"]))
    w["lo"] = d2o(w["onset"]) - 365
    w["hi"] = d2o(w["end"])

watches = []
for ev in events:
    win = next((w for w in windows if w["lo"] <= ev["stamp_ord"] <= w["hi"]), None)
    row = {"onset": o2d(ev["stamp_ord"]).isoformat(),
           "confirmed": o2d(ev["confirm_ord"]).isoformat() if ev["confirm_ord"] is not None else None,
           "outcome": "confirmed recession" if ev["outcome"] == "confirmed"
                      else ("open" if ev["outcome"] == "open" else "fizzled"),
           "era": ev["era"],
           "precision": "month" if ev["era"] == "monthly" else "day"}
    if ev["outcome"] == "killed":
        row["cause"] = ev["cause"]
    if ev["outcome"] == "confirmed" and win is not None:
        row["episode"] = win["key"]
        row["onset_delta_days"] = ev["stamp_ord"] - d2o(win["onset"])
        row["confirm_lag_days"] = ev["confirm_ord"] - ev["stamp_ord"]
        # the 1957-58 onset is the monthly series' first month: the delta is
        # measured against a censored left boundary, and labeled so.
        if d2o(win["onset"]) <= int(ords_m[0]):
            row["left_censored"] = True
    if ev["pace30"] is not None: row["pace30"] = round(ev["pace30"], 2)
    if ev["pace60"] is not None: row["pace60"] = round(ev["pace60"], 2)
    if ev["pace90"] is not None: row["pace90"] = round(ev["pace90"], 2)
    row["pace_ok"] = bool(ev["gates_passed"])  # all three pace gates met
    watches.append(row)

print("ONSET WATCH backtest (1957+, monthly era at month precision):")
for w in watches:
    tag = " [%s]" % w["precision"] if w["precision"] == "month" else ""
    if w["outcome"] == "confirmed recession":
        print("  watch opened %s%s -> confirmed %s, onset delta %+dd, confirmed after %dd"
              % (w["onset"], tag, w["episode"], w["onset_delta_days"], w["confirm_lag_days"]))
    else:
        print("  watch opened %s%s -> %s (%s)" % (w["onset"], tag, w["outcome"], w.get("cause", "open")))
fz = [w for w in watches if w["outcome"] == "fizzled"]
cf = [w for w in watches if w["outcome"] == "confirmed recession"]
print("  totals: %d watches, %d confirmed, %d killed" % (len(watches), len(cf), len(fz)))

# ---- current state (daily lane, data edge) ----
d_last = days[-1]
r_last = float(sm_d[-1]); e_last = float(e12_d[-1])
open_ev = next((ev for ev in events if ev["outcome"] == "open"), None)
conf_events = [ev for ev in events if ev["era"] == "daily" and ev["outcome"] == "confirmed"]
last_conf_i = conf_events[-1]["confirm_i"] if conf_events else 0
# DEC-026: the live state uses the SAME re-arm test as the backtest above, so the
# published state can never contradict the published history. The old drainage test
# is retained alongside it only to report the accumulator's own condition.
_calm_d = np.asarray(sm_d) < COOL_SIGMA
_ord_a = np.array([d.toordinal() for d in days])
_j0 = np.searchsorted(_ord_a, _ord_a - COOL_DAYS, side="left")
cooled_since_conf = any(bool(_calm_d[_j0[i]:i + 1].all())
                        for i in range(last_conf_i, len(days)))
drained_since_conf = bool(float(e12_d[last_conf_i:].min()) < DRAIN)
armed = cooled_since_conf
if open_ev is not None:
    state = "watch"
elif not cooled_since_conf:
    state = "confirmed"
else:
    state = "clear"
ui_state = state
# Live display only: "aftermath" means the confirmed episode has cooled below
# the DETECTOR's recession bar, so it stays pinned to REC_BAR (7.5). DEC-023
# moved the watch's CONFIRMATION bar to 5.0; it deliberately does not move
# this display cut, which would otherwise show aftermath while the detector
# still reads a recession in progress.
if state == "confirmed" and r_last < THR and e_last < REC_BAR:
    ui_state = "aftermath"

# 10y-2y curve status — informational only (a leading gauge shown elsewhere on
# the site); DEC-020 removed the curve sanction from the watch preconditions.
def load(sid):
    o = {}
    for r in csv.reader(open("raw/" + sid + ".csv")):
        if r and r[0][:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            o[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
    return o
G10, G2 = load("DGS10"), load("DGS2")
curve = {d: G10[d] - G2[d] for d in G10 if d in G2}
cd = sorted(curve)
def inverted_within(d, days_back=548):
    i0 = bisect.bisect_left(cd, d - dt.timedelta(days=days_back))
    i1 = bisect.bisect_right(cd, d)
    return any(curve[cd[j]] < 0 for j in range(i0, i1))

cur = {"state": ui_state,
       "reading": round(r_last, 2), "e12": round(e_last, 2),
       "armed": bool(armed and e_last < REC_BAR),   # display cut: REC_BAR
       "curve_sanction": inverted_within(d_last),   # informational, not a gate
       "watch_onset": o2d(open_ev["stamp_ord"]).isoformat() if open_ev else None}
# aftermath nuance: not yet re-armed — E12 never drained below 1.5 since the
# last confirmation (DEC-020 drain; formerly 2.0)
cur["aftermath_undrained"] = bool(not cooled_since_conf)   # DEC-026: not re-armed
cur["e12_undrained"] = bool(not drained_since_conf)        # accumulator's own state

# ---- same-day disturbance monitor ----
# A disturbance OPENS the day the official 21-day reading crosses the census floor
# (+0.5 sigma) from below - the same crossing the event census uses to date every
# historical disturbance, so the live call and the historical record are one rule.
DFLOOR = 0.5
cur["dist_open"] = bool(r_last >= DFLOOR)
if cur["dist_open"]:
    i0 = n_d - 1
    while i0 > 0 and sm_d[i0 - 1] >= DFLOOR:
        i0 -= 1
    cur["dist_since"] = o2d(ords_d[i0]).isoformat()
    cur["dist_peak"] = round(float(sm_d[i0:].max()), 2)
# live pace read for an active watch (site shows the gate clock from ~day 30)
if open_ev is not None:
    cur["watch_age_days"] = int(ords_d[-1]) - open_ev["stamp_ord"]
    cur["watch_pace"] = round(e_last - float(e12_d[open_ev["stamp_i"]]), 2)
print("\ncurrent:", cur)

json.dump({"rules": {"open_thr": THR, "slope_days": SLOPE_DAYS,
                     "g30": G30, "g60": G60, "g90": G90, "drain": DRAIN,
                     # DEC-026 re-arm: published so the copy can state the LIVE rule.
                     # Until now the rules blob carried only the retired drain gate,
                     # so the template literally could not say what re-arms the watch.
                     "cool_sigma": COOL_SIGMA, "cool_days": COOL_DAYS,
                     "bar": BAR, "rec_bar": REC_BAR,
                     "fizzle_days": FIZZLE_DAYS,
                     "decision": "DEC-020+DEC-023"},
           "current": cur,
           "history": watches},
          open("geo/watch.json", "w"), separators=(",", ":"))
print("saved geo/watch.json")
