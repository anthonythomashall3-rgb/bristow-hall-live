"""B-NBER-FORK — build the DATA-only NBER business-cycle reference-date artifact,
forked directly from NBER publisher source bytes (§5.1, cited fetch), NOT from the
instrument_onset_target_ledger.v1.json.

Owner ruling OWNER Option-3 (answers/20260809T034119Z_B-TABULA-RASA-INVENTORY.md):
the NBER peak/trough dates are DATA; onset_T_star is prior model output and leaves
the live surface with the shelved ledger. This artifact carries ONLY the published
peak/trough pairs, byte-faithful. It is an EXTERNAL COMPARATOR (CLAUDE.md), never a
construction input, never a target, never a chronology of our own making.
"""
import json, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = REPO / "research/prefetch/nber_reference_cycles/business_cycle_dates.json"
META = REPO / "research/prefetch/nber_reference_cycles/FETCH.meta"
OUT = HERE / "nber_reference_cycles.v1.json"

raw = SRC.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
cycles = json.loads(raw)  # list of {"peak": "YYYY-MM-DD"|"", "trough": "YYYY-MM-DD"}
meta = dict(
    line.strip().split("=", 1) for line in META.read_text().splitlines() if "=" in line
)

# byte-faithful: preserve exactly what the publisher published, including the first
# cycle's empty peak (1854-12-01 trough only).
cyc = [{"peak": c.get("peak", ""), "trough": c.get("trough", "")} for c in cycles]
peaks = [c["peak"] for c in cyc if c["peak"]]
troughs = [c["trough"] for c in cyc if c["trough"]]

doc = {
    "schema_version": "recession_monitor_v2.nber_reference_cycles.v1",
    "artifact_id": "nber_reference_cycles.v1",
    "artifact_class": "external_comparator_data",
    "is_data_not_construction": True,
    "provenance_is_extraction_not_construction": True,
    "not_a_target": True,
    "not_a_channel_member_weight_or_threshold": True,
    "no_chronology_of_our_own_making": True,
    "onset_T_star_present": False,
    "usage_bar": (
        "External comparator only (CLAUDE.md): NBER dates are not clean construction "
        "inputs and never a fitted target. onset_T_star is NOT here; it left the live "
        "surface with the shelved instrument_onset_target_ledger.v1.json per OWNER "
        "Option-3. Validation (CH-R124 machinery, RED-tier dating grading) cites THIS "
        "artifact for NBER peak/trough, never the shelved ledger."
    ),
    "source": {
        "publisher": "National Bureau of Economic Research (NBER)",
        "url": meta.get("SOURCE_URL"),
        "fetch_stamp": meta.get("FETCH_STAMP"),
        "http": meta.get("HTTP"),
        "source_object_path": "research/prefetch/nber_reference_cycles/business_cycle_dates.json",
        "source_sha256": sha,
        "source_bytes": len(raw),
        "probe_receipt": "research/prefetch/nber_reference_cycles/PROBE_RECEIPT.v1.json",
    },
    "measured_from_bytes": {
        "record_count_cycles": len(cyc),
        "peak_count": len(peaks),
        "trough_count": len(troughs),
        "earliest_date": min(sorted(peaks + troughs)),
        "latest_date": max(sorted(peaks + troughs)),
    },
    "cycles": cyc,
    "peaks": peaks,
    "troughs": troughs,
}

data = (json.dumps(doc, indent=2) + "\n").encode()
if not OUT.exists() or OUT.read_bytes() != data:
    OUT.write_bytes(data)
    print("WROTE", OUT.relative_to(REPO), "bytes", len(data))
else:
    print("UNCHANGED", OUT.relative_to(REPO))
print("source_sha256", sha, "cycles", len(cyc), "peaks", len(peaks), "troughs", len(troughs))
