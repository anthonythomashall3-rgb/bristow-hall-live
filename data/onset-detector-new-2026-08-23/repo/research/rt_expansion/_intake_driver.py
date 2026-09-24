"""B-INTAKE-RT-1 driver: run the intake validator on the real registry and emit
reservation DRAFTS + tranche plan to research/ staging. No store/config writes."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from live_data.rmv2_live.rt_intake_validator import run_intake

RT = ROOT / "research" / "rt_expansion"
registry = json.load(open(RT / "registry.v1.json"))
entries = registry["entries"]

rank = list(csv.DictReader(open(RT / "landing_rank.v2.csv")))
by_cid = {r["candidate_id"]: r for r in rank}

# verdict_map from landing_rank.v2 (the authoritative intake order/verdicts).
verdict_map = {}
for r in rank:
    verdict_map[r["candidate_id"]] = {
        "dedup": r["dedup_verdict"],
        "eligible": r["eligible_for_landing"] == "True",
        "flagged": r["flagged_rights"] == "True",
    }

result = run_intake(entries, verdict_map)

# Draft output (staging only).
out = {
    "schema_version": "rmv2.rt-intake.reservation-drafts.v1",
    "authority": "B-INTAKE-RT-1; registry.v1.json (188, FINAL); "
                 "landing_rank.v2.csv; CH-R74 + CH-R74-B briefs; "
                 "OWNER_RULING_20260806_RIGHTS_ALL_CHANNELS.md",
    "note": "DRAFTS ONLY. Not written to planned_sources.v1.json. Each draft's "
            "coverage family is unregistered; writing requires a family "
            "admission into external_source_registry.csv (registered-family-"
            "subset invariant, tests/test_rmv2_source_matrix.py L398-403).",
    "counts": dict(result.counts),
    "n_reservation_drafts": len(result.reservations),
    "reservations": result.reservations,
    "rejections": [
        {"candidate_id": c, "reason": rc, "detail": d}
        for (c, rc, d) in result.rejections
    ],
}
(RT / "reservation_drafts.v1.json").write_text(
    json.dumps(out, indent=1, ensure_ascii=False))

# Split drafts for reporting.
from collections import Counter
role_ct = Counter(r["role"] for r in result.reservations)
status_ct = Counter(r["registry_status"] for r in result.reservations)

print("COUNTS", dict(result.counts))
print("N_DRAFTS", len(result.reservations))
print("ROLE", dict(role_ct))
print("STATUS", dict(status_ct))
print("N_REJECT", len(result.rejections))
rej_ct = Counter(rc for (_, rc, _) in result.rejections)
print("REJECT_BY", dict(rej_ct))

# Sanity: every draft field-order matches schema.
from live_data.rmv2_live.rt_intake_validator import PLANNED_SOURCE_FIELDS
bad = [r["source_id"] for r in result.reservations
       if tuple(r) != PLANNED_SOURCE_FIELDS]
print("BAD_FIELD_ORDER", bad)

# Registered-family check: how many draft families already registered?
reg = set(row["source_id"] for row in csv.DictReader(
    open(ROOT / "data_vault" / "catalog" / "external_source_registry.csv")))
draft_fams = set()
for r in result.reservations:
    draft_fams.update(r["coverage_source_family_ids"])
already = draft_fams & reg
print("DRAFT_FAMILIES", len(draft_fams), "ALREADY_REGISTERED", len(already),
      sorted(already))
