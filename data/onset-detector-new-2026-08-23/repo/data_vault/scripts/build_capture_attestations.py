#!/usr/bin/env python3
"""Regenerate the two capture attestations: data-manifest.json + source-receipt.json.

B-ATTEST-REGEN restored regenerability to two artifacts that previously had NO
generator anywhere in the tree (B-CTX-1 measured it). Because they were
hand-frozen, editing any ``method_source/**`` byte invalidated their rolling
integrity fields with no reproducible way to close them — the §24.6 state
"a derived value changed without re-running its recorded command".

CAPTURE vs ROLLING (brief steps 1-3). Each attestation carries two kinds of
field:

* CAPTURE CLAIM — a point-in-time fact about the 2026-07-29 checkout
  ``233754a`` and the original-site -> index.html byte transform. By
  definition these must NOT track later edits; the 2026-07-29 worktree is gone
  and cannot be re-measured. This generator PRESERVES them verbatim from the
  prior artifact and never recomputes them. Preserving-from-prior is the only
  honest way to keep a capture claim: it is re-scoped so ``method_source/**``
  edits cannot invalidate it.

* ROLLING INTEGRITY CLAIM — a fact about the CURRENT governed store
  (lane file/byte counts, method_source totals, the DATA_SHA256SUMS
  record_count/byte_count/sha256, and the receipt's data_package mirror of
  those). This generator RECOMPUTES these from the live store on every run.

Acceptance (brief step 3): run against the unmodified store, this reproduces
the current files byte-for-byte. That reproduction is the proof it is a
generator and not a silent replacement.

Regeneration order (§17.2, data_vault/README.md): run AFTER
build_payload_checksums.py (so DATA_SHA256SUMS is current) and BEFORE
build_handoff_manifest.py (which hashes both attestations as members).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple


MANIFEST_REL = "data-manifest.json"
RECEIPT_REL = "source-receipt.json"
SUMS_REL = "DATA_SHA256SUMS"
METHOD_SOURCE_LANE_PATH = "method_source"


def is_tree_noise(path: Path) -> bool:
    """Identical tree-noise rule to verify_data_vault.is_tree_noise and
    build_payload_checksums (B-SAFE-1 §3.3): .DS_Store, __pycache__ dirs and
    *.pyc are never governed payload bytes."""
    return (
        path.name == ".DS_Store"
        or "__pycache__" in path.parts
        or path.suffix == ".pyc"
    )


def _tree_stats(base: Path) -> Tuple[int, int]:
    file_count = 0
    byte_count = 0
    for path in base.rglob("*"):
        if path.is_file() and not is_tree_noise(path):
            file_count += 1
            byte_count += path.stat().st_size
    return file_count, byte_count


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def measure(root: Path) -> Dict[str, object]:
    """Measure every ROLLING input from the live store. The lane path/lane_id/
    semantics come from the prior manifest (they are static structure); only
    the counts here roll."""
    prior = json.loads((root / MANIFEST_REL).read_text(encoding="utf-8"))

    lanes: List[Dict[str, object]] = []
    method_source = {"file_count": 0, "byte_count": 0}
    for lane in prior["lanes"]:
        file_count, byte_count = _tree_stats(root / lane["path"])
        entry: Dict[str, object] = {
            "path": lane["path"],
            "file_count": file_count,
            "byte_count": byte_count,
        }
        if "includes_provider_vintages" in lane:
            sub = lane["includes_provider_vintages"]
            sfc, sbc = _tree_stats(root / sub["path"])
            entry["includes_provider_vintages"] = {
                "file_count": sfc,
                "byte_count": sbc,
            }
        lanes.append(entry)
        if lane["path"] == METHOD_SOURCE_LANE_PATH:
            method_source = {"file_count": file_count, "byte_count": byte_count}

    sums_bytes = (root / SUMS_REL).read_bytes()
    record_count = sum(1 for line in sums_bytes.decode("utf-8").splitlines() if line)
    sums = {
        "record_count": record_count,
        "byte_count": len(sums_bytes),
        "sha256": sha256_bytes(sums_bytes),
    }
    return {"lanes": lanes, "method_source": method_source, "sums": sums}


def _non_overlapping(measurements: Dict[str, object]) -> Dict[str, int]:
    """The data-only total: every lane summed, minus the method_source lane.
    The lanes do not overlap (includes_provider_vintages is a nested annotation
    inside current_revised_and_spatial, not a separate lane)."""
    total_files = sum(lane["file_count"] for lane in measurements["lanes"])
    total_bytes = sum(lane["byte_count"] for lane in measurements["lanes"])
    ms = measurements["method_source"]
    return {
        "file_count": total_files - ms["file_count"],
        "byte_count": total_bytes - ms["byte_count"],
    }


def assemble_manifest(prior: Dict[str, object], measurements: Dict[str, object]) -> str:
    """Pure: patch ONLY the rolling fields of the prior manifest object; every
    capture/static field passes through untouched, in its original key order."""
    obj = copy.deepcopy(prior)
    by_path = {lane["path"]: lane for lane in measurements["lanes"]}
    for lane in obj["lanes"]:
        meas = by_path[lane["path"]]
        lane["file_count"] = meas["file_count"]
        lane["byte_count"] = meas["byte_count"]
        if "includes_provider_vintages" in lane:
            sub = meas["includes_provider_vintages"]
            lane["includes_provider_vintages"]["file_count"] = sub["file_count"]
            lane["includes_provider_vintages"]["byte_count"] = sub["byte_count"]

    non_overlapping = _non_overlapping(measurements)
    obj["non_overlapping_data_totals"]["file_count"] = non_overlapping["file_count"]
    obj["non_overlapping_data_totals"]["byte_count"] = non_overlapping["byte_count"]

    obj["method_source_totals"]["file_count"] = measurements["method_source"]["file_count"]
    obj["method_source_totals"]["byte_count"] = measurements["method_source"]["byte_count"]

    sums = measurements["sums"]
    obj["integrity_manifest"]["record_count"] = sums["record_count"]
    obj["integrity_manifest"]["byte_count"] = sums["byte_count"]
    obj["integrity_manifest"]["sha256"] = sums["sha256"]

    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def assemble_receipt(
    prior: Dict[str, object], manifest_text: str, measurements: Dict[str, object]
) -> str:
    """Pure: patch ONLY the rolling data_package fields; the source-capture
    block and transformation record pass through untouched."""
    obj = copy.deepcopy(prior)
    pkg = obj["data_package"]
    pkg["manifest_sha256"] = sha256_bytes(manifest_text.encode("utf-8"))

    non_overlapping = _non_overlapping(measurements)
    pkg["data_file_count"] = non_overlapping["file_count"]
    pkg["data_byte_count"] = non_overlapping["byte_count"]

    pkg["method_source_file_count"] = measurements["method_source"]["file_count"]
    pkg["method_source_byte_count"] = measurements["method_source"]["byte_count"]

    sums = measurements["sums"]
    pkg["sha256sums_record_count"] = sums["record_count"]
    pkg["sha256sums_sha256"] = sums["sha256"]

    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def build_manifest_text(root: Path) -> str:
    prior = json.loads((root / MANIFEST_REL).read_text(encoding="utf-8"))
    return assemble_manifest(prior, measure(root))


def build_receipt_text(root: Path) -> str:
    measurements = measure(root)
    prior_m = json.loads((root / MANIFEST_REL).read_text(encoding="utf-8"))
    manifest_text = assemble_manifest(prior_m, measurements)
    prior_r = json.loads((root / RECEIPT_REL).read_text(encoding="utf-8"))
    return assemble_receipt(prior_r, manifest_text, measurements)


def regenerate(root: Path) -> Dict[str, str]:
    """Return {relative_path: text} for both attestations, manifest first (the
    receipt's manifest_sha256 binds the exact manifest bytes)."""
    measurements = measure(root)
    prior_m = json.loads((root / MANIFEST_REL).read_text(encoding="utf-8"))
    manifest_text = assemble_manifest(prior_m, measurements)
    prior_r = json.loads((root / RECEIPT_REL).read_text(encoding="utf-8"))
    receipt_text = assemble_receipt(prior_r, manifest_text, measurements)
    return {MANIFEST_REL: manifest_text, RECEIPT_REL: receipt_text}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Recession Monitor V2 root",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="reproduce and compare to the on-disk files without writing; "
        "exit 1 on any drift",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = regenerate(root)

    if args.check:
        drift = False
        for relative, text in outputs.items():
            current = (root / relative).read_text(encoding="utf-8")
            status = "OK" if current == text else "DRIFT"
            if current != text:
                drift = True
            print(f"{status} {relative}")
        return 1 if drift else 0

    for relative, text in outputs.items():
        path = root / relative
        path.write_text(text, encoding="utf-8")
        print(f"WROTE {relative} sha256={sha256_bytes(text.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
