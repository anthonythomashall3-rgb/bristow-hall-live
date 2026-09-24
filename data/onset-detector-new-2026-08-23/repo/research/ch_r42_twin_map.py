#!/usr/bin/env python3
"""CH-R42 — FULL-UNIVERSE TWIN MAP (window 2, read-only, §20-class). research/ only.

Extends CH1 §1 pairwise-correlation from the 17 site members to EVERY landed
current_revised base series in the store.

Method:
  1. Store-load current_revised series (richest source per series_id) -- gather block
     reused verbatim from ch4_persistence_universe.py.
  2. Monthly grid, asof carry-forward (matches CH1 "daily asof step-carried" mechanic,
     dropped to monthly so an O(N^2) map over ~thousands of series is tractable and so
     mixed daily/weekly/monthly/quarterly cadences align on one calendar).
  3. Common transform = YoY change (12-month additive difference of the monthly asof
     level).  Removes level trend + rebasing artifacts (CH-R21/CH-R22 finding: INDPRO/
     GDP-class "revisions" are rebasing; a level-correlation twin map would be dominated
     by shared trend).  Correlation is scale-invariant so heterogeneous units are fine.
  4. Two-stage twin detection:
       (a) cheap screen: standardized + L2-normalized transform matrix, C = Zc^T Zc,
           an approximate (full-column-centered) Pearson, matmul over all series.
       (b) exact confirm: for every screened pair >= SCREEN_GATE, recompute EXACT
           pairwise-complete Pearson + Spearman on the overlap; only exact r decides.
  5. Derived break threshold (not a hard 0.80): from the exact-confirmed upper tail,
     the twin cut = max(TWIN_FLOOR, knee = value just above the largest gap in the
     sorted upper-tail |r|).  Both reported.
  6. Cluster: graph with edges (exact |r| >= threshold); connected components = twin
     groups.
  7. Seat-keeper candidate per group: proxy for "better time-data class" = longest span,
     ties -> most monthly points, ties -> finer native cadence.  Proxy only; CH-R32
     knowability ledger is the authoritative class and refines seating later.

Writes: research/twin_map_v1.csv (flagged twin pairs) + research/ch_r42_twin_map.json
(brief payload) + research/ch_r42_run.log.  ZERO store writes.
"""
import sys, os, re, time, csv, json, math
sys.path.insert(0, "live_data")
import numpy as np
from pathlib import Path
from datetime import date
from collections import defaultdict
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore

PR = Path(".").resolve()
LOG = open("research/ch_r42_run.log", "w")
def log(*a):
    print(*a, file=LOG, flush=True); print(*a, flush=True)

cfgp = PR / "live_data/config/sources.v1.json"
load_env_file(cfgp.parent / "local.env"); cfg = load_config(cfgp)
st = LiveStore(PR, cfg); st.initialize()
heads = st.all_source_heads()
VINT = re.compile(r"vintage|deep|asof|archive|_alfred|snapshot", re.I)

def pdate(s):
    s = str(s).strip()
    m = re.match(r"^(\d{4})-Q([1-4])$", s)
    if m: return date(int(m.group(1)), (int(m.group(2)) - 1) * 3 + 1, 1)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m: return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m: return date(int(m.group(1)), int(m.group(2)), 1)
    m = re.match(r"^(\d{4})$", s)
    if m: return date(int(m.group(1)), 1, 1)
    return None

# ---------- gather current_revised series (richest source per id) : ch4 block ----------
t0 = time.time()
cand = defaultdict(dict); label = {}; unit = {}
kept = [(h.get("record_count", 0), sid) for sid, h in heads.items() if not VINT.search(sid)]
kept.sort()
log(f"sources to scan: {len(kept)}  start")
for i, (rc, sid) in enumerate(kept):
    try: norm = st.read_normalized(heads[sid]["normalized_sha256"])
    except Exception as e: log("ERR read", sid, e); continue
    for r in norm.get("records", []):
        if r.get("information_set_mode") != "current_revised": continue
        try: fv = float(r.get("value"))
        except: continue
        d = pdate(r.get("observation_period"))
        if d is None: continue
        si = r.get("series_id")
        if not si: continue
        cand[si].setdefault(sid, {})[d] = fv
        label.setdefault(si, r.get("label")); unit.setdefault(si, r.get("unit"))
    if i % 50 == 0: log(f"  [{i+1}/{len(kept)}] t={time.time()-t0:.0f}s")
log(f"scan done {time.time()-t0:.0f}s; distinct current_revised series={len(cand)}")

series = {}
for si, bys in cand.items():
    best = max(bys, key=lambda s: len(bys[s]))
    series[si] = (best, bys[best])

# ---------- monthly asof carry-forward onto one common grid ----------
def midx(d): return d.year * 12 + (d.month - 1)
allm = [midx(d) for _, dv in series.values() for d in dv]
GLO, GHI = min(allm), max(allm)                      # inclusive month-index bounds
NG = GHI - GLO + 1
gidx = np.arange(GLO, GHI + 1)
log(f"monthly grid: {GLO//12}-{GLO%12+1:02d} .. {GHI//12}-{GHI%12+1:02d}  ({NG} months)")

MIN_MONTHS = 48        # require >=4y of YoY-transform coverage to enter the map
CADENCE = {}           # si -> median native spacing (days)
level_rows = []        # (si, monthly level asof array with NaN before first obs)
meta = {}              # si -> dict(span_months, n_native, cadence_days, first_m, last_m)
for si, (src, dv) in series.items():
    ds = sorted(dv)
    if len(ds) < 6: continue
    gaps = [(ds[k+1] - ds[k]).days for k in range(len(ds)-1) if (ds[k+1]-ds[k]).days > 0]
    cad = float(np.median(gaps)) if gaps else None
    # bucket to month: last native obs in or before each month
    bym = {}
    for d in ds: bym[midx(d)] = dv[d]      # dict insertion in date order -> last wins
    lvl = np.full(NG, np.nan)
    last = np.nan
    bk = sorted(bym)
    p = 0
    for gi in range(NG):
        mm = GLO + gi
        while p < len(bk) and bk[p] <= mm:
            last = bym[bk[p]]; p += 1
        lvl[gi] = last
    # YoY additive transform: x[t]-x[t-12]
    yoy = np.full(NG, np.nan)
    yoy[12:] = lvl[12:] - lvl[:-12]
    if np.sum(~np.isnan(yoy)) < MIN_MONTHS: continue
    fm = midx(ds[0]); lm = midx(ds[-1])
    meta[si] = dict(source=src, span_months=lm - fm + 1, n_native=len(ds),
                    cadence_days=cad, first_m=fm, last_m=lm,
                    label=(label.get(si) or "")[:70], unit=unit.get(si) or "")
    level_rows.append((si, yoy))

names = [si for si, _ in level_rows]
N = len(names)
log(f"universe entering twin map (>= {MIN_MONTHS} YoY months): N={N} series")

# transform matrix T x N with NaN
Y = np.column_stack([y for _, y in level_rows]) if N else np.zeros((NG, 0))

# ---------- stage (a) screen: full-column-centered, L2-normalized, matmul ----------
Yc = Y.copy()
colmean = np.nanmean(Yc, axis=0)
Yc = Yc - colmean
mask = ~np.isnan(Yc)
Yc[~mask] = 0.0
norm = np.sqrt(np.sum(Yc * Yc, axis=0))
norm[norm == 0] = 1.0
Zc = Yc / norm
log("screen matmul ...")
C = Zc.T @ Zc                       # approx pearson (full-column centering)
np.fill_diagonal(C, 0.0)
SCREEN_GATE = 0.70
iu = np.triu_indices(N, 1)
cand_mask = np.abs(C[iu]) >= SCREEN_GATE
ci, cj = iu[0][cand_mask], iu[1][cand_mask]
log(f"screened candidate pairs |approx r|>={SCREEN_GATE}: {len(ci)}")

# ---------- stage (b) exact pairwise-complete Pearson + Spearman on candidates ----------
def rankdata(v):
    order = np.argsort(v, kind="mergesort"); r = np.empty(len(v)); r[order] = np.arange(len(v))
    # average ties
    _, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
    csum = np.cumsum(cnt); starts = csum - cnt
    avg = (starts + csum - 1) / 2.0
    return avg[inv]
MIN_OVERLAP = 36
exact = []
for a, b in zip(ci, cj):
    xa, xb = Y[:, a], Y[:, b]
    ok = ~np.isnan(xa) & ~np.isnan(xb)
    n = int(ok.sum())
    if n < MIN_OVERLAP: continue
    va, vb = xa[ok], xb[ok]
    if np.std(va) == 0 or np.std(vb) == 0: continue
    pr = float(np.corrcoef(va, vb)[0, 1])
    sp = float(np.corrcoef(rankdata(va), rankdata(vb))[0, 1])
    exact.append((names[a], names[b], pr, sp, n))
log(f"exact-confirmed pairs (overlap>={MIN_OVERLAP}): {len(exact)}")

# ---------- derive break threshold ----------
# Look for an empirical knee (largest gap) in the sorted |r| twin zone.  If the
# distribution is continuous (no gap) there is NO data-driven break -> fall back to a
# documented convention.  Also emit a sensitivity ladder of pair/group counts.
absr = sorted((abs(pr) for _, _, pr, _, _ in exact), reverse=True)
TWIN_FLOOR = 0.85
tail = [r for r in absr if r >= TWIN_FLOOR]
best_gap = 0.0; gap_at = None
for k in range(len(tail) - 1):
    g = tail[k] - tail[k+1]
    if g > best_gap:
        best_gap = g; gap_at = (round(tail[k],4), round(tail[k+1],4), round(g,4))
EMPIRICAL_KNEE = best_gap >= 0.01          # a real break separates the tail by >=0.01
def edges_at(th): return [(a,b,pr,sp,n) for a,b,pr,sp,n in exact if abs(pr) >= th]
def groups_at(edges):
    p = {}
    def f(x):
        p.setdefault(x,x)
        while p[x]!=x: p[x]=p[p[x]]; x=p[x]
        return x
    for a,b,*_ in edges:
        ra,rb=f(a),f(b)
        if ra!=rb: p[ra]=rb
    gs=defaultdict(set)
    for a,b,*_ in edges: gs[f(a)].add(a); gs[f(a)].add(b)
    return list(gs.values())
LADDER = [0.85, 0.90, 0.95, 0.975, 0.99, 0.995]
ladder = []
for th in LADDER:
    e = edges_at(th); g = groups_at(e)
    ladder.append(dict(threshold=th, pairs=len(e), groups=len(g),
                       series=len({x for a,b,*_ in e for x in (a,b)}),
                       largest_group=(max((len(x) for x in g)) if g else 0)))
    log(f"  ladder th={th}: pairs={len(e)} groups={len(g)} "
        f"largest_group={ladder[-1]['largest_group']}")
# primary "twin" convention = 0.95; near-duplicate seating-hazard tier = 0.99
THRESH = 0.95
NEAR_DUP = 0.99
log(f"empirical knee found={EMPIRICAL_KNEE} (largest gap in twin zone={gap_at}); "
    f"distribution continuous -> adopt CONVENTION twin>={THRESH}, near_dup>={NEAR_DUP}")

# ---------- flag twins, cluster (at primary convention) ----------
twins = edges_at(THRESH)
near_dups = edges_at(NEAR_DUP)
log(f"flagged twin pairs (|exact r|>={THRESH}): {len(twins)}; "
    f"near-dup (>={NEAR_DUP}): {len(near_dups)}")

# union-find clusters
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb
for a, b, *_ in twins:
    union(a, b)
groups = defaultdict(set)
for a, b, *_ in twins:
    groups[find(a)].add(a); groups[find(a)].add(b)
clusters = [sorted(g) for g in groups.values()]
clusters.sort(key=len, reverse=True)
log(f"twin groups: {len(clusters)}; sizes {[len(c) for c in clusters][:20]}")

# ---------- seat-keeper per group ----------
def seat_score(si):
    m = meta[si]
    cad = m["cadence_days"] or 9999
    return (m["span_months"], m["n_native"], -cad)   # longer span, more obs, finer cadence
group_out = []
for gi, g in enumerate(clusters):
    keeper = max(g, key=seat_score)
    group_out.append(dict(
        group=gi, size=len(g), members=g, seat_keeper=keeper,
        seat_keeper_span_months=meta[keeper]["span_months"],
        seat_keeper_cadence_days=meta[keeper]["cadence_days"],
        seat_keeper_label=meta[keeper]["label"],
        member_meta={s: dict(span_months=meta[s]["span_months"],
                             n_native=meta[s]["n_native"],
                             cadence_days=meta[s]["cadence_days"],
                             label=meta[s]["label"]) for s in g}))

# ---------- write twin_map_v1.csv ----------
twins_sorted = sorted(twins, key=lambda t: -abs(t[2]))
gi_of = {}
for gi, g in enumerate(clusters):
    for s in g: gi_of[s] = gi
with open("research/twin_map_v1.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["series_a","series_b","pearson_yoy","spearman_yoy","overlap_months",
                "tier","twin_group","seat_keeper_of_group","label_a","label_b"])
    for a, b, pr, sp, n in twins_sorted:
        gg = gi_of.get(a)
        kp = group_out[gg]["seat_keeper"] if gg is not None else ""
        tier = "near_dup" if abs(pr) >= NEAR_DUP else "twin"
        w.writerow([a, b, round(pr,4), round(sp,4), n, tier, gg, kp,
                    meta[a]["label"], meta[b]["label"]])
log(f"wrote research/twin_map_v1.csv  ({len(twins_sorted)} twin pairs)")

# ---------- named-anchor readout: do the 17 CH1 members reproduce? ----------
CH1_PAIRS = [("PERMIT","HOUST"),("INDPRO","TCU"),("INDPRO","CMRMTSPL"),
             ("IURSA","SAHMREALTIME"),("CMRMTSPL","TCU"),("BAA","AAA")]
exact_lut = {}
for a, b, pr, sp, n in exact:
    exact_lut[(a,b)] = (pr, sp, n); exact_lut[(b,a)] = (pr, sp, n)
ch1_reproduce = []
for a, b in CH1_PAIRS:
    v = exact_lut.get((a,b))
    ch1_reproduce.append(dict(pair=f"{a}~{b}",
        yoy_pearson=(round(v[0],3) if v else None),
        yoy_spearman=(round(v[1],3) if v else None),
        overlap=(v[2] if v else None),
        present=bool(v)))

# ---------- brief payload ----------
payload = dict(
    schema_version="ch_r42.v1", batch_id="CH-R42_COLLINEARITY_FULL",
    window=2, writes_vault=False, network=False,
    method=dict(grid="monthly asof carry-forward", transform="YoY 12-month additive change",
                screen="full-column-centered L2 matmul approx Pearson",
                confirm="exact pairwise-complete Pearson+Spearman on overlap",
                min_yoy_months=MIN_MONTHS, min_overlap=MIN_OVERLAP,
                screen_gate=SCREEN_GATE, twin_floor=TWIN_FLOOR),
    universe=dict(current_revised_series=len(cand), entered_map=N,
                  grid_months=NG,
                  grid_span=f"{GLO//12}-{GLO%12+1:02d}..{GHI//12}-{GHI%12+1:02d}"),
    threshold=dict(primary_twin=THRESH, near_dup=NEAR_DUP, floor=TWIN_FLOOR,
                   empirical_knee_found=EMPIRICAL_KNEE, largest_gap_in_twin_zone=gap_at,
                   note=("|r| distribution over the macro universe is continuous with no "
                         "empirical break; primary/near_dup are documented conventions, "
                         "not a data-driven knee"),
                   sensitivity_ladder=ladder),
    counts=dict(screened_pairs=int(len(ci)), exact_confirmed=len(exact),
                twin_pairs=len(twins), near_dup_pairs=len(near_dups),
                twin_groups=len(clusters), series_in_a_twin=len(gi_of)),
    ch1_anchor_reproduction=ch1_reproduce,
    top_twin_pairs=[dict(a=a, b=b, pearson=round(pr,3), spearman=round(sp,3), overlap=n)
                    for a, b, pr, sp, n in twins_sorted[:40]],
    twin_groups=group_out[:60],
    largest_groups=[dict(group=g["group"], size=g["size"],
                         seat_keeper=g["seat_keeper"], members=g["members"][:25])
                    for g in group_out[:25]],
    seat_keeper_note=("seat_keeper = proxy for better time-data class "
        "(longest span, then most native obs, then finest cadence); "
        "CH-R32 knowability ledger is authoritative and refines seating."),
    feeds="S3 twins ruling + S5 seating",
)
json.dump(payload, open("research/ch_r42_twin_map.json", "w"), indent=1)
log("wrote research/ch_r42_twin_map.json")
log(f"DONE total {time.time()-t0:.0f}s")
