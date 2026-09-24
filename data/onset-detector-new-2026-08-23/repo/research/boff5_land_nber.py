"""B-OFFLINE-5 - land the NBER Macrohistory REMAINDER top tranche as frozen-
archival offline-current EVIDENCE lanes, one source per .dat file.

B-OFFLINE-2 item 5. GATE satisfied: B-OFFLINE-4_NBER_CENTURY is COMPLETE. Reuses
the B-OFFLINE-4 adapter (nber_macrohistory_dat) and the already-registered
nber_macrohistory registry family VERBATIM - this batch adds MORE series to the
same family, registers no new family, changes no adapter code.

Owner ruling carried by the batch (2026-08-06): each series lands under its OWN
NBER_* id, NEVER aliased/merged/spliced to a modern twin (S16's call, not
acquisition), class RESEARCH/NEAR, enabled:false + archival:true,
substituted_diagnostic, out-of-sample validation scope only (product timeline
1948->today) so nothing here reaches the headline.

Ranking = research/nber_remainder_ranking_v1.csv (CH-R50: episodes x cadence x
parse cost). We take the top N clean monthly rows in the ranking's existing sort
order; the remainder stays enumerated with the ranking intact so the next batch
resumes at row N+1. Units/title/coverage are parsed from the sibling codebook
.txt (authoritative), never fabricated.

Zero network. The cache .dat bytes ARE the source object (sha-manifested from the
CH-R27 prefetch). Converge via ONE TARGETED zero-network refresh of the newly-
bound DISABLED sources only (never a full refresh - the B-OFFLINE-2 incident),
which republishes the generation AND writes operational_status in the same step
(the B-LAND-3D gotcha).
"""
import argparse
import csv
import hashlib
import json
import os
import re
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
RANKING = ROOT / "research/nber_remainder_ranking_v1.csv"
AS_OF = "2026-08-06T12:00:00Z"

# the 7 already landed by B-OFFLINE-4 (defensive: they are NOT in the ranking csv,
# but gate them out anyway so a re-run can never double-land).
LANDED = frozenset(("m13002", "m01130a", "m01135a", "m03030",
                    "m13001", "m06001a", "m06002b"))

FIREWALL = (
    "Own NBER_* id, NEVER aliased/merged/spliced to a modern twin; never-revised "
    "closed historical compilation; out-of-sample VALIDATION SCOPE ONLY (product "
    "timeline 1948->today per owner ruling), does not reach the headline display. "
    "Whether it joins any modern series is S16's call, not acquisition."
)


def _manifest_index():
    index = {}
    with open(MANIFEST, newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 8:
                continue
            chapter, filename, kind, url, fetch_utc, status, nbytes, sha = row[:8]
            if kind != "dat":
                continue
            key = (chapter, filename)
            rec = {"url": url, "fetch_utc": fetch_utc, "bytes": int(nbytes), "sha256": sha}
            if key in index:
                prior = index[key]
                if prior["sha256"] != rec["sha256"] or prior["bytes"] != rec["bytes"]:
                    raise SystemExit("MANIFEST BYTES CONFLICT for %s: %r vs %r" % (key, prior, rec))
                if rec["fetch_utc"] < prior["fetch_utc"]:
                    prior["fetch_utc"] = rec["fetch_utc"]
                continue
            index[key] = rec
    return index


def _codebook(chapter, file_id):
    """Parse the authoritative sibling codebook for units/title/coverage. STOP
    (skip) a series whose codebook lacks a clean UNITS line - never fabricate."""
    path = CACHE_ROOT / "docs" / chapter / ("%s.txt" % file_id)
    if not path.exists():
        return None
    txt = path.read_text(errors="replace")

    def grab(key):
        m = re.search(r"%s:\s*(.+)" % re.escape(key), txt)
        if not m:
            return None
        return m.group(1).strip().rstrip('"').strip()

    units = grab("UNITS")
    if not units:
        return None
    return {
        "units": units,
        "sa": grab("SEASONAL ADJUSTMENT"),
        "mcov": grab("MONTHLY COVERAGE"),
    }


def _cache_manifest_for(file_id, chapter, mindex):
    path = CACHE_ROOT / "data" / chapter / ("%s.dat" % file_id)
    if not path.exists():
        return None, None, "NODAT"
    body = path.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    rec = mindex.get((chapter, "%s.dat" % file_id))
    if rec is None:
        return None, None, "NOMANIFEST"
    if sha != rec["sha256"]:
        return None, None, "SHAMISMATCH"
    if len(body) != rec["bytes"]:
        return None, None, "LENMISMATCH"
    manifest = {
        "fetch_utc": rec["fetch_utc"],
        "source_bytes_length": len(body),
        "source_sha256": sha,
        "url": rec["url"],
    }
    return body, manifest, "OK"


def _series_id(file_id):
    return "NBER_" + file_id.upper()


def _source(file_id, chapter, title, units, coverage):
    series_id = _series_id(file_id)
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
            "substituted_diagnostic; %s B-OFFLINE-5]"
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
            "unit": units,
            "label": "%s, NBER Macrohistory %s (chapter %s). %s" % (
                title, file_id, chapter, FIREWALL),
        },
        "source_id": "nber_macrohistory_%s" % file_id,
        "value_status": "actual",
    }


def _candidates(n):
    rows = list(csv.DictReader(open(RANKING)))
    picked = []
    skipped = []
    for r in rows:
        if len(picked) >= n:
            break
        fid = r["id"]
        ch = r["chapter"]
        if fid in LANDED:
            continue
        if r["corrupt"] != "0" or r["freq"] != "M":
            skipped.append((fid, "not_clean_monthly"))
            continue
        picked.append(r)
    return picked, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    mindex = _manifest_index()
    picked, skipped = _candidates(a.n)

    plan = []
    rejects = []
    for r in picked:
        fid, ch = r["id"], r["chapter"]
        cb = _codebook(ch, fid)
        if cb is None:
            rejects.append((fid, "NO_UNITS_CODEBOOK"))
            continue
        body, manifest, why = _cache_manifest_for(fid, ch, mindex)
        if body is None:
            rejects.append((fid, why))
            continue
        title = r["title"].strip()
        coverage = "%s-%s" % (r["ymin"], r["ymax"])
        src = _source(fid, ch, title, cb["units"], coverage)
        plan.append((src, body, manifest, {"title": title, "units": cb["units"],
                                           "sa": cb["sa"], "coverage": coverage,
                                           "chapter": ch, "file_id": fid,
                                           "episodes": r["episodes"]}))

    if rejects:
        print("REJECTS (skipped, ranking preserved):", json.dumps(rejects))

    cfg = load_config(CFG_PATH)
    existing = {s["source_id"] for s in cfg["sources"]}
    existing_series = set()
    for s in cfg["sources"]:
        sid = (s.get("series") or {}).get("series_id")
        if sid:
            existing_series.add(sid)
    for src, _b, _m, _meta in plan:
        if src["source_id"] in existing:
            raise SystemExit("COLLISION source_id: %s" % src["source_id"])
        if src["series"]["series_id"] in existing_series:
            raise SystemExit("COLLISION series_id: %s" % src["series"]["series_id"])

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

    # clobber-proof: gate EVERY candidate against the live config BEFORE any write,
    # including the prior in-batch candidates (intra-batch collision catch).
    running = dict(cfg)
    running["sources"] = list(cfg["sources"])
    report = {}
    for src, body, _m, meta in plan:
        feed_factory._validate_source_candidate(ROOT, running, src)
        recs = normalize(src, body, AS_OF)
        avail = sum(1 for rr in recs if rr.get("value_status") != "unavailable")
        report[src["source_id"]] = {
            "series_id": src["series"]["series_id"],
            "unit": src["series"]["unit"],
            "title": meta["title"],
            "records": len(recs), "available": avail,
            "first": recs[0]["observation_period"], "last": recs[-1]["observation_period"],
        }
        running["sources"] = list(running["sources"]) + [src]
    print("GATE PASS all %d (of %d requested)." % (len(plan), a.n))
    json.dump({"report": report, "rejects": rejects, "skipped": skipped},
              open("research/BOFF5_land_plan.json", "w"), indent=1, sort_keys=True)
    print("plan -> research/BOFF5_land_plan.json  landed_count=%d total_records=%d"
          % (len(plan), sum(v["records"] for v in report.values())))

    if a.dry:
        print("DRY: gated + parsed, no writes")
        return

    bound = {}
    for src, body, manifest, _meta in plan:
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        bound[src["source_id"]] = {
            "records": oc["record_count"], "receipt": oc["receipt_sha256"],
            "latest": oc["latest_observation_period"],
        }
        print("BOUND", src["source_id"], oc["record_count"], oc["receipt_sha256"][:12])

    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + [src for src, _b, _m, _meta in plan]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]),
          "archival", sum(1 for s in raw["sources"] if s.get("archival")))

    ids = [src["source_id"] for src, _b, _m, _meta in plan]
    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=ids, due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    json.dump({"bound": bound, "report": report,
               "refresh": {"outcomes": outcomes, "pointer": pointer}},
              open("research/BOFF5_land_out.json", "w"), indent=1, default=str, sort_keys=True)


main()
