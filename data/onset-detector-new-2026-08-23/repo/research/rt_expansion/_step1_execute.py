"""B-INTAKE-RT-1 step 1 (owner-ruled tiered admission, 20260806~2045Z):
admit the 40 spot_confirmed A/B families + write their reservations.
Appends to external_source_registry.csv and planned_sources.v1.json. No store writes."""
import csv
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / "research" / "rt_expansion"
REG_CSV = ROOT / "data_vault" / "catalog" / "external_source_registry.csv"
PLANNED = ROOT / "live_data" / "config" / "planned_sources.v1.json"

ids = json.load(open(RT / "_step1_ids.json"))
assert len(ids) == 40, len(ids)
entries = {e["candidate_id"]: e
           for e in json.load(open(RT / "registry.v1.json"))["entries"]}
drafts = {d["source_id"]: d
          for d in json.load(open(RT / "reservation_drafts.v1.json"))["reservations"]}

ACCESS = {  # rights_class -> access_class (A/B only; never C)
    "public_domain": "A",
    "government_with_attribution": "A",
    "free_with_attribution": "B",
    "free_registration_key": "B",
}


def freq_kw(cadence):
    c = cadence.lower()
    for kw in ("daily", "weekly", "monthly", "quarterly", "annual", "hourly"):
        if kw in c:
            return kw
    return cadence.split()[0] if cadence else "unknown"


# --- 1. registry rows ---
with REG_CSV.open("r", encoding="utf-8", newline="") as fh:
    reader = csv.DictReader(fh)
    header = reader.fieldnames
    existing = list(reader)
existing_ids = {r["source_id"] for r in existing}

new_rows = []
for cid in ids:
    assert cid not in existing_ids, "collision: %s" % cid
    e = entries[cid]
    rc = e["rights_class"]
    ac = ACCESS[rc]
    assert ac in ("A", "B"), (cid, ac)
    sv = e.get("spot_verify") or {}
    notes = ("RT intake B-INTAKE-RT-1 (owner tiered-admission ruling "
             "20260806~2045Z); identity=finder_fetch+adversarial_spot_confirmed; "
             "reservation-only, not admitted for construction; "
             + (sv.get("notes", "")[:180]))
    new_rows.append({
        "schema_version": "recession-monitor-v2.external-source-registry.v1",
        "source_id": cid,
        "family": cid,
        "publisher": e["publisher"],
        "measure": e["name"],
        "frequency": freq_kw(e["cadence"]),
        "coverage": (e.get("history_start") or "UNKNOWN"),
        "typical_release_or_availability": e.get("publication_lag") or "unresolved",
        "revision_and_vintage_behavior": (
            (e.get("revision_policy_claim") or "unresolved") + " | vintage: "
            + (e.get("vintage_archive") or "unresolved")),
        "role": "construction_or_diagnostic",
        "access_class": ac,
        "rights_status": rc,
        "primary_url": e["url"],
        "notes": notes,
        "publish_class": "",
    })

# Write registry CSV back with the 40 appended (append-only, order preserved).
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
w.writeheader()
for r in existing:
    w.writerow(r)
for r in new_rows:
    w.writerow(r)
REG_CSV.write_text(buf.getvalue(), encoding="utf-8")

# --- 2. reservations ---
planned = json.load(open(PLANNED))
existing_res_ids = {s["source_id"] for s in planned["sources"]}
added = 0
for cid in ids:
    assert cid not in existing_res_ids, "res collision %s" % cid
    planned["sources"].append(drafts[cid])
    added += 1
planned["scope"]["reservation_count"] = len(planned["sources"])
PLANNED.write_text(json.dumps(planned, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")

print("registry rows appended:", len(new_rows), "-> total",
      len(existing) + len(new_rows))
print("reservations appended:", added, "-> total", len(planned["sources"]))
print("reservation_count:", planned["scope"]["reservation_count"])
from collections import Counter
print("new access_class:", dict(Counter(r["access_class"] for r in new_rows)))
print("new res status:",
      dict(Counter(drafts[c]["registry_status"] for c in ids)))
