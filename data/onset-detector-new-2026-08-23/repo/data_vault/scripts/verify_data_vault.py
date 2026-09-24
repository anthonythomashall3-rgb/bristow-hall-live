#!/usr/bin/env python3
"""Fail-closed verification for the Recession Monitor V2 data vault.

The default verification checks every generated catalog/manfiest identity and
the exact path/hash relation recorded in the local file inventory. ``--full``
also rehashes every retained payload byte against DATA_SHA256SUMS.

This verifier does not download data, promote a provider snapshot to a
publisher first release, or interpret any observation scientifically.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


EXPECTED_SCHEMA = "recession-monitor-v2.local-byte-inventory.v1"
HANDOFF_SCHEMA = "recession-monitor-v2.claude-research-handoff.v1"
PAYLOAD_ROOTS = ("data", "data_archive", "method_source")
ALLOWED_UNLISTED = {"data_archive/README.md"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_tree_noise(path: Path) -> bool:
    """macOS/Python tree cruft that is never a payload byte: .DS_Store,
    __pycache__ dirs, and *.pyc. Basename/parts match only — never a glob that
    could reach a real payload (B-SAFE-1 §3.3). Keeps the gate from being
    fragile to a Finder-dropped .DS_Store."""
    return (
        path.name == ".DS_Store"
        or "__pycache__" in path.parts
        or path.suffix == ".pyc"
    )
INFORMATION_MODES = [
    "current_revised",
    "archive_snapshot_asof",
    "stitched_strict_first_release",
    "substituted_diagnostic",
]
# D0B UNFREEZE THE VAULT VERIFIER: the store-growing pins below are no longer
# hand-typed literals. They read low-water floors and append-only id sets from
# the single growth-floor authority D0 created, and cross-check against the
# regenerated source matrix. Growth is allowed; a shrink, a dropped/renamed id,
# a removed schema field, or a registry/matrix divergence still fails closed.
# The four science ledgers (2022 evidence, severity reference, research claims,
# severity dimensions) and the chronology-method and canonical-clock registries
# stay pinned to exact counts on purpose: they are target/contract artifacts,
# not growable store data (D0B section 1.1).
GROWTH_FLOORS_PATH = "live_data/config/source_registry_growth_floors.v1.json"
SOURCE_MATRIX_PATH = "live_data/catalog/source_matrix.v1.json"
HANDOFF_TOP_LEVEL_MEMBERS = (
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


class VerificationError(RuntimeError):
    """Raised when any vault invariant does not hold."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> object:
    def reject_duplicate(pairs: Sequence[tuple]) -> Dict[str, object]:
        result: Dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise VerificationError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=lambda value: (_ for _ in ()).throw(
                VerificationError(f"non-finite JSON value {value!r} in {path}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot load {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def read_checksum_manifest(path: Path) -> Dict[str, str]:
    records: Dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        parts = raw.split("  ", 1)
        require(len(parts) == 2, f"invalid checksum line {number}")
        digest, relative_path = parts
        require(bool(SHA256_RE.fullmatch(digest)), f"invalid digest at line {number}")
        require(relative_path not in records, f"duplicate checksum path {relative_path}")
        records[relative_path] = digest
    return records


def read_inventory(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames is not None, "inventory has no header")
        rows = list(reader)
    paths = [row["path"] for row in rows]
    require(len(paths) == len(set(paths)), "inventory contains duplicate paths")
    return rows


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames is not None, f"{path} has no header")
        rows = list(reader)
    require(all(None not in row for row in rows), f"{path} has excess CSV fields")
    return rows


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def discover_payloads(root: Path) -> List[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for payload_root in PAYLOAD_ROOTS
        for path in (root / payload_root).rglob("*")
        if path.is_file() and not is_tree_noise(path)
    )


def verify_output_hashes(root: Path, receipt: Mapping[str, object]) -> None:
    outputs = receipt.get("outputs")
    require(isinstance(outputs, dict), "receipt outputs must be an object")
    for relative_path, expected in sorted(outputs.items()):
        require(isinstance(relative_path, str), "output path must be a string")
        require(isinstance(expected, dict), f"invalid output record {relative_path}")
        path = root / relative_path
        require(path.is_file(), f"missing generated output {relative_path}")
        require(
            path.stat().st_size == expected.get("bytes"),
            f"byte-count mismatch for {relative_path}",
        )
        require(
            sha256_file(path) == expected.get("sha256"),
            f"SHA-256 mismatch for {relative_path}",
        )


def verify_inventory_relation(
    root: Path,
    receipt: Mapping[str, object],
    rows: Sequence[Mapping[str, str]],
    expected: Mapping[str, str],
    full: bool,
) -> None:
    discovered = discover_payloads(root)
    inventory_paths = [row["path"] for row in rows]
    require(inventory_paths == discovered, "inventory path set/order differs from disk")
    require(
        int(receipt["discovered_files"]) == len(rows),
        "receipt discovered_files does not match inventory",
    )
    total_bytes = sum(int(row["byte_count"]) for row in rows)
    require(
        int(receipt["discovered_bytes"]) == total_bytes,
        "receipt discovered_bytes does not match inventory",
    )
    require(
        set(discovered) - set(expected) == ALLOWED_UNLISTED,
        "unexpected unlisted payload set",
    )
    require(not (set(expected) - set(discovered)), "manifest payload missing from disk")

    matches = 0
    mismatches = 0
    lane_counts: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"files": 0, "bytes": 0}
    )
    hash_groups: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        relative_path = row["path"]
        digest = row["sha256"]
        require(bool(SHA256_RE.fullmatch(digest)), f"invalid row digest {relative_path}")
        require(
            (root / relative_path).stat().st_size == int(row["byte_count"]),
            f"row byte count differs from disk: {relative_path}",
        )
        if relative_path in expected:
            require(
                row["expected_sha256"] == expected[relative_path],
                f"row expected hash differs from source manifest: {relative_path}",
            )
            if digest == expected[relative_path]:
                matches += 1
                require(row["manifest_match"] == "true", f"false match flag {relative_path}")
            else:
                mismatches += 1
        else:
            require(
                row["manifest_match"] == "unlisted",
                f"unlisted object has wrong match flag: {relative_path}",
            )
        if full:
            require(
                sha256_file(root / relative_path) == digest,
                f"live payload hash differs from inventory: {relative_path}",
            )
        lane = row["lane"]
        lane_counts[lane]["files"] += 1
        lane_counts[lane]["bytes"] += int(row["byte_count"])
        hash_groups[digest].append(relative_path)

    require(matches == receipt["manifest_matches"], "manifest match count differs")
    require(mismatches == receipt["manifest_mismatches"], "mismatch count differs")
    require(dict(sorted(lane_counts.items())) == receipt["lane_counts"], "lane counts differ")

    duplicate_path = root / "data_vault/manifests/duplicate_hash_groups.json"
    duplicate_rows = load_json(duplicate_path)
    require(isinstance(duplicate_rows, list), "duplicate groups must be an array")
    rebuilt = [
        {"sha256": digest, "count": len(paths), "paths": sorted(paths)}
        for digest, paths in sorted(hash_groups.items())
        if len(paths) > 1
    ]
    require(duplicate_rows == rebuilt, "duplicate hash groups do not reconcile")
    require(
        len(rebuilt) == receipt["duplicate_hash_group_count"],
        "duplicate group count differs",
    )


def verify_series_rollup(
    root: Path, receipt: Mapping[str, object], rows: Sequence[Mapping[str, str]]
) -> None:
    path = root / "data_vault/catalog/local_series_inventory.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        series_rows = list(csv.DictReader(handle))
    ids = [row["series_id"] for row in series_rows]
    require(ids == sorted(ids), "series inventory is not sorted")
    require(len(ids) == len(set(ids)), "duplicate series identifier")
    inventory_ids = {row["series_id"] for row in rows if row["series_id"]}
    require(set(ids) == inventory_ids, "series rollup exact set differs")
    require(len(ids) == receipt["series_id_count"], "series count differs")
    counts = Counter(row["series_id"] for row in rows if row["series_id"])
    for row in series_rows:
        require(
            int(row["file_count"]) == counts[row["series_id"]],
            f"series file count differs: {row['series_id']}",
        )


def verify_research_catalogs(root: Path, receipt: Mapping[str, object]) -> None:
    metrics = read_csv(root / "data_vault/catalog/metric_catalog.csv")
    require(len(metrics) == receipt["series_id_count"], "metric catalog count differs")
    metric_ids = [row["series_id"] for row in metrics]
    require(metric_ids == sorted(metric_ids), "metric catalog is not sorted")
    require(len(metric_ids) == len(set(metric_ids)), "duplicate metric catalog ID")
    require(
        {row["schema_version"] for row in metrics}
        == {"recession-monitor-v2.metric-catalog.v1"},
        "metric catalog schema differs",
    )

    floors = load_json(root / GROWTH_FLOORS_PATH)
    require(isinstance(floors, dict), "growth floors must be an object")

    datasets = read_csv(root / "data_vault/catalog/dataset_catalog.csv")
    dataset_ids = [row["dataset_id"] for row in datasets]
    # Converted from an exact tuple to an append-only floor (D0B). Every
    # previously-recorded dataset partition must still exist (7.3); the count may
    # only grow. A new dataset directory is allowed; a dropped or renamed
    # partition, or a decrease below the floor, still fails.
    dataset_floor_ids = set(floors["append_only_dataset_ids"])
    require(
        dataset_floor_ids <= set(dataset_ids),
        "dataset catalog dropped a previously-recorded dataset_id",
    )
    require(
        len(dataset_ids) >= int(floors["count_floors"]["dataset_partition"]),
        "dataset partition count fell below recorded floor",
    )
    require(len(dataset_ids) == len(set(dataset_ids)), "duplicate dataset ID")
    require(
        sum(int(row["file_count"]) for row in datasets)
        == receipt["discovered_files"],
        "dataset catalog file total differs",
    )
    require(
        sum(int(row["byte_count"]) for row in datasets)
        == receipt["discovered_bytes"],
        "dataset catalog byte total differs",
    )

    external = read_csv(root / "data_vault/catalog/external_source_registry.csv")
    expected_fields = [
        "schema_version",
        "source_id",
        "family",
        "publisher",
        "measure",
        "frequency",
        "coverage",
        "typical_release_or_availability",
        "revision_and_vintage_behavior",
        "role",
        "access_class",
        "rights_status",
        "primary_url",
        "notes",
    ]
    with (root / "data_vault/catalog/external_source_registry.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = csv.DictReader(handle).fieldnames
    require(fieldnames is not None, "external source registry has no header")
    # Superset (D0B): a new column (e.g. a coverage-family field a registration
    # batch adds) must not fail; a removed required column still fails.
    require(
        set(expected_fields) <= set(fieldnames),
        "external source registry is missing a required field",
    )
    source_ids = [row["source_id"] for row in external]
    # Count is unfrozen (D0B): never-decrease against the recorded floor, and
    # every previously-recorded source_id must still exist (append-only, 7.3).
    # This is what FAM1 needs to register a coverage family.
    require(
        len(external) >= int(floors["count_floors"]["registered_source_family"]),
        "external source registry count fell below recorded floor",
    )
    require(
        set(floors["append_only_source_ids"]["registered_source_family"])
        <= set(source_ids),
        "external source registry dropped a previously-recorded source_id",
    )
    require(len(source_ids) == len(set(source_ids)), "duplicate external source ID")
    # Cross-check: the registry and the regenerated source matrix cannot silently
    # diverge. The matrix's registered_source_family id set and tally must both
    # reconcile with the registry.
    matrix = load_json(root / SOURCE_MATRIX_PATH)
    require(isinstance(matrix, dict), "source matrix must be an object")
    matrix_rows = matrix.get("rows")
    require(isinstance(matrix_rows, list), "source matrix rows must be an array")
    matrix_family_ids = {
        row["source_id"]
        for row in matrix_rows
        if isinstance(row, dict) and row.get("record_kind") == "registered_source_family"
    }
    require(
        matrix_family_ids == set(source_ids),
        "external registry and source matrix registered-family id sets diverge",
    )
    require(
        int(matrix["counts"]["registered_source_family"]) == len(external),
        "external registry count and source matrix family tally diverge",
    )
    require(
        {row["schema_version"] for row in external}
        == {"recession-monitor-v2.external-source-registry.v1"},
        "external source registry schema differs",
    )
    require(
        set(row["access_class"] for row in external) == {"A", "B", "C", "D"},
        "external source access classes differ",
    )
    require(
        all(row["primary_url"].startswith("https://") for row in external),
        "external source registry contains non-HTTPS URL",
    )

    episode_2022 = read_csv(
        root / "data_vault/catalog/episode_2022_release_evidence.csv"
    )
    episode_fields = [
        "schema_version",
        "evidence_id",
        "release_at",
        "observation_period",
        "measurement",
        "value",
        "unit",
        "release_stage",
        "evidence_status",
        "source_url",
        "relevance",
        "limitation",
    ]
    with (root / "data_vault/catalog/episode_2022_release_evidence.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = csv.DictReader(handle).fieldnames
    require(fieldnames == episode_fields, "2022 evidence fields differ")
    evidence_ids = [row["evidence_id"] for row in episode_2022]
    require(len(episode_2022) == 13, "2022 evidence count differs")
    require(len(evidence_ids) == len(set(evidence_ids)), "duplicate 2022 evidence ID")
    require(
        {row["schema_version"] for row in episode_2022}
        == {"recession-monitor-v2.episode-2022-release-evidence.v1"},
        "2022 evidence schema differs",
    )
    require(
        all(row["source_url"].startswith("https://") for row in episode_2022),
        "2022 evidence contains non-HTTPS source URL",
    )

    severity = read_csv(root / "data_vault/catalog/severity_reference_ledger.csv")
    severity_fields = [
        "schema_version",
        "evidence_id",
        "episode_start",
        "episode_end",
        "external_classification",
        "classification_dimensions",
        "publication_date",
        "source_url",
        "model_use",
        "limitations",
    ]
    with (root / "data_vault/catalog/severity_reference_ledger.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = csv.DictReader(handle).fieldnames
    require(fieldnames == severity_fields, "severity reference fields differ")
    severity_ids = [row["evidence_id"] for row in severity]
    require(len(severity) == 9, "severity reference count differs")
    require(len(severity_ids) == len(set(severity_ids)), "duplicate severity ID")
    require(
        {row["schema_version"] for row in severity}
        == {"recession-monitor-v2.severity-reference-ledger.v1"},
        "severity reference schema differs",
    )
    require(
        {row["external_classification"] for row in severity}
        == {"mild", "moderate", "severe"},
        "severity reference classes differ",
    )
    require(
        {row["model_use"] for row in severity} == {"external_validation_only"},
        "severity reference model-use boundary differs",
    )

    claims = read_csv(root / "data_vault/catalog/research_claim_ledger.csv")
    claim_fields = [
        "schema_version",
        "claim_id",
        "claim",
        "risk",
        "evidence_state",
        "primary_sources",
        "counter_search",
        "model_implication",
    ]
    with (root / "data_vault/catalog/research_claim_ledger.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = csv.DictReader(handle).fieldnames
    require(fieldnames == claim_fields, "research claim fields differ")
    claim_ids = [row["claim_id"] for row in claims]
    require(len(claims) == 7, "research claim count differs")
    require(len(claim_ids) == len(set(claim_ids)), "duplicate research claim ID")
    require(
        {row["schema_version"] for row in claims}
        == {"recession-monitor-v2.research-claim-ledger.v1"},
        "research claim schema differs",
    )
    require(
        set(row["evidence_state"] for row in claims)
        <= {"verified_exact_bytes", "verified_primary_source", "corroborated"},
        "research claim evidence state differs",
    )

    chronology_methods = read_csv(
        root / "data_vault/catalog/chronology_method_registry.csv"
    )
    chronology_fields = [
        "schema_version",
        "method_family_id",
        "cycle_concept",
        "geometry",
        "output",
        "target_independent_in_principle",
        "fitted_or_calibrated_degrees_of_freedom",
        "failure_mode",
        "primary_sources",
    ]
    with (root / "data_vault/catalog/chronology_method_registry.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = csv.DictReader(handle).fieldnames
    require(fieldnames == chronology_fields, "chronology method fields differ")
    chronology_ids = [row["method_family_id"] for row in chronology_methods]
    require(len(chronology_methods) == 9, "chronology method count differs")
    require(
        len(chronology_ids) == len(set(chronology_ids)),
        "duplicate chronology method ID",
    )
    require(
        {row["schema_version"] for row in chronology_methods}
        == {"recession-monitor-v2.chronology-method-registry.v1"},
        "chronology method schema differs",
    )
    require(
        {row["target_independent_in_principle"] for row in chronology_methods}
        == {"true"},
        "chronology method target-independence field differs",
    )
    require(
        all(row["fitted_or_calibrated_degrees_of_freedom"] for row in chronology_methods),
        "chronology method omits governed degrees of freedom",
    )

    severity_dimensions = read_csv(
        root / "data_vault/catalog/severity_dimension_registry.csv"
    )
    severity_dimension_fields = [
        "schema_version",
        "dimension_id",
        "dimension_name",
        "primitive_description",
        "scope",
        "governed_degrees_of_freedom",
        "primary_sources",
        "interpretation_boundary",
    ]
    with (root / "data_vault/catalog/severity_dimension_registry.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = csv.DictReader(handle).fieldnames
    require(
        fieldnames == severity_dimension_fields,
        "severity dimension fields differ",
    )
    severity_dimension_ids = [row["dimension_id"] for row in severity_dimensions]
    require(len(severity_dimensions) == 13, "severity dimension count differs")
    require(
        len(severity_dimension_ids) == len(set(severity_dimension_ids)),
        "duplicate severity dimension ID",
    )
    require(
        {row["schema_version"] for row in severity_dimensions}
        == {"recession-monitor-v2.severity-dimension-registry.v1"},
        "severity dimension schema differs",
    )
    require(
        all(row["governed_degrees_of_freedom"] for row in severity_dimensions),
        "severity dimension omits governed degrees of freedom",
    )

    timing = load_json(root / "data_vault/catalog/timing_model.json")
    require(isinstance(timing, dict), "timing model must be an object")
    require(
        timing.get("information_set_modes") == INFORMATION_MODES,
        "information-set modes differ",
    )
    clocks = timing.get("canonical_clocks")
    require(isinstance(clocks, list) and len(clocks) == 7, "canonical clocks differ")
    clock_names = [row.get("clock") for row in clocks if isinstance(row, dict)]
    require(len(clock_names) == len(set(clock_names)), "duplicate canonical clock")


def handoff_paths(root: Path) -> List[str]:
    paths = list(HANDOFF_TOP_LEVEL_MEMBERS)
    for path in (root / "data_vault").rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "data_vault/manifests/claude_handoff_manifest.json":
            continue
        if is_tree_noise(path):
            continue
        paths.append(relative)
    return sorted(set(paths))


def verify_handoff_manifest(root: Path) -> None:
    path = root / "data_vault/manifests/claude_handoff_manifest.json"
    manifest = load_json(path)
    require(isinstance(manifest, dict), "handoff manifest must be an object")
    require(manifest.get("schema_version") == HANDOFF_SCHEMA, "handoff schema differs")
    members = manifest.get("members")
    require(isinstance(members, list), "handoff members must be an array")
    expected_paths = handoff_paths(root)
    actual_paths = [
        member.get("path") for member in members if isinstance(member, dict)
    ]
    require(actual_paths == expected_paths, "handoff member exact set/order differs")
    require(len(actual_paths) == len(set(actual_paths)), "duplicate handoff member")
    require(manifest.get("member_count") == len(members), "handoff member count differs")
    for member in members:
        require(isinstance(member, dict), "invalid handoff member")
        member_path = root / str(member["path"])
        require(member_path.is_file(), f"missing handoff member {member['path']}")
        require(
            member_path.stat().st_size == member.get("bytes"),
            f"handoff byte count differs: {member['path']}",
        )
        require(
            sha256_file(member_path) == member.get("sha256"),
            f"handoff hash differs: {member['path']}",
        )
    require(
        hashlib.sha256(canonical_bytes(members)).hexdigest()
        == manifest.get("member_set_sha256"),
        "handoff member-set hash differs",
    )
    metrics = read_csv(root / "data_vault/catalog/metric_catalog.csv")
    datasets = read_csv(root / "data_vault/catalog/dataset_catalog.csv")
    external = read_csv(root / "data_vault/catalog/external_source_registry.csv")
    episode_2022 = read_csv(
        root / "data_vault/catalog/episode_2022_release_evidence.csv"
    )
    severity = read_csv(root / "data_vault/catalog/severity_reference_ledger.csv")
    claims = read_csv(root / "data_vault/catalog/research_claim_ledger.csv")
    chronology_methods = read_csv(
        root / "data_vault/catalog/chronology_method_registry.csv"
    )
    severity_dimensions = read_csv(
        root / "data_vault/catalog/severity_dimension_registry.csv"
    )
    expected_catalog_counts = {
        "metric_rows": len(metrics),
        "dataset_rows": len(datasets),
        "external_source_rows": len(external),
        "episode_2022_evidence_rows": len(episode_2022),
        "severity_reference_rows": len(severity),
        "research_claim_rows": len(claims),
        "chronology_method_rows": len(chronology_methods),
        "severity_dimension_rows": len(severity_dimensions),
        "external_access_classes": dict(
            sorted(Counter(row["access_class"] for row in external).items())
        ),
        "external_rights_statuses": dict(
            sorted(Counter(row["rights_status"] for row in external).items())
        ),
        "metric_metadata_confidence": dict(
            sorted(Counter(row["metadata_confidence"] for row in metrics).items())
        ),
        "metric_observation_frequency": dict(
            sorted(
                Counter(row["observation_frequency"] for row in metrics).items()
            )
        ),
        "metric_1950_coverage": dict(
            sorted(
                Counter(row["local_1950_coverage_status"] for row in metrics).items()
            )
        ),
        "metric_release_clock_status": dict(
            sorted(Counter(row["release_clock_status"] for row in metrics).items())
        ),
        "metric_strict_first_release_status": dict(
            sorted(
                Counter(
                    row["strict_first_release_local_status"] for row in metrics
                ).items()
            )
        ),
        "metric_rights_status": dict(
            sorted(Counter(row["rights_status"] for row in metrics).items())
        ),
    }
    require(
        manifest.get("catalog_counts") == expected_catalog_counts,
        "handoff catalog-count summary differs",
    )


def verify_receipt(root: Path, full: bool) -> Dict[str, object]:
    receipt_path = root / "data_vault/manifests/local_inventory_receipt.json"
    receipt = load_json(receipt_path)
    require(isinstance(receipt, dict), "receipt must be a JSON object")
    require(receipt.get("schema_version") == EXPECTED_SCHEMA, "unexpected receipt schema")
    require(receipt.get("payload_roots") == list(PAYLOAD_ROOTS), "payload roots differ")
    require(receipt.get("manifest_mismatches") == 0, "receipt contains mismatches")
    require(receipt.get("unlisted_on_disk") == [], "receipt contains unlisted objects")
    require(receipt.get("missing_from_disk") == [], "receipt contains missing objects")
    require(
        set(receipt.get("allowed_unlisted_on_disk", [])) == ALLOWED_UNLISTED,
        "allowed-unlisted set differs",
    )

    source = receipt.get("source_manifest")
    require(isinstance(source, dict), "source_manifest must be an object")
    manifest_path = root / str(source["path"])
    require(manifest_path.is_file(), "source checksum manifest missing")
    require(manifest_path.stat().st_size == source["bytes"], "source manifest size differs")
    require(sha256_file(manifest_path) == source["sha256"], "source manifest hash differs")
    expected = read_checksum_manifest(manifest_path)
    require(len(expected) == source["records"], "source manifest record count differs")

    verify_output_hashes(root, receipt)
    inventory_path = root / "data_vault/manifests/local_file_inventory.csv"
    rows = read_inventory(inventory_path)
    verify_inventory_relation(root, receipt, rows, expected, full)
    verify_series_rollup(root, receipt, rows)
    verify_research_catalogs(root, receipt)
    verify_handoff_manifest(root)
    return dict(receipt)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Recession Monitor V2 root",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="rehash all retained payload bytes, not only generated artifacts",
    )
    args = parser.parse_args()
    try:
        receipt = verify_receipt(args.root.resolve(), args.full)
    except VerificationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    mode = "full-byte" if args.full else "catalog"
    print(
        "PASS "
        f"mode={mode} files={receipt['discovered_files']} "
        f"bytes={receipt['discovered_bytes']} "
        f"series={receipt['series_id_count']} "
        f"manifest_matches={receipt['manifest_matches']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
