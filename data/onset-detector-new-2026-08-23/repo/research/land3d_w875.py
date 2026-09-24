"""B-LAND-3D — land the identity-confirmed FRED-MD W875RX1 deep vintages as a
PROVIDER-TAGGED second deep lane (vintage_provider_tag=FREDMD).

Authority: director ruling _mailbox/answers/20260805T220347Z_B-LAND-3C-R2.md
(Option 2). Identity already PASSED in B-LAND-3C-R2 (corr 0.9999999991, 809
months). ALFRED already owns W875RX1.DEEPASOF* (118 vintages, floor 2010-06);
this lands the disjoint W875RX1.FREDMD.DEEPASOF* family from FRED-MD panels,
extending as-of depth back to 2000-01 (~+10.5y).
"""
import json, sys, os, argparse
sys.path.insert(0, "live_data")
from pathlib import Path
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
from rmv2_live.pipeline import RefreshPipeline
from rmv2_live import fredmd_panel as fp
from rmv2_live.offline_binding import bind_offline_vintage

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
AS_OF = "2026-08-05T00:00:00Z"
ATT = "2026-08-05T23:15:00Z"
DMIN, DMAX = "20000101", "20191231"
BASE = "W875RX1"
TAG = "FREDMD"


def source_for():
    return {
        "adapter": "fred_json_api_vintages_deep",
        "allowed_hosts": ["www.stlouisfed.org"],
        "archival": True,
        "coverage_source_ids": ["fred_md_official_panels"],
        "enabled": False,
        "endpoint": "https://www.stlouisfed.org/research/economists/mccracken/fred-databases",
        "expected_content_types": ["text/csv"],
        "frequency": "monthly",
        "information_set_mode": "archive_snapshot_asof",
        "label": ("Real personal income ex current transfer receipts "
                  "(FRED-MD monthly panel reconstructed vintage matrix, as-of "
                  "snapshots) [DEEP pre-2020 as-of window, FRED-MD provider lane]"),
        "max_bytes": 33554432,
        "method_version": "fred_w875rx1_fredmd_panel_vintages_deep.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Bank of St. Louis (McCracken FRED-MD)",
        "publisher_release_clock": ("named monthly FRED-MD panel release; "
                                    "underlying publisher release time null unless "
                                    "separately proven"),
        "rights_status": "FRED_terms_and_underlying_publisher_rights_control",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "label": "Real personal income excluding current transfer receipts",
            "series_id": BASE,
            "unit": "Billions of Chained 2017 Dollars",
        },
        "source_id": "fred_w875rx1_fredmd_panel_vintages_deep",
        "value_status": "actual",
        "vintage_provider_tag": TAG,
    }


def all_panels():
    roots = ["data_archive/additional_vintages/fred_md_official/extracted",
             "data_archive/additional_vintages/fred_md_official/current"]
    ps = []
    for r in roots:
        for dp, _, fns in os.walk(r):
            for fn in fns:
                if fn.lower().endswith(".csv"):
                    ps.append(os.path.join(dp, fn))
    return sorted(ps)


def fredmd_existing(store):
    """Existing W875RX1.FREDMD.DEEPASOF* ids already landed (empty first time)."""
    ids = set()
    h = store.read_source_head("fred_w875rx1_fredmd_panel_vintages_deep")
    if h:
        n = store.read_normalized(h["normalized_sha256"])
        for r in n["records"]:
            if r["series_id"].startswith("%s.%s.DEEPASOF" % (BASE, TAG)):
                ids.add(r["series_id"])
    return ids


def plan(store):
    panels = all_panels()
    existing = fredmd_existing(store)
    kept, excl_window, excl_coll = [], [], []
    for p in panels:
        v = fp.vintage_yyyymmdd(p)
        if not (DMIN <= v <= DMAX):
            excl_window.append(v)
            continue
        sid = "%s.%s.DEEPASOF%s" % (BASE, TAG, v)
        if sid in existing:
            excl_coll.append(v)
            continue
        kept.append(p)
    return {"kept": kept, "n_kept": len(kept),
            "n_excl_window": len(excl_window), "n_excl_coll": len(excl_coll),
            "excl_coll": excl_coll,
            "vmin": fp.vintage_yyyymmdd(kept[0]) if kept else None,
            "vmax": fp.vintage_yyyymmdd(kept[-1]) if kept else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    cfg = load_config(CFG_PATH)
    store = LiveStore(ROOT, cfg)
    store.initialize()
    pl = plan(store)
    print("W875RX1 FRED-MD lane: kept=%d (%s..%s) excl_window=%d excl_coll=%d %s"
          % (pl["n_kept"], pl["vmin"], pl["vmax"], pl["n_excl_window"],
             pl["n_excl_coll"], pl["excl_coll"]))
    if a.dry:
        json.dump({k: v for k, v in pl.items() if k != "kept"},
                  open("research/land3d_plan.json", "w"), indent=1)
        print("DRY — no writes")
        return
    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()
    src = source_for()
    oc = bind_offline_vintage(pipeline, src, pl["kept"], AS_OF, transcoder=fp)
    print("BOUND W875RX1/FREDMD records=%d series=%d receipt=%s"
          % (oc["record_count"], len(oc["landed_series"]),
             oc["receipt_sha256"][:12]))
    cfg["sources"].append(src)
    raw = json.load(open(CFG_PATH))
    raw["sources"] = cfg["sources"]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))
    snap = pipeline.build_snapshot(ATT)
    cov = pipeline.build_coverage(ATT)
    st = pipeline.build_status(ATT)
    ptr = pipeline.store.publish_generation(snap, st, cov)
    print("PUBLISHED generation", ptr.get("generation_sha256"))
    json.dump({"outcome": oc, "pointer": ptr,
               "landed_series_sample": sorted(oc["landed_series"])[:3]},
              open("research/land3d_land_out.json", "w"), indent=1)


main()
