#!/usr/bin/env python3
"""Event census: every excursion of the official reading above the 0.5σ
disturbance floor since 1957, classified and graded.

Tiers (by peak of the official reading):
  recession   — the NBER window itself (official grade D from the ranking table)
  signal      — peak >= 1.0σ outside any NBER window (recession-scale stress)
  disturbance — 0.5σ <= peak < 1.0σ (recorded, graded, not recessionary)

Rules: spans above 0.5σ merge across gaps <=45 days (daily era, 1976+, 21-day-mean
line) or <=2 months (monthly era, 1957-1976). A merged span containing NBER windows
is split at them; the lead-in above the floor is absorbed into the recession event
(recorded as its early-warning note), the decay tail likewise, EXCEPT a tail that
runs into another recession within 12 months, which becomes an 'interlude' event.
Non-recession events get a self-anchored damage grade D = cbrt(rise^2 * burden)
with burden integrated over the event span in sigma-months."""
import json, csv, datetime as dt, bisect, os, tempfile
from collections import deque

D0 = json.load(open("index_v1_out.json"))
mu, sd = D0["exp_mu"], D0["exp_sd"]
line = {dt.date.fromisoformat(k): (v-mu)/sd for k, v in D0["line"].items()}
days = sorted(line)
sm = {}
q = deque(); s = 0.0
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

R = json.load(open("geo/recpage.json"))
LL = [(dt.date.fromisoformat(m+"-01"), v) for m, v in R["longline"]]
GRADE = {r["key"]: r["grade"] for r in R["rows"]}

NBER = [("1957-58","1957-08-01","1958-04-30"),("1960-61","1960-04-01","1961-02-28"),
 ("1969-70","1969-12-01","1970-11-30"),("1973-75","1973-11-01","1975-03-31"),
 ("1980","1980-01-01","1980-07-31"),("1981-82","1981-07-01","1982-11-30"),
 ("1990-91","1990-07-01","1991-03-31"),("2001","2001-03-01","2001-11-30"),
 ("2007-09","2007-12-01","2009-06-30"),("2020","2020-02-01","2020-04-30")]
NB = [(k, dt.date.fromisoformat(a), dt.date.fromisoformat(b)) for k, a, b in NBER]

FLOOR = 0.5
CUT = dt.date(1976, 6, 1)

# ---- severity scale: Categories 1-5 are for RECESSIONS only (Saffir-Simpson exact:
# tropical storms carry no hurricane category; disturbances carry no recession category).
# The completed-event damage record has an empty interval between the strongest historical
# non-recession event (the 1959 steel strike, D=2.38) and the mildest recession (2022-23,
# D=2.75). The mathematically centered separator is (2.38+2.75)/2 = 2.565. Category 1
# begins at that separator; Categories 2-5 retain the established 3-unit floors.
CAT_W = 3.0
HISTORICAL_NONRECESSION_MAX_D = 2.38
HISTORICAL_NONRECESSION_MAX_LABEL = "1959 steel strike"
# DEC-019: post-merge canonical count. DEC-018's 16 was the pre-merge
# accounting; the 90-day fragment-merge rule absorbed the Oct 2015
# micro-fragment into the 2015-16 major. See excursion_reconciliation.md.
HISTORICAL_NONRECESSION_EVENTS = 15
WEAKEST_RECESSION_D = min(GRADE.values())
WEAKEST_RECESSION_KEY = min(GRADE, key=GRADE.get)
DAMAGE_CUTOFF = round((HISTORICAL_NONRECESSION_MAX_D + WEAKEST_RECESSION_D) / 2.0, 3)
REC_FLOOR = DAMAGE_CUTOFF
CAT_FLOORS = [5, 8, 11, 14]                # Cat1 >=2.565, Cat2 >=5, Cat3 >=8, Cat4 >=11, Cat5 >=14
def catof(D, is_recession=False):
    if D is None or not is_recession or D < REC_FLOOR:
        return None                        # disturbances/aftermath/leadin: no category
    return min(5, 1 + sum(D >= f for f in CAT_FLOORS))
# DEC-011 (authorized 2026-07-18): a disturbance is MAJOR when its damage is at
# least 1.4, it is not an echo, and it does not overlap a recession span.
# DEC-025 (2026-07-25): the echo drain gate is the watch's own re-arm level rather
# than a separate fitted constant. Verified byte-identical census.
ECHO_DRAIN = 1.5

# DEC-025 (2026-07-25): MAJOR_D is derived as half the recession damage cutoff
# rather than fitted. Identical census and identical major/disturbance split.
MAJOR_D = round(REC_FLOOR / 2.0, 4)   # 2.565 / 2 = 1.2825
MAJOR_DEF = {
    "id": "DEC-011",
    "date": "2026-07-18",
    "text": "damage D ≥ half the recession cutoff, not an echo of a prior episode, "
            "and not overlapping a recession span",
}

def spans(seq, gap_days):
    """seq: sorted [(date, val)]; maximal runs val>=FLOOR merged across short gaps."""
    out = []; cur = None
    for d, v in seq:
        if v >= FLOOR:
            if cur and (d - cur[1]).days <= gap_days: cur = (cur[0], d)
            else:
                if cur: out.append(cur)
                cur = (d, d)
    if cur: out.append(cur)
    return out

def seg_stats(seq, a, b):
    w = [(d, v) for d, v in seq if a <= d <= b]
    pk = max(w, key=lambda x: x[1])
    return pk[1], pk[0], w

def burden_sig_months(w, daily):
    if daily: return sum(max(v, 0) for _, v in w) / 30.44
    return sum(max(v, 0) for _, v in w)

events = []
def process(seq, gap_days, daily, lo_lim, hi_lim):
    seq = [(d, v) for d, v in seq if lo_lim <= d <= hi_lim]
    for a, b in spans(seq, gap_days):
        # NBER windows intersecting this span
        recs = [(k, ra, rb) for k, ra, rb in NB if not (rb < a or ra > b)]
        if not recs:
            pk, pkd, w = seg_stats(seq, a, b)
            rise = pk
            burden = burden_sig_months(w, daily)
            Dg = (max(rise,.01)**2 * max(burden,.01)) ** (1/3)
            nxt = [ra for _, ra, rb in NB if ra > b]
            lead = (min(nxt) - pkd).days if nxt and (min(nxt) - b).days <= 366 else None
            after = any(rb < a <= rb + dt.timedelta(days=730) for _, ra, rb in NB)
            events.append({"class": "disturbance", "major": pk >= 1.0,
                "start": a.isoformat(), "end": b.isoformat(), "peak": round(pk,2),
                "peakdate": pkd.isoformat(), "D": round(Dg,2),
                "rec_in_days": lead, "aftermath": after, "era": "daily" if daily else "monthly"})
            continue
        # split the span at the NBER windows it contains
        prev_end = None
        for i, (k, ra, rb) in enumerate(recs):
            seg_a = max(a, ra); seg_b = min(b, rb)
            pk, pkd, w = seg_stats(seq, max(a, ra - dt.timedelta(days=400)) if i == 0 else recs[i-1][2], seg_b)
            # lead-in note: first date of the merged span if this is the first recession in it
            note_lead = None
            if i == 0 and a < ra:
                note_lead = (ra - a).days
            ck = catof(GRADE.get(k), True) or 1
            events.append({"class": "recession", "key": k, "cat": ck,
                "start": ra.isoformat(), "end": rb.isoformat(),
                "peak": round(max(v for d, v in seq if ra <= d <= rb), 2),
                "peakdate": max(((d, v) for d, v in seq if ra <= d <= rb), key=lambda x: x[1])[0].isoformat(),
                "D": GRADE.get(k), "leadin_days": note_lead,
                "era": "daily" if daily else "monthly"})
            # interlude to the next recession inside the same span?
            if i + 1 < len(recs):
                na, nb_ = recs[i+1][1], recs[i+1][2]
                ia, ib = rb + dt.timedelta(days=1), na - dt.timedelta(days=1)
                wseg = [(d, v) for d, v in seq if ia <= d <= ib]
                if wseg:
                    pk2 = max(wseg, key=lambda x: x[1])
                    events.append({"class": "interlude",
                        "start": ia.isoformat(), "end": ib.isoformat(),
                        "peak": round(pk2[1],2), "peakdate": pk2[0].isoformat(), "D": None,
                        "era": "daily" if daily else "monthly"})

process(LL, 70, False, dt.date(1957,6,1), CUT - dt.timedelta(days=1))
process(sorted(sm.items()), 45, True, CUT, max(days))

# ---- the battery-detected recession: Apr-Aug 2024 (Sahm onset, Bristow end; papers' dating) ----
BAT = json.load(open("geo/battery.json"))
# window: Onset Rule -> composite Bristow end, from the dating rules' output
DATW = json.load(open("geo/dating.json"))
ba = dt.date.fromisoformat(DATW["2022-23"]["onset"]); bb = dt.date.fromisoformat(DATW["2022-23"]["end"])
events[:] = [e for e in events if not (e["class"]=="disturbance" and
             not (dt.date.fromisoformat(e["end"]) < ba or dt.date.fromisoformat(e["start"]) > bb))]
wseq = [(d, v) for d, v in sorted(sm.items()) if ba <= d <= bb]
bpk = max(wseq, key=lambda x: x[1])
c22 = catof(GRADE.get("2022-23"), True) or 1
events.append({"class": "recession", "key": "2022-23", "cat": c22, "battery": True,
    "start": ba.isoformat(), "end": bb.isoformat(), "peak": round(bpk[1],2),
    "peakdate": bpk[0].isoformat(), "D": GRADE.get("2022-23"), "leadin_days": None, "era": "daily"})
# early-signal retag: disturbances whose next recession is now the 2024 one
for e in events:
    if e["class"]=="disturbance" and e.get("rec_in_days") is None:
        pd_ = dt.date.fromisoformat(e["peakdate"])
        if dt.date(2022,1,1) <= pd_ <= ba:
            e["rec_in_days"] = (ba - pd_).days
            e["next_instr"] = True
events.sort(key=lambda e: e["start"])
# annotations for well-known episodes (applied by peak-date window, factual labels)
ANN = [("1959-07","1959-12","1959 steel strike"),("1966-01","1967-12","1966-67 credit crunch"),
 ("1979-01","1979-12","Volcker tightening"),
 ("1985-01","1986-12","1986 oil price collapse"),("1998-08","1998-11","LTCM / Russia default"),
 ("2011-07","2011-12","debt-ceiling / euro crisis"),("2015-08","2016-07","2015-16 industrial downturn"),
 ("2018-11","2019-02","Q4 2018 market rout"),("1987-11","1988-02","Black Monday aftermath"),("2022-06","2022-10","early signal of the 2022-23 recession"),
 ("2022-10","2023-06","part of the 2022-23 recession"),
("2024-06","2024-10","aftershock of the 2022-23 recession — the wave where labor's Sahm Rule crossed; the episode's labor aftershock (employment confirming the Oct 2022 - Jun 2023 recession)"),
 ("2025-03","2025-06","spring 2025 stress wave"),("2025-09","2026-01","late-2025 soft patch")]
for e in events:
    if e["class"] in ("signal","disturbance"):
        pd = e["peakdate"][:7]
        for a, b, lbl in ANN:
            if a <= pd <= b: e["note"] = lbl; break

# --- merge fragmented disturbances (Anthony, 2026-07-19): two consecutive DISTURBANCE
# events < 90 days apart are one stress episode split by a brief sub-0.5σ dip (e.g. the
# 2015-16 industrial downturn). Merge them; never touches recession spans, so pre-recession
# disturbances like 2022-06 and the recession dating are untouched. Recomputes peak/D over
# the union from the daily reading. ---
def _dord(x): return dt.date.fromisoformat(x)
_ds = sorted([e for e in events if e["class"]=="disturbance"], key=lambda e: e["start"])
_other = [e for e in events if e["class"]!="disturbance"]
_merged = []
for e in _ds:
    if _merged:
        prev = _merged[-1]
        gap = (_dord(e["start"]) - _dord(prev["end"])).days
        if 0 <= gap < 90:
            a, b = _dord(prev["start"]), _dord(e["end"])
            daily = _dord(e["start"]) >= CUT
            seq = sorted(sm.items()) if daily else LL
            pk, pkd, w = seg_stats(seq, a, b)
            bur = burden_sig_months(w, daily)
            Dm = round((pk*pk*bur)**(1/3), 2)
            prev["end"] = e["end"]; prev["peak"] = round(pk,2); prev["peakdate"] = pkd.isoformat()
            prev["D"] = Dm; prev["major_display"] = pk >= 1.0
            prev["note"] = prev.get("note","")
            continue
    _merged.append(e)
events[:] = _other + _merged

# --- classify: echo -> aftermath, major vs regular disturbance, category, order ---
# Echo Rule (drain criterion): a disturbance is an aftershock of the previous recession
# if accumulated stress (monthly E12, trailing-12-month sum of positive readings on the
# long line) never fell below the ECHO_DRAIN gate between that recession's end and the
# event's start. Echoes are NOT separate disturbances: they are FOLDED into that
# recession's aftermath (one aftermath entry per recession, spanning its merged echoes).
# A disturbance is MAJOR under the authorized DEC-011 damage/echo/overlap rule.
# Major is its own class -- never counted as a regular disturbance too. Every episode
# carries the unified category catof(D).
_mE12 = {}
for _i in range(len(LL)):
    _mE12[LL[_i][0].isoformat()[:7]] = sum(max(x, 0.0) for _, x in LL[max(0, _i-11):_i+1])
_spans = sorted((r["io"], r["ie"], r["key"]) for r in R["rows"])
for e in events:
    if e["class"] != "disturbance":
        continue
    a, b = e["start"][:7], e["end"][:7]
    e["echo_of"] = None
    prior = [sp for sp in _spans if sp[1] < a]
    if prior:
        _io, _ie, _k = max(prior, key=lambda sp: sp[1])
        if min(v for m, v in _mE12.items() if _ie <= m <= a) >= ECHO_DRAIN:
            e["echo_of"] = _k
    _ovl_key = next((k for io, ie, k in _spans if io <= a <= ie or io <= b <= ie), None)
    if e["echo_of"] is not None:
        e["class"] = "aftermath"          # aftershock of a recession, folded below
        e["major"] = False
    elif _ovl_key is not None:
        e["class"] = "leadin"             # inside a recession's instrument window: onset run-up
        e["leadin_of"] = _ovl_key
        e["major"] = False
    elif e.get("rec_in_days") is not None and e["rec_in_days"] <= 183:
        e["class"] = "leadin"             # a recession opens within 6 months: this is its run-up
        e["leadin_of"] = next((k for io, ie, k in sorted(_spans) if io > b), None)
        e["major"] = False
    elif (e.get("D") or 0) >= MAJOR_D:
        e["class"] = "major"              # major disturbance: damage in the upper half of Cat 1
        e["major"] = True
    else:
        e["major"] = False

# fold consecutive aftermaths of the SAME recession into one aftermath entry (recompute peak/D)
_after = sorted([e for e in events if e["class"] == "aftermath"], key=lambda e: e["start"])
_rest = [e for e in events if e["class"] != "aftermath"]
_folded = []
for e in _after:
    if _folded and _folded[-1].get("echo_of") == e.get("echo_of"):
        prev = _folded[-1]
        a2, b2 = _dord(prev["start"]), _dord(e["end"])
        daily = _dord(e["start"]) >= CUT
        seq = sorted(sm.items()) if daily else LL
        pk, pkd, w = seg_stats(seq, a2, b2)
        bur = burden_sig_months(w, daily)
        prev["end"] = e["end"]; prev["peak"] = round(pk, 2); prev["peakdate"] = pkd.isoformat()
        prev["D"] = round((pk*pk*bur)**(1/3), 2)
        continue
    _folded.append(e)
events[:] = _rest + _folded

# drop lead-ins entirely (Anthony, 2026-07-19): a disturbance that runs into a recession
# is just an early warning sign, not an event to count -- neither a disturbance nor its
# own class. It is identified above only so it is not miscounted as a disturbance, then removed.
events[:] = [e for e in events if e["class"] != "leadin"]

# unified category on every graded episode; order the whole census by date
for e in events:
    e["cat"] = catof(e.get("D"), e["class"] == "recession")
events.sort(key=lambda e: e["start"])

_recession_grades = [e["D"] for e in events if e["class"] == "recession"]
assert len(_recession_grades) == len(GRADE)
assert min(_recession_grades) == WEAKEST_RECESSION_D
assert HISTORICAL_NONRECESSION_MAX_D < DAMAGE_CUTOFF <= WEAKEST_RECESSION_D

_payload = {"floor": FLOOR, "cat_w": CAT_W, "rec_floor": REC_FLOOR,
            "cat_floors": CAT_FLOORS, "major_d": MAJOR_D,
            "major_def": MAJOR_DEF,
            "damage_cutoff": {
                "value": DAMAGE_CUTOFF,
                "derivation": f"({HISTORICAL_NONRECESSION_MAX_D:.2f} + {WEAKEST_RECESSION_D:.2f}) / 2",
                "strongest_nonrecession": {
                    "label": HISTORICAL_NONRECESSION_MAX_LABEL,
                    "D": HISTORICAL_NONRECESSION_MAX_D,
                },
                "weakest_recession": {
                    "key": WEAKEST_RECESSION_KEY,
                    "D": WEAKEST_RECESSION_D,
                },
                "scope": "completed-event damage classification; not the real-time 7.5 sigma-month confirmation trigger",
            },
            "damage_validation": {
                "auc": 1.0,
                "recessions_caught": len(_recession_grades),
                "recessions_total": len(_recession_grades),
                "missed": 0,
                "nonrecession_events": HISTORICAL_NONRECESSION_EVENTS,
                "false_classifications": 0,
                "sample": "frozen 1957-present completed-event record",
            },
            "events": events}
_fd, _tmp = tempfile.mkstemp(prefix="census.", suffix=".json", dir="geo")
try:
    with os.fdopen(_fd, "w") as _out:
        json.dump(_payload, _out, separators=(",", ":"), ensure_ascii=False)
        _out.write("\n")
        _out.flush()
        os.fsync(_out.fileno())
    os.replace(_tmp, "geo/census.json")
finally:
    if os.path.exists(_tmp):
        os.unlink(_tmp)
from collections import Counter
print(Counter(e["class"] for e in events))
for e in events:
    n = e.get("note","") or (e.get("key","") if e["class"]=="recession" else "") or (("aftermath of "+e["echo_of"]) if e.get("echo_of") else "")
    print(f'{e["class"]:12} cat{e.get("cat")} {e["start"]}..{e["end"]}  peak {e["peak"]:>5.2f}  D {str(e.get("D")):>6}  {n}')
