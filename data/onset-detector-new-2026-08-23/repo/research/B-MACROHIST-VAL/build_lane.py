#!/usr/bin/env python3
"""B-MACROHIST-VAL lane builder.

Parse EVERY on-disk NBER Macrohistory .dat through the reviewed contract parser
(live_data/rmv2_live/nber_macrohistory.parse_nber_macrohistory_dat) into a
separately-labelled VALIDATION_ONLY lane under research/B-MACROHIST-VAL/lane/.

Never merged into the headline. Own NBER_* ids. Sets no parameter (§22.4).
Byte-provenance taken from the CH-R27 prefetch manifest.csv (per-file sha256).
Writes results to files; prints only a summary (context diet).
"""
from __future__ import annotations
import csv, hashlib, json, os, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PREFETCH = REPO / "research/prefetch/nber_macrohistory"
DATА = PREFETCH / "data"  # noqa
DATA = PREFETCH / "data"
DOCS = PREFETCH / "docs"
OUT = REPO / "research/B-MACROHIST-VAL/lane"
NORM = OUT / "normalized"

sys.path.insert(0, str(REPO))
from live_data.rmv2_live.nber_macrohistory import (  # noqa: E402
    parse_nber_macrohistory_dat, NberMacrohistoryDataError,
)

# --- provenance: per-file sha256 from prefetch manifest.csv (dat rows only) ---
# manifest.csv columns: chapter,file,kind,url,fetch_utc,http,bytes,sha256,status
prov = {}
with open(PREFETCH / "manifest.csv", newline="") as fh:
    for row in csv.reader(fh):
        if len(row) < 9:
            continue
        chapter, fname, kind, url, futc, http, nbytes, sha, status = row[:9]
        if kind == "dat":
            prov[(chapter, fname)] = {
                "dat_sha256": sha, "fetch_utc": futc, "http": http,
                "source_bytes_length": int(nbytes) if nbytes.isdigit() else None,
                "url": url, "fetch_status": status,
            }

# --- codebook (.txt) title + UNITS extraction -------------------------------
_UNITS_RE = re.compile(r"UNITS:\s*(.+?)\s*$")
_CADENCE_RE = re.compile(r"(MONTHLY|QUARTERLY|ANNUAL) COVERAGE:\s*(.+?)\s*$")

def read_codebook(chapter: str, stem: str):
    p = DOCS / chapter / (stem + ".txt")
    title = None; units = None; coverage = {}
    if not p.exists():
        return {"title": None, "units": None, "coverage": {}, "codebook": False}
    lines = p.read_text("latin-1").splitlines()
    # strip the leading-quote fixed 'c   ...' framing
    stripped = []
    for ln in lines:
        s = ln.strip().strip('"').rstrip()
        if s.startswith("c"):
            s = s[1:]
        stripped.append(s.strip())
    for i, s in enumerate(stripped):
        m = _UNITS_RE.search(s)
        if m and units is None:
            units = m.group(1)
        m2 = _CADENCE_RE.search(s)
        if m2:
            coverage[m2.group(1).lower()] = m2.group(2)
        # title = the ALL-CAPS description line immediately above a dashes rule
        if set(s) == {"-"} and len(s) >= 3 and i > 0 and title is None:
            cand = stripped[i - 1].strip()
            if cand and cand.upper() == cand and any(ch.isalpha() for ch in cand):
                title = cand
    return {"title": title, "units": units, "coverage": coverage, "codebook": True}


def canon(stem: str) -> str:
    return "NBER_" + re.sub(r"[^A-Za-z0-9_]", "_", stem).upper()


registry = []
errors = []
parsed_ok = 0
total_obs = 0
total_nonmissing = 0
chapter_shards = {}

dat_files = sorted(DATA.rglob("*.dat"))
for dat in dat_files:
    chapter = dat.parent.name
    fname = dat.name
    stem = dat.stem
    body = dat.read_bytes()
    disk_sha = hashlib.sha256(body).hexdigest()
    p = prov.get((chapter, fname), {})
    manifest_sha = p.get("dat_sha256")
    sha_match = (manifest_sha == disk_sha) if manifest_sha else None
    cb = read_codebook(chapter, stem)
    series_id = canon(stem)
    label = cb["title"] or ("NBER Macrohistory %s" % stem)
    unit = cb["units"] or "nber_native_units_unresolved"
    cfg = {"series_id": series_id, "unit": unit, "label": label}
    rec = {
        "series_id": series_id, "chapter": chapter, "dat_file": fname,
        "dat_sha256": disk_sha, "manifest_sha256": manifest_sha,
        "sha_match": sha_match, "unit": unit, "label": label,
        "codebook_present": cb["codebook"], "scope": "VALIDATION_ONLY",
    }
    try:
        obs = parse_nber_macrohistory_dat(cfg, body)
    except NberMacrohistoryDataError as exc:
        rec["parse"] = "ERROR"
        rec["parse_error"] = str(exc)[:200]
        errors.append(rec)
        registry.append(rec)
        continue
    nonmiss = [o for o in obs if o.get("value") is not None]
    years = [int(o["observation_period"][:4]) for o in obs if o.get("observation_period")]
    rec.update({
        "parse": "OK", "obs_count": len(obs), "non_missing": len(nonmiss),
        "first_period": obs[0]["observation_period"] if obs else None,
        "last_period": obs[-1]["observation_period"] if obs else None,
        "first_year": min(years) if years else None,
        "last_year": max(years) if years else None,
        "granularity": obs[0].get("period_granularity") if obs else None,
    })
    parsed_ok += 1
    total_obs += len(obs)
    total_nonmissing += len(nonmiss)
    registry.append(rec)
    shard = chapter_shards.setdefault(chapter, [])
    shard.append({"series_id": series_id, "scope": "VALIDATION_ONLY",
                  "unit": unit, "label": label, "observations": obs})

# --- write lane -------------------------------------------------------------
NORM.mkdir(parents=True, exist_ok=True)
for chapter, series_list in sorted(chapter_shards.items()):
    with open(NORM / ("chapter_%s.jsonl" % chapter), "w") as fh:
        for s in series_list:
            fh.write(json.dumps(s, separators=(",", ":")) + "\n")

registry.sort(key=lambda r: r["series_id"])
with open(OUT / "registry.v1.json", "w") as fh:
    json.dump({
        "schema_version": "recession-monitor-v2.macrohist-validation-lane.v1",
        "scope": "VALIDATION_ONLY",
        "prohibition": (
            "§22.4 — no parameter, weight, threshold, membership, transform or "
            "dimension may EVER be set, tuned, or validated-then-adjusted from "
            "this lane. Frozen archival, out-of-sample, never merged into the "
            "headline, never carrying a real-time claim (§3.6). Same family is "
            "NOT same series (§3.1)."
        ),
        "provenance": "CH-R27 prefetch manifest.csv per-file sha256",
        "parser": "live_data/rmv2_live/nber_macrohistory.parse_nber_macrohistory_dat",
        "series_count": len(registry),
        "parsed_ok": parsed_ok,
        "parse_errors": len(errors),
        "total_observations": total_obs,
        "total_non_missing": total_nonmissing,
        "series": registry,
    }, fh, indent=1)

# --- chapter/domain summary for cluster-recurrence (use 1) ------------------
by_chapter = {}
for r in registry:
    c = by_chapter.setdefault(r["chapter"], {"series": 0, "ok": 0,
                                             "min_year": None, "max_year": None})
    c["series"] += 1
    if r.get("parse") == "OK":
        c["ok"] += 1
        fy, ly = r.get("first_year"), r.get("last_year")
        if fy is not None:
            c["min_year"] = fy if c["min_year"] is None else min(c["min_year"], fy)
        if ly is not None:
            c["max_year"] = ly if c["max_year"] is None else max(c["max_year"], ly)
with open(OUT / "chapter_summary.v1.json", "w") as fh:
    json.dump(by_chapter, fh, indent=1)

print("SERIES_TOTAL", len(registry))
print("PARSED_OK", parsed_ok)
print("PARSE_ERRORS", len(errors))
print("SHA_MISMATCH", sum(1 for r in registry if r.get("sha_match") is False))
print("SHA_UNKNOWN", sum(1 for r in registry if r.get("sha_match") is None))
print("CODEBOOK_MISSING", sum(1 for r in registry if not r["codebook_present"]))
print("TOTAL_OBS", total_obs, "NON_MISSING", total_nonmissing)
print("CHAPTERS", sorted(by_chapter))
for r in errors[:10]:
    print("ERR", r["series_id"], r.get("parse_error"))
