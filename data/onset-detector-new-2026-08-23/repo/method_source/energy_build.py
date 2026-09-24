#!/usr/bin/env python3
"""THE unified detector. One statistic, one bar, one gate — no exceptions:
  E12(t) = trailing 12-month integral of max(official reading, 0), in sigma-months.
  RECESSION BAR: E12 >= 7.5  (weakest episode 8.80 monthly / 10.56 daily;
                              weakest NBER-dated recession 20.7 monthly;
                              highest monthly reading outside a padded
                              recession window 6.14, in 2003-12)
  ECHO GATE:     a crossing opens a NEW episode only if E12 drained below 2.0
                 since the prior episode (every gap between distinct recessions
                 drained to 0.54 or less; the one undrained path, the 1980 and
                 1981-82 twins, floored at 23.85 monthly, so it is one
                 double-dip episode rather than two).
  READ THE BAR HONESTLY: 6.14 is the MONTHLY figure. On the daily line the same
                 padded-window rule leaves a maximum of 8.00, on 2003-12-01,
                 which is ABOVE the 7.5 bar — that day is the 2001 recession's
                 own energy still draining, and it is the echo gate, not
                 headroom under the bar, that keeps the false-alarm count at
                 zero there. Both outside-window maxima fall on the first day
                 the exclusion pad expires on a monotonically draining path, so
                 they measure where the pad ends as much as they measure the
                 economy.
Dating of every episode: Sahm Rule onset, Bristow Rule end (the papers' rules).
Outputs: daily E12 series for the chart, per-recession detection dates, calib.

The five calibration numbers quoted above used to be typed in by hand here and
retyped in five copy blocks elsewhere, pinned by nothing. They are now
recomputed from the record at build time (see DERIVE CALIBRATION below) and
checked against the numerals still in print, so a drift fails loudly instead of
leaving five stale copies. Nothing in this file is tuned: BAR_E and RESET are
unchanged, and the derived numbers describe the record rather than set it."""
import json, os, re, sys, datetime as dt
from collections import deque

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


BAR_E, RESET = 7.5, 2.0
BASE = dt.date(1970, 1, 1)
off = lambda d: (d - BASE).days

# ---- daily E12 from the official reading ----
D = json.load(open("index_v1_out.json"))
mu, sd = D["exp_mu"], D["exp_sd"]
line = {dt.date.fromisoformat(k): (v-mu)/sd for k, v in D["line"].items()}
days = sorted(line)
sm = {}; q = deque(); s = 0.0
vals = [line[d] for d in days]
for i, d in enumerate(days):
    q.append(vals[i]); s += vals[i]
    while len(q) > 21: s -= q.popleft()
    sm[d] = s/len(q)

# compressed testimony: beyond 4 sigma (a once-per-generation reading) additional
# depth counts at fourth-root weight — only persistence can add conviction
def compress(v, _C=4.0):
    return v if v <= _C else _C + (v - _C) ** 0.25
sm = {d: compress(v) for d, v in sm.items()}
E = {}; q2 = deque(); s2 = 0.0
for d in days:
    v = max(sm[d], 0.0); q2.append((d, v)); s2 += v
    while (d - q2[0][0]).days > 365: s2 -= q2.popleft()[1]
    E[d] = s2/30.44

# ---- monthly E12 (1957+) for the pre-1976 era ----
R = json.load(open("geo/recpage.json"))
LL = [(dt.date.fromisoformat(m+"-01"), v) for m, v in R["longline"]]
mdates = [d for d, _ in LL]; mpos = [max(v, 0) for _, v in LL]
_assert_complete_calendar([m for m, _v in R["longline"]], "energy_build longline")
mE = {mdates[i]: sum(mpos[max(0, i-11):i+1]) for i in range(len(mdates))}

# ---- episode detection with the echo gate (uniform, full record) ----
def detect(series_dates, series_E):
    """walk the record: upcross of BAR_E while armed -> detection; re-arm on drain < RESET"""
    armed = True; detections = []
    for d in series_dates:
        e = series_E[d]
        if armed and e >= BAR_E:
            detections.append(d); armed = False
        elif not armed and e < RESET:
            armed = True
    return detections

det_m = detect([d for d in mdates if d < dt.date(1976, 6, 1)], mE)
det_d = detect(days, E)
print("Episode detections (monthly era):", [d.isoformat()[:7] for d in det_m])
print("Episode detections (daily era):  ", [d.isoformat() for d in det_d])

# ---- attach detections to recessions; verify count & zero FP ----
EP = [("1957-58","1957-08-01"),("1960-61","1960-04-01"),("1969-70","1969-12-01"),
      ("1973-75","1973-11-01"),("1980","1980-01-01"),("1981-82","1981-07-01"),
      ("1990-91","1990-07-01"),("2001","2001-03-01"),("2007-09","2007-12-01"),
      ("2020","2020-02-01"),("2022-23","2022-10-19")]
alldet = det_m + det_d
attach = {}
for d in alldet:
    best = min(EP, key=lambda kv: abs((dt.date.fromisoformat(kv[1]) - d).days))
    k, onset = best
    gap = (d - dt.date.fromisoformat(onset)).days
    attach[k] = attach.get(k) or (d, gap)
print("\nDetection vs onset (negative = before the recession began):")
orphans = [d for d in alldet if all(abs((dt.date.fromisoformat(o) - d).days) > 500 for _, o in EP)]
for k, onset in EP:
    if k in attach:
        d, gap = attach[k]
        print(f"  {k:8} detected {d}  ({gap:+d} days vs onset)")
    else:
        # twins: 1981-82 has no own detection (energy never reset after 1980) — same episode
        print(f"  {k:8} — no separate detection (energy never drained after the prior twin: one double-dip episode)")
print("orphan detections (false positives):", orphans or "NONE")

# ================= DERIVE CALIBRATION =================
# Every number below is recomputed from the two E12 series and the chronology
# already loaded above. None of them is a threshold: BAR_E and RESET are set
# elsewhere and are not touched here. These are descriptions of the record, and
# a description that is typed rather than measured is the thing that rots.
#
# Two stated design choices, both disclosed in the papers, neither fitted:
#   * the exclusion pad around a recession, one year of lead-in and two of tail,
#     because the accumulator builds ahead of an onset and drains slowly after;
#   * which window an episode's peak is read over. "Drives the line to X" is a
#     claim about the episode as the instrument dates it (io..ie), not about the
#     committee's peak-to-trough months: 2020's NBER window is three months long
#     and the twelve-month integral had not finished accumulating inside it.
LEAD_PAD, TAIL_PAD = 365, 730

def _m1(s):                      # "YYYY-MM" -> first day of that month
    return dt.date(int(s[:4]), int(s[5:7]), 1)
def _eom(s):                     # "YYYY-MM" -> last day of that month
    y, m = int(s[:4]), int(s[5:7])
    return dt.date(y + (m == 12), 1 if m == 12 else m + 1, 1) - dt.timedelta(days=1)
def _peak(series, dates, a, b):
    seg = [series[d] for d in dates if a <= d <= b]
    return max(seg) if seg else None

ROWS = sorted(R["rows"], key=lambda r: r["start"])
OFFICIAL = [r for r in ROWS if r["key"] != "2022-23"]   # 2022-23 is the instrument's own

# per-episode peaks, over the episode as the instrument dates it
epk_m = {r["key"]: _peak(mE, mdates, _m1(r["io"]), _eom(r["ie"])) for r in ROWS}
epk_d = {r["key"]: _peak(E,  days,   _m1(r["io"]), _eom(r["ie"])) for r in ROWS}
weakest_key = min(epk_m, key=lambda k: epk_m[k])
official_key = min((r["key"] for r in OFFICIAL), key=lambda k: epk_m[k])

# the highest the line has ever reached outside a padded recession window
def _padded(d):
    return any(_m1(r["start"]) - dt.timedelta(days=LEAD_PAD) <= d
               <= _eom(r["end"]) + dt.timedelta(days=TAIL_PAD) for r in ROWS)
out_when, out_max = max(((d, mE[d]) for d in mdates if not _padded(d)), key=lambda x: x[1])
outd_when, outd_max = max(((d, E[d]) for d in days if not _padded(d)), key=lambda x: x[1])

# the drain test the echo gate encodes: minimum E12 in each inter-recession gap
drained, undrained = [], []
for _p, _n in zip(ROWS, ROWS[1:]):
    seg = [mE[d] for d in mdates if _eom(_p["end"]) < d < _m1(_n["start"])]
    if not seg:
        continue
    segd = [E[d] for d in days if _eom(_p["end"]) < d < _m1(_n["start"])]
    rec = {"gap": f"{_p['key']}->{_n['key']}", "floor_monthly": round(min(seg), 2),
           "floor_daily": round(min(segd), 2) if segd else None}
    (drained if min(seg) < RESET else undrained).append(rec)

calib = {
    "bar": BAR_E, "reset": RESET,
    "weakest_key": weakest_key,
    "weakest_monthly": round(epk_m[weakest_key], 2),
    # None if the weakest episode ever moves back before the daily line starts
    "weakest_daily": (round(epk_d[weakest_key], 2) if epk_d[weakest_key] is not None else None),
    "official_floor_key": official_key,
    "official_floor": round(epk_m[official_key], 2),
    "outside_max": round(out_max, 2), "outside_when": out_when.isoformat()[:7],
    "outside_max_daily": round(outd_max, 2), "outside_when_daily": outd_when.isoformat(),
    "drain_max": round(max(g["floor_monthly"] for g in drained), 2),
    "drain_min": round(min(g["floor_monthly"] for g in drained), 2),
    "undrained_floor": (round(min(g["floor_monthly"] for g in undrained), 2)
                        if undrained else None),
    "drained_gaps": drained, "undrained_gaps": undrained,
    "pad_days": [LEAD_PAD, TAIL_PAD],
    "episode_peaks_monthly": {k: round(v, 2) for k, v in epk_m.items()},
    "episode_peaks_daily": {k: (round(v, 2) if v is not None else None) for k, v in epk_d.items()},
}
print("\nDerived calibration:")
print(f"  weakest episode        {weakest_key}: {calib['weakest_monthly']:.2f} monthly / "
      f"{calib['weakest_daily']:.2f} daily")
print(f"  weakest NBER-dated     {official_key}: {calib['official_floor']:.2f} monthly")
print(f"  outside padded windows {calib['outside_max']:.2f} monthly ({calib['outside_when']}) / "
      f"{calib['outside_max_daily']:.2f} daily ({calib['outside_when_daily']})")
print(f"  inter-recession drains {calib['drain_min']:.2f}-{calib['drain_max']:.2f} over "
      f"{len(drained)} drained gaps; undrained: "
      + (", ".join(f"{g['gap']} floor {g['floor_monthly']:.2f}m/{g['floor_daily']:.2f}d"
                   for g in undrained) or "none"))
if calib["outside_max_daily"] >= BAR_E:
    print(f"  NOTE the daily line reaches {calib['outside_max_daily']:.2f} outside every padded "
          f"window, above the {BAR_E} bar: zero false alarms is delivered by the echo gate\n"
          f"       there, not by headroom under the bar.")

# ---- outputs ----
e12 = {"d": [off(d) for d in days], "v": [round(E[d]*100) for d in days]}
detections = {k: attach[k][0].isoformat() for k in attach}
json.dump({"e12": e12, "bar": BAR_E, "reset": RESET, "detections": detections,
           "det_gaps": {k: attach[k][1] for k in attach}, "calib": calib,
           "current": round(E[days[-1]], 2)},
          open("geo/energy.json", "w"), separators=(",", ":"))

# ---- patch recpage rows with energy detection ----
rp = json.load(open("geo/recpage.json"))
for r in rp["rows"]:
    k = r["key"]
    if k in attach:
        d, gap = attach[k]
        r["edet"] = d.isoformat(); r["edet_gap"] = gap
    else:
        r["edet"] = None; r["edet_gap"] = None   # 1981-82 twin
json.dump(rp, open("geo/recpage.json", "w"), separators=(",", ":"))
print(f"\nenergy.json {os.path.getsize('geo/energy.json')/1e3:.0f} KB · current E12 {E[days[-1]]:.2f} σ-months")

# ================= PIN THE COPY BLOCKS =================
# Deriving the numbers fixes this file. It does not fix the five copy blocks that
# quote them as typed numerals -- this docstring, the site template, the deployed
# page, and the two paper renderings -- and nothing else in the repo compares the
# two. energy.json's calib is shipped but never read by the site JS, so a drift
# would change nothing visible while five prose copies went quietly wrong.
#
# So: check each derived number against the numeral actually in print, at the
# precision it is printed to, and name every file carrying a stale one. Set
# ENERGY_ALLOW_CALIB_DRIFT=1 to downgrade the failure to a warning while the
# copy is being updated.
COPY_BLOCKS = ("energy_build.py", "geo/site_tpl.html", "deploy/public/index.html",
               "papers/paper2_v3.md", "papers/p2_v3.html",
               "papers/paper2_v2.md", "papers/p2_v2.html",
               "research/artifacts/ground_truth.md")
PINNED = (
    ("weakest episode, monthly peak",              calib["weakest_monthly"],   "8.80"),
    ("weakest episode, daily peak",                calib["weakest_daily"],     "10.56"),
    ("weakest NBER-dated recession, monthly peak", calib["official_floor"],    "20.7"),
    ("highest monthly reading outside a pad",      calib["outside_max"],       "6.14"),
    ("highest daily reading outside a pad",        calib["outside_max_daily"], "8.00"),
    ("deepest drain between distinct recessions",  calib["drain_max"],         "0.54"),
    ("floor of the undrained twin path",           calib["undrained_floor"],   "23.85"),
)

def _carriers(numeral):
    """Files that print this numeral, and how many times."""
    pat = re.compile(r"(?<![\d.])" + re.escape(numeral) + r"(?![\d])")
    hits = []
    for rel in COPY_BLOCKS:
        try:
            n = len(pat.findall(open(rel, encoding="utf-8", errors="replace").read()))
        except OSError:
            continue
        if n:
            hits.append(f"{rel} x{n}")
    return hits

drift, uncited = [], []
for label, derived, printed in PINNED:
    if derived is None or f"{derived:.{len(printed.split('.')[1])}f}" != printed:
        drift.append((label, derived, printed, _carriers(printed)))
    elif not _carriers(printed):
        uncited.append((label, printed))

if drift:
    print("\nCALIB DRIFT — a published number no longer matches the record:", file=sys.stderr)
    for label, derived, printed, files in drift:
        print(f"  {label}: derived {derived}, in print as {printed}", file=sys.stderr)
        print("    stale copies: " + (", ".join(files) or "none found — check by hand"),
              file=sys.stderr)
    print("  geo/energy.json has been written with the DERIVED values; the prose has not.\n"
          "  Update the copy blocks, then rerun. ENERGY_ALLOW_CALIB_DRIFT=1 to proceed.",
          file=sys.stderr)
    if not os.environ.get("ENERGY_ALLOW_CALIB_DRIFT"):
        sys.exit(3)
elif uncited:
    # the pin has rotted into a tautology: nothing in print carries the numeral
    print("\nCALIB PIN STALE — nothing in the copy blocks quotes these any more:", file=sys.stderr)
    for label, printed in uncited:
        print(f"  {label} ({printed}) — drop it from PINNED or point at the new copy",
              file=sys.stderr)
    if not os.environ.get("ENERGY_ALLOW_CALIB_DRIFT"):
        sys.exit(3)
else:
    print("calib pin OK: %d derived numbers match every copy block that quotes them (%s)"
          % (len(PINNED), ", ".join(sorted({f.split(" x")[0] for _, _, p in PINNED
                                            for f in _carriers(p)}))))
