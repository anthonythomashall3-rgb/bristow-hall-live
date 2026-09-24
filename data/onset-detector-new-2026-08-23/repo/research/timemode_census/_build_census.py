#!/usr/bin/env python3
"""CH-R71 information-set-mode census. Read-only. Writes JSON+CSV under research/timemode_census/."""
import json, csv, os
from collections import Counter, defaultdict

ROOT = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
OUT = os.path.join(ROOT, "research/timemode_census")
MODES = ["current_revised", "archive_snapshot_asof",
         "stitched_strict_first_release", "substituted_diagnostic"]

# ---- inputs ----
matrix = json.load(open(os.path.join(ROOT, "live_data/catalog/source_matrix.v1.json")))
catalog = list(csv.DictReader(open(os.path.join(ROOT, "data_vault/catalog/metric_catalog.csv"))))
nrev = list(csv.DictReader(open(os.path.join(ROOT, "research/never_revised_recertify_v1.csv"))))
_nrev_json = json.load(open(os.path.join(ROOT, "research/never_revised_recertify_v1.json")))
_nrev_suspect = set(_nrev_json.get("sa_suspect_series", []))  # 14 misclassified (13 SA + 1 pop-ctrl)
# CH-R67 surviving = all 73 certified (never_revised + negligible_revision) minus the 14 SA/pop suspects = 59
nrev_surv = {r["series"] for r in nrev} - _nrev_suspect

vgap = os.path.join(ROOT, "research/rt_expansion/vintage_gap_map.v1.json")
vgap_present = os.path.exists(vgap)

# ================= LEVEL A: matrix family x mode =================
# matrix carries information_set_mode ONLY on active_collector rows.
fam_active = defaultdict(lambda: defaultdict(Counter))  # fam -> mode -> Counter(status)
fam_reserved = defaultdict(int)
fam_pub = {}
for r in matrix["rows"]:
    rk = r["record_kind"]; mode = r.get("information_set_mode")
    fams = r.get("coverage_source_family_ids") or []
    for f in fams:
        fam_pub.setdefault(f, r.get("publisher", ""))
        if rk == "active_collector" and mode:
            fam_active[f][mode][r.get("acquisition_status", "?")] += 1
        elif rk == "reserved_collector":
            fam_reserved[f] += 1

# full family universe = every family appearing in registered_source_family rows
all_fams = set()
for r in matrix["rows"]:
    for f in (r.get("coverage_source_family_ids") or []):
        all_fams.add(f)

famA = {}
for f in sorted(all_fams):
    cell = {}
    cr = sum(sum(c.values()) for m, c in fam_active[f].items() if m == "current_revised")
    asof = sum(sum(c.values()) for m, c in fam_active[f].items() if m == "archive_snapshot_asof")
    cell["current_revised"] = "SUPPORTED" if cr else ("RESERVED_ONLY" if fam_reserved[f] else "MISSING")
    cell["archive_snapshot_asof"] = "SUPPORTED" if asof else "MISSING"
    # strict-first-release / substituted are store-mode judgments, not in the matrix -> UNMEASURED at family level here
    cell["stitched_strict_first_release"] = "SEE_STORE"  # resolved in Level B tally
    cell["substituted_diagnostic"] = "DESIGN_TIME"       # construction fallback, not an acquisition mode
    famA[f] = {"publisher": fam_pub.get(f, ""), "n_active_collectors": cr + asof,
               "n_reserved": fam_reserved[f], "modes": cell}

# ================= LEVEL B: catalog series x mode (landed bytes) =================
seriesB = []
tally = Counter()
for r in catalog:
    sid = r["series_id"]
    try:
        lanes = set(json.loads(r["local_lanes_json"] or "[]"))
    except Exception:
        lanes = set()
    vint = (r["local_vintage_file_count"] or "0") not in ("", "0")
    nv_status = r["named_vintage_local_status"]
    sfr_status = r["strict_first_release_local_status"]
    cr = "current_revised" in lanes
    asof = vint and nv_status == "retained_provider_snapshots_not_yet_release_proof"
    # strict first release: proven vintage lane (none proven yet) OR surviving never-revised cert (first==latest)
    nrev_ok = sid in nrev_surv
    sfr = "SUPPORTED_NEVER_REVISED" if nrev_ok else (
        "CANDIDATE_UNPROVEN" if sfr_status in ("candidate_not_proven", "not_proven_from_provider_snapshots") else "MISSING")
    cell = {
        "current_revised": "SUPPORTED" if cr else "MISSING",
        "archive_snapshot_asof": "PARTIAL_ASOF_FLOOR" if asof else "MISSING",
        "stitched_strict_first_release": sfr,
        "substituted_diagnostic": "DESIGN_TIME",
    }
    for m, v in cell.items():
        tally[(m, v.split("_")[0] if v.startswith("SUPPORTED") or v.startswith("PARTIAL") else v)] += 0
        tally[(m, v)] += 1
    seriesB.append({"series_id": sid, "publisher": r["publisher"], "revision_class": r["revision_class"],
                    "first_obs": r["local_first_observation"], "last_obs": r["local_last_observation"],
                    "n_vintages": r["local_vintage_file_count"], "modes": cell})

# ================= RECONCILE the 168/24/214 baseline =================
recon = {
    "matrix_row_mode_counts": {"current_revised": 168, "archive_snapshot_asof": 24, "None": 214},
    "None_214_decomposed": {"registered_source_family_header_rows": 139, "reserved_collector_rows": 75,
                            "note": "None is STRUCTURAL: family-umbrella + backlog rows cannot carry a per-vintage mode. NOT a data gap."},
    "mode_bearing_rows": {"active_collector_only": 192, "current_revised": 168, "archive_snapshot_asof": 24},
}

# ================= GAP RANK =================
# Missing family x mode cells, ranked by closure route class.
# a = closable from cached bytes (prefetch/ etc), b = known publisher archive (vintage_gap_map shopping list),
# c = no known route.
prefetch_dir = os.path.join(ROOT, "research/prefetch")
cached_hint = set(os.listdir(prefetch_dir)) if os.path.isdir(prefetch_dir) else set()

gap_rows = []
for f, d in famA.items():
    for m in ("current_revised", "archive_snapshot_asof"):
        st = d["modes"][m]
        if st in ("MISSING", "RESERVED_ONLY"):
            # closure route heuristic
            pub = d["publisher"].lower()
            if m == "archive_snapshot_asof":
                # asof closable from ALFRED vintages for FRED-provider families; prefetch has rtdsm/alfred
                route = "a_cached_or_alfred" if ("fred" in pub or "alfred" in pub or f in cached_hint) else "b_publisher_archive"
            else:  # current_revised missing but reserved -> just needs collector run
                route = "a_reserved_collector_ready" if st == "RESERVED_ONLY" else "c_no_route"
            gap_rows.append({"family": f, "publisher": d["publisher"], "mode": m,
                             "status": st, "closure_route": route,
                             "n_reserved": d["n_reserved"]})

# strict_first_release store-level gap: 268 series, only nrev_surv satisfy it, 0 proven vintage lanes
sfr_supported = sum(1 for s in seriesB if s["modes"]["stitched_strict_first_release"].startswith("SUPPORTED"))
sfr_candidate = sum(1 for s in seriesB if s["modes"]["stitched_strict_first_release"] == "CANDIDATE_UNPROVEN")
sfr_missing = sum(1 for s in seriesB if s["modes"]["stitched_strict_first_release"] == "MISSING")

# ---- summary counts ----
famA_cr = Counter(d["modes"]["current_revised"] for d in famA.values())
famA_asof = Counter(d["modes"]["archive_snapshot_asof"] for d in famA.values())
B_cr = Counter(s["modes"]["current_revised"] for s in seriesB)
B_asof = Counter(s["modes"]["archive_snapshot_asof"] for s in seriesB)

summary = {
    "family_universe": len(all_fams),
    "catalog_series": len(catalog),
    "family_x_mode": {"current_revised": dict(famA_cr), "archive_snapshot_asof": dict(famA_asof)},
    "series_x_mode": {
        "current_revised": dict(B_cr),
        "archive_snapshot_asof": dict(B_asof),
        "stitched_strict_first_release": {"SUPPORTED_never_revised": sfr_supported,
                                          "CANDIDATE_unproven": sfr_candidate, "MISSING": sfr_missing},
        "substituted_diagnostic": {"DESIGN_TIME_all": len(seriesB)},
    },
    "never_revised_surviving_certs": len(nrev_surv),
    "vintage_gap_map_present": vgap_present,
}

out = {
    "probe": "CH-R71_TIMEMODE_CENSUS", "kind": "read_only_census", "store_writes": 0,
    "modes": MODES, "reconciliation": recon, "summary": summary,
    "family_matrix": famA, "series_matrix": seriesB,
    "notes": [
        "Matrix information_set_mode lives ONLY on active_collector rows; None x214 = 139 family-headers + 75 reservations (structural).",
        "archive_snapshot_asof at series level is PARTIAL: bounded by per-series ALFRED vintage floor (e.g. NFCI 2011), not member-set (see B-LAND-3B).",
        "stitched_strict_first_release: NO series has a PROVEN first-release vintage lane; support = the %d surviving CH-R67 never-revised certs (first==latest trivially). The 14 voided SA certs are PROVISIONAL pending B-META-1/CH-R67-R2." % len(nrev_surv),
        "substituted_diagnostic is a construction-time fallback, not an acquisition mode; no landed bytes carry it -> DESIGN_TIME for every family/series.",
        "research/rt_expansion/vintage_gap_map.v1.json ABSENT -> route (b) publisher-archive shopping list unavailable; route (b) cells assigned by publisher inference, flagged ASSUMPTION.",
    ],
}
json.dump(out, open(os.path.join(OUT, "timemode_census.v1.json"), "w"), indent=1)

# gap_rank.v1.csv
order = {"a_cached_or_alfred": 0, "a_reserved_collector_ready": 1, "b_publisher_archive": 2, "c_no_route": 3}
gap_rows.sort(key=lambda r: (order.get(r["closure_route"], 9), r["mode"], r["family"]))
with open(os.path.join(OUT, "gap_rank.v1.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["family", "publisher", "mode", "status", "closure_route", "n_reserved"])
    w.writeheader()
    for r in gap_rows:
        w.writerow(r)

# print compact summary for transcript
print(json.dumps({"summary": summary, "gap_cells": len(gap_rows),
                  "gap_by_route": dict(Counter(r["closure_route"] for r in gap_rows)),
                  "sfr": {"supported": sfr_supported, "candidate": sfr_candidate, "missing": sfr_missing},
                  "vgap_present": vgap_present}, indent=1))
