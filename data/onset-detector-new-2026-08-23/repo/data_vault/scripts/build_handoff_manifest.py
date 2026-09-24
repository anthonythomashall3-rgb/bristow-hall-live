#!/usr/bin/env python3
"""Build the deterministic Claude Code research-handoff manifest.

The payload corpus is already governed by DATA_SHA256SUMS and the local
inventory receipt. This manifest binds the smaller documentation, catalog,
script, and evidence-control generation that tells another agent how to use
that corpus.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List


SCHEMA = "recession-monitor-v2.claude-research-handoff.v1"
OUTPUT = "data_vault/manifests/claude_handoff_manifest.json"
TOP_LEVEL_MEMBERS = (
    "README.md",
    "CLAUDE.md",
    "CLAUDE_CODE_HANDOFF.md",
    "CLAUDE_CODE_PROGRESS.md",
    "ORIGINAL_METHOD_AND_DATA_INVENTORY.md",
    "DATA_SHA256SUMS",
    "data-manifest.json",
    "source-receipt.json",
    "data_archive/README.md",
    "skills/build-recession-monitor-v2/SKILL.md",
    "skills/build-recession-monitor-v2/agents/openai.yaml",
    "skills/build-recession-monitor-v2/references/stage-contracts.md",
    "skills/build-recession-monitor-v2/references/performance-and-order-contracts.md",
    "live_data/README.md",
    "live_data/config/sources.v1.json",
    "live_data/config/planned_sources.v1.json",
    ".superloopy/evidence/research/2026-07-29-rmv2-live-data/FRAME.md",
    ".superloopy/evidence/research/2026-07-29-rmv2-live-data/SYNTHESIS.md",
    ".superloopy/evidence/research/2026-07-29-rmv2-live-data/claim-ledger.md",
)


def is_tree_noise(path: Path) -> bool:
    """macOS/Python tree cruft that is never a handoff member: .DS_Store,
    __pycache__ dirs, and *.pyc. Basename/parts match only (B-SAFE-1 §3.3)."""
    return (
        path.name == ".DS_Store"
        or "__pycache__" in path.parts
        or path.suffix == ".pyc"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def handoff_paths(root: Path) -> List[str]:
    paths = list(TOP_LEVEL_MEMBERS)
    vault = root / "data_vault"
    for path in vault.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == OUTPUT:
            continue
        if is_tree_noise(path):
            continue
        paths.append(relative)
    return sorted(set(paths))


def read_csv(root: Path, relative: str) -> List[Dict[str, str]]:
    with (root / relative).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build(root: Path) -> Dict[str, object]:
    receipt = json.loads(
        (root / "data_vault/manifests/local_inventory_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    members = [
        {
            "path": relative,
            "bytes": (root / relative).stat().st_size,
            "sha256": sha256_file(root / relative),
        }
        for relative in handoff_paths(root)
    ]
    metrics = read_csv(root, "data_vault/catalog/metric_catalog.csv")
    datasets = read_csv(root, "data_vault/catalog/dataset_catalog.csv")
    external = read_csv(root, "data_vault/catalog/external_source_registry.csv")
    episode_2022 = read_csv(
        root, "data_vault/catalog/episode_2022_release_evidence.csv"
    )
    severity = read_csv(root, "data_vault/catalog/severity_reference_ledger.csv")
    claims = read_csv(root, "data_vault/catalog/research_claim_ledger.csv")
    chronology_methods = read_csv(
        root, "data_vault/catalog/chronology_method_registry.csv"
    )
    severity_dimensions = read_csv(
        root, "data_vault/catalog/severity_dimension_registry.csv"
    )
    access_counts = Counter(row["access_class"] for row in external)
    rights_counts = Counter(row["rights_status"] for row in external)
    metric_confidence_counts = Counter(row["metadata_confidence"] for row in metrics)
    metric_frequency_counts = Counter(row["observation_frequency"] for row in metrics)
    metric_coverage_counts = Counter(
        row["local_1950_coverage_status"] for row in metrics
    )
    metric_clock_counts = Counter(row["release_clock_status"] for row in metrics)
    metric_first_release_counts = Counter(
        row["strict_first_release_local_status"] for row in metrics
    )
    metric_rights_counts = Counter(row["rights_status"] for row in metrics)

    return {
        "schema_version": SCHEMA,
        "generation_date": receipt["inventory_cutoff"],
        "product": "Recession Monitor V2",
        "predecessor_program": "Codex BHI2 Complex",
        "entrypoint": "CLAUDE_CODE_HANDOFF.md",
        "scientific_state": (
            "RESEARCH_AND_DATA_PREPARATION_ONLY;"
            "NO_NEW_STRESS_UNIT_CHRONOLOGY_MONITOR_OR_DAMAGE_FORMULA_ACCEPTED"
        ),
        "payload_receipt": {
            "path": "data_vault/manifests/local_inventory_receipt.json",
            "schema_version": receipt["schema_version"],
            "files": receipt["discovered_files"],
            "bytes": receipt["discovered_bytes"],
            "manifest_matches": receipt["manifest_matches"],
            "manifest_mismatches": receipt["manifest_mismatches"],
            "series_ids": receipt["series_id_count"],
        },
        "catalog_counts": {
            "metric_rows": len(metrics),
            "dataset_rows": len(datasets),
            "external_source_rows": len(external),
            "episode_2022_evidence_rows": len(episode_2022),
            "severity_reference_rows": len(severity),
            "research_claim_rows": len(claims),
            "chronology_method_rows": len(chronology_methods),
            "severity_dimension_rows": len(severity_dimensions),
            "external_access_classes": dict(sorted(access_counts.items())),
            "external_rights_statuses": dict(sorted(rights_counts.items())),
            "metric_metadata_confidence": dict(
                sorted(metric_confidence_counts.items())
            ),
            "metric_observation_frequency": dict(
                sorted(metric_frequency_counts.items())
            ),
            "metric_1950_coverage": dict(sorted(metric_coverage_counts.items())),
            "metric_release_clock_status": dict(
                sorted(metric_clock_counts.items())
            ),
            "metric_strict_first_release_status": dict(
                sorted(metric_first_release_counts.items())
            ),
            "metric_rights_status": dict(sorted(metric_rights_counts.items())),
        },
        "members": members,
        "member_count": len(members),
        "member_set_sha256": hashlib.sha256(canonical_bytes(members)).hexdigest(),
        "required_disclosures": [
            "Codex research is advisory and must be independently verified.",
            "Desired historical outcomes are product requirements, not evidence.",
            "Outcome-guided equation or threshold selection is calibration.",
            "Provider snapshots are not automatically publisher first releases.",
            "Rights and later-start coverage blockers must remain explicit.",
        ],
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output = root / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build(root)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"WROTE {OUTPUT} members={payload['member_count']} "
        f"member_set_sha256={payload['member_set_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
