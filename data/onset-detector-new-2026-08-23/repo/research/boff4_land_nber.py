"""B-OFFLINE-4 — land the NBER Macrohistory century shortlist as frozen-archival
offline-current EVIDENCE lanes, one source per .dat file (7 series).

Owner ruling carried by the batch (2026-08-06): each series lands under its OWN
NBER_* id, NEVER aliased/merged/spliced to a modern twin, class RESEARCH/NEAR,
enabled:false + archival:true, out-of-sample validation scope only (product
timeline 1948->today) so nothing here reaches the headline. Bound to the new
`nber_macrohistory` registry family (access A, role out_of_sample_validation_only,
registered this batch under the batch's explicit owner identity ruling; B-REG-1
precedent: identity already owner-ruled -> registration is mechanical in-batch).

Zero network. The cache .dat bytes ARE the source object (sha-manifested from the
CH-R27 prefetch). Converge via ONE TARGETED zero-network refresh of the 7
newly-bound DISABLED sources only (never a full refresh — the B-OFFLINE-2
incident), which republishes the generation AND writes operational_status in the
same step (the B-LAND-3D gotcha).
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "live_data")
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline
from rmv2_live import feed_factory
from rmv2_live.adapters import normalize
from rmv2_live.offline_binding import bind_offline_current

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
CACHE_ROOT = ROOT / "research/prefetch/nber_macrohistory"
MANIFEST = CACHE_ROOT / "manifest.csv"
AS_OF = "2026-08-06T09:30:00Z"

FIREWALL = (
    "Own NBER_* id, NEVER aliased/merged/spliced to a modern twin; never-revised "
    "closed historical compilation; out-of-sample VALIDATION SCOPE ONLY (product "
    "timeline 1948->today per owner ruling), does not reach the headline display. "
    "Whether it joins any modern series is S16's call, not acquisition."
)

# file_id -> (chapter, series_id, title, unit, coverage)
SHORTLIST = [
    ("m13002", "13", "NBER_M13002", "Commercial paper rates, New York City",
     "PERCENT", "1857-1971"),
    ("m01130a", "01", "NBER_M01130A", "Pig iron production",
     "THOUSANDS OF GROSS TONS", "1877-1941"),
    ("m01135a", "01", "NBER_M01135A", "Steel ingot production",
     "THOUSANDS OF LONG TONS PER AVERAGE WORKING DAY", "1899-1939"),
    ("m03030", "03", "NBER_M03030",
     "Index of freight carloadings, total, Federal Reserve Board",
     "index (FRB freight carloadings)", "1919-1953"),
    ("m13001", "13", "NBER_M13001", "Call money rates, mixed collateral, New York City",
     "PERCENT", "1857-1970"),
    ("m06001a", "06", "NBER_M06001A", "Retail trade index",
     "1919=100", "1914-1919"),
    ("m06002b", "06", "NBER_M06002B", "Index of department store sales",
     "1957-1959=100", "1919-1963"),
]


def _manifest_index():
    """dat rows keyed by (chapter, filename); assert a single consistent sha."""
    index = {}
    with open(MANIFEST, newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 9:
                continue
            chapter, filename, kind, url, fetch_utc, status, nbytes, sha, _cache = row[:9]
            if kind != "dat":
                continue
            key = (chapter, filename)
            rec = {"url": url, "fetch_utc": fetch_utc, "bytes": int(nbytes), "sha256": sha}
            if key in index:
                prior = index[key]
                # duplicate rows (fetched then cached) are fine iff the bytes agree;
                # keep the earliest fetch_utc as the acquisition timestamp.
                if prior["sha256"] != rec["sha256"] or prior["bytes"] != rec["bytes"]:
                    raise SystemExit("MANIFEST BYTES CONFLICT for %s: %r vs %r" % (key, prior, rec))
                if rec["fetch_utc"] < prior["fetch_utc"]:
                    prior["fetch_utc"] = rec["fetch_utc"]
                continue
            index[key] = rec
    return index


def _cache_manifest_for(file_id, chapter, mindex):
    path = CACHE_ROOT / "data" / chapter / ("%s.dat" % file_id)
    body = path.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    rec = mindex.get((chapter, "%s.dat" % file_id))
    if rec is None:
        raise SystemExit("NO MANIFEST ROW for %s/%s.dat" % (chapter, file_id))
    if sha != rec["sha256"]:
        raise SystemExit("SHA MISMATCH %s: cache %s vs manifest %s" % (file_id, sha, rec["sha256"]))
    if len(body) != rec["bytes"]:
        raise SystemExit("LENGTH MISMATCH %s: %d vs %d" % (file_id, len(body), rec["bytes"]))
    manifest = {
        "fetch_utc": rec["fetch_utc"],
        "source_bytes_length": len(body),
        "source_sha256": sha,
        "url": rec["url"],
    }
    return body, manifest


def _source(file_id, chapter, series_id, title, unit, coverage):
    return {
        "adapter": "nber_macrohistory_dat",
        "allowed_hosts": ["data.nber.org"],
        "archival": True,
        "coverage_source_ids": ["nber_macrohistory"],
        "enabled": False,
        "endpoint": (
            "https://data.nber.org/databases/macrohistory/rectdata/%s/%s.dat"
            % (chapter, file_id)
        ),
        "expected_content_types": ["text/plain", "application/octet-stream"],
        "frequency": "monthly",
        "information_set_mode": "substituted_diagnostic",
        "label": (
            "NBER Macrohistory %s (%s) [OFFLINE-CURRENT frozen archival; "
            "substituted_diagnostic; %s B-OFFLINE-4]"
            % (title, coverage, FIREWALL)
        ),
        "max_bytes": 200000,
        "method_version": "nber_macrohistory_offline.v1",
        "poll_seconds": 86400,
        "publisher": "National Bureau of Economic Research",
        "publisher_release_clock": "closed historical compilation; never revised",
        "rights_status": "public_research_data",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "series_id": series_id,
            "unit": unit,
            "label": "%s, NBER Macrohistory %s (chapter %s). %s" % (
                title, file_id, chapter, FIREWALL),
        },
        "source_id": "nber_macrohistory_%s" % file_id,
        "value_status": "actual",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    mindex = _manifest_index()
    plan = []
    for file_id, chapter, series_id, title, unit, coverage in SHORTLIST:
        src = _source(file_id, chapter, series_id, title, unit, coverage)
        body, manifest = _cache_manifest_for(file_id, chapter, mindex)
        plan.append((src, body, manifest))

    cfg = load_config(CFG_PATH)
    existing = {s["source_id"] for s in cfg["sources"]}
    for src, _b, _m in plan:
        if src["source_id"] in existing:
            raise SystemExit("COLLISION: %s already in config" % src["source_id"])

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

    # clobber-proof: gate EVERY candidate against the live config BEFORE any write.
    running = dict(cfg)
    running["sources"] = list(cfg["sources"])
    report = {}
    for src, body, _m in plan:
        feed_factory._validate_source_candidate(ROOT, running, src)
        recs = normalize(src, body, AS_OF)
        avail = sum(1 for r in recs if r.get("value_status") != "unavailable")
        report[src["source_id"]] = {
            "series_id": src["series"]["series_id"],
            "records": len(recs), "available": avail,
            "first": recs[0]["observation_period"], "last": recs[-1]["observation_period"],
        }
        running["sources"] = list(running["sources"]) + [src]  # gate next vs this one too
    print("GATE PASS all %d. report:" % len(plan))
    print(json.dumps(report, indent=1, sort_keys=True))

    if a.dry:
        json.dump(report, open("research/BOFF4_land_plan.json", "w"), indent=1, sort_keys=True)
        print("DRY: gated + parsed, no writes")
        return

    # bind each (writes head/status/receipt per source, no publish yet)
    bound = {}
    for src, body, manifest in plan:
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        bound[src["source_id"]] = {
            "records": oc["record_count"], "receipt": oc["receipt_sha256"],
            "latest": oc["latest_observation_period"],
        }
        print("BOUND", src["source_id"], oc["record_count"], oc["receipt_sha256"][:12])

    # append all 7 to config atomically
    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + [src for src, _b, _m in plan]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]),
          "archival", sum(1 for s in raw["sources"] if s.get("archival")))

    # ONE targeted zero-network refresh of the 7 disabled sources -> republish
    # generation (binding the archival heads) + write operational_status.
    ids = [src["source_id"] for src, _b, _m in plan]
    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=ids, due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    json.dump({"bound": bound, "report": report,
               "refresh": {"outcomes": outcomes, "pointer": pointer}},
              open("research/BOFF4_land_out.json", "w"), indent=1, default=str, sort_keys=True)


main()
