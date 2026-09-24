"""Claude/Codex-readable acquisition coverage matrix."""

from __future__ import absolute_import

import csv
import io
from pathlib import Path

from .canonical import (
    CanonicalDataError,
    atomic_write,
    atomic_write_group,
    canonical_json_bytes,
    pretty_json_bytes,
    read_json,
    sha256_bytes,
)


MATRIX_FIELDS = (
    "source_id",
    "record_kind",
    "acquisition_status",
    "publisher",
    "endpoint",
    "auth_env",
    "cadence",
    "release_timezone",
    "release_clock",
    "observation_period",
    "available_at",
    "retrieved_at",
    "vintage_id",
    "information_set_mode",
    "revision_policy",
    "rights",
    "parser_version",
    "raw_sha256",
    "normalized_sha256",
    "role",
    "coverage_source_family_ids",
    "known_breaks",
    "unchecked_scope",
)

MATRIX_DEFINITION_FIELDS = (
    "source_id",
    "record_kind",
    "publisher",
    "endpoint",
    "auth_env",
    "cadence",
    "release_timezone",
    "release_clock",
    "information_set_mode",
    "revision_policy",
    "rights",
    "parser_version",
    "role",
    "coverage_source_family_ids",
    "known_breaks",
    "unchecked_scope",
)


def _text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def source_matrix_definition_sha256(rows):
    """Hash only the stable source-universe contract, never poll state."""
    definition_rows = [
        {
            field: row.get(field)
            for field in MATRIX_DEFINITION_FIELDS
        }
        for row in rows
    ]
    definition_rows.sort(
        key=lambda row: (row["record_kind"] or "", row["source_id"] or "")
    )
    return sha256_bytes(canonical_json_bytes({
        "field_order": list(MATRIX_DEFINITION_FIELDS),
        "rows": definition_rows,
        "schema_version": (
            "recession-monitor-v2.source-acquisition-matrix-definition.v1"
        ),
    }))


def _release_timezone(release_clock):
    value = release_clock or ""
    if "America/New_York" in value or " ET" in value:
        return "America/New_York"
    if "America/Chicago" in value or " CT" in value:
        return "America/Chicago"
    if "UTC" in value:
        return "UTC"
    return "unresolved"


def _load_planned(project_root):
    path = (
        Path(project_root) /
        "live_data" /
        "config" /
        "planned_sources.v1.json"
    )
    if not path.exists():
        return []
    value = read_json(path)
    if set(value) != {"schema_version", "scope", "sources"}:
        raise CanonicalDataError("planned-source reservation key set is invalid")
    if (
        value["schema_version"] !=
        "recession-monitor-v2.planned-source-reservations.v1"
    ):
        raise CanonicalDataError("planned-source reservation schema is invalid")
    if not isinstance(value["sources"], list):
        raise CanonicalDataError("planned-source reservations must be a list")
    seen = set()
    for index, source in enumerate(value["sources"]):
        if not isinstance(source, dict):
            raise CanonicalDataError(
                "planned-source reservation row %d is not an object" % index
            )
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise CanonicalDataError(
                "planned-source reservation row %d has no source_id" % index
            )
        if source_id in seen:
            raise CanonicalDataError(
                "duplicate planned-source reservation: %s" % source_id
            )
        seen.add(source_id)
    return value["sources"]


def build_source_matrix(project_root, config, store, coverage, generated_at):
    """Build all registered, active, and reserved sources without promotion."""
    project_root = Path(project_root).resolve()
    coverage_by_id = {
        row["source_id"]: row
        for row in coverage["rows"]
    }
    statuses = store.all_source_statuses()
    heads = store.all_source_heads()
    rows = []

    registry_path = (project_root / config["catalog_registry"]).resolve()
    with registry_path.open("r", encoding="utf-8", newline="") as handle:
        for source in csv.DictReader(handle):
            coverage_row = coverage_by_id[source["source_id"]]
            rows.append({
                "acquisition_status": coverage_row["live_state"],
                "auth_env": None,
                "available_at": None,
                "cadence": source["frequency"],
                "coverage_source_family_ids": [source["source_id"]],
                "endpoint": source["primary_url"],
                "information_set_mode": None,
                "known_breaks": source.get("notes") or "unresolved",
                "normalized_sha256": None,
                "observation_period": source["coverage"],
                "parser_version": None,
                "publisher": source["publisher"],
                "raw_sha256": None,
                "record_kind": "registered_source_family",
                "release_clock": source["typical_release_or_availability"],
                "release_timezone": _release_timezone(
                    source["typical_release_or_availability"]
                ),
                "retrieved_at": None,
                "revision_policy": (
                    source.get("revision_and_vintage_behavior") or "unresolved"
                ),
                "rights": source["rights_status"],
                "role": source.get("role") or "unresolved",
                "source_id": source["source_id"],
                "unchecked_scope": (
                    "collector, exact release-event ledger, and publisher-first-"
                    "release proof remain unverified unless a separate active "
                    "collector row proves them"
                ),
                "vintage_id": None,
            })

    for source in config["sources"]:
        source_id = source["source_id"]
        if source.get("archival"):
            # Archival (frozen-admission) rows are config-known runtime heads that
            # are never fetched. They are not live acquisition and MUST NOT be
            # emitted as active_collector rows; the matrix's active collectors
            # stay exactly the enabled set (record-kind contract is fixed, D0
            # §1.2 / test_rmv2_source_matrix ALLOWED_RECORD_KINDS).
            continue
        head = heads.get(source_id)
        status = statuses.get(source_id)
        rows.append({
            "acquisition_status": (
                (status or {}).get("outcome") or
                ("configured_enabled" if source["enabled"] else "disabled")
            ),
            "auth_env": source["secret_env"],
            "available_at": head.get("retrieved_at") if head else None,
            "cadence": source["frequency"],
            "coverage_source_family_ids": source["coverage_source_ids"],
            "endpoint": source["endpoint"],
            "information_set_mode": source["information_set_mode"],
            "known_breaks": (
                "current collector is not proof of a complete publisher "
                "first-release history"
            ),
            "normalized_sha256": (
                head.get("normalized_sha256") if head else None
            ),
            "observation_period": (
                head.get("latest_observation_period") if head else None
            ),
            "parser_version": source["method_version"],
            "publisher": source["publisher"],
            "raw_sha256": (
                head.get("source_bytes_sha256") if head else None
            ),
            "record_kind": "active_collector",
            "release_clock": source["publisher_release_clock"],
            "release_timezone": _release_timezone(
                source["publisher_release_clock"]
            ),
            "retrieved_at": head.get("retrieved_at") if head else None,
            "revision_policy": (
                "immutable retrieved-vintage bytes and chained receipts; "
                "publisher revision semantics remain source-specific"
            ),
            "rights": source["rights_status"],
            "role": (
                "raw_capture_only"
                if source["adapter"] == "raw_capture"
                else "measurement_acquisition_not_scientific_admission"
            ),
            "source_id": source_id,
            "unchecked_scope": (
                "scientific eligibility, strict first-release history, and "
                "release-clock proof remain outside acquisition"
            ),
            "vintage_id": (
                head.get("source_bytes_sha256") if head else None
            ),
        })

    planned_required = {
        "auth_env",
        "cadence",
        "clock_notes",
        "coverage_source_family_ids",
        "enabled",
        "endpoint",
        "endpoint_status",
        "observation_period",
        "parser_version",
        "publisher",
        "registry_status",
        "release_clock",
        "release_timezone",
        "revision_policy",
        "rights",
        "role",
        "source_id",
        "split_or_bias_guard",
    }
    for source in _load_planned(project_root):
        if set(source) != planned_required:
            raise CanonicalDataError(
                "planned-source row key set is invalid for %r" %
                source.get("source_id")
            )
        rows.append({
            "acquisition_status": source["registry_status"],
            "auth_env": source["auth_env"],
            "available_at": None,
            "cadence": source["cadence"],
            "coverage_source_family_ids": source[
                "coverage_source_family_ids"
            ],
            "endpoint": source["endpoint"],
            "information_set_mode": None,
            "known_breaks": source["split_or_bias_guard"],
            "normalized_sha256": None,
            "observation_period": source["observation_period"],
            "parser_version": source["parser_version"],
            "publisher": source["publisher"],
            "raw_sha256": None,
            "record_kind": "reserved_collector",
            "release_clock": source["release_clock"],
            "release_timezone": source["release_timezone"],
            "retrieved_at": None,
            "revision_policy": source["revision_policy"],
            "rights": source["rights"],
            "role": source["role"],
            "source_id": source["source_id"],
            "unchecked_scope": (
                "%s; %s" %
                (source["endpoint_status"], source["clock_notes"])
            ),
            "vintage_id": None,
        })

    rows.sort(key=lambda row: (row["record_kind"], row["source_id"]))
    counts = {}
    for row in rows:
        counts[row["record_kind"]] = counts.get(row["record_kind"], 0) + 1
    preimage = {
        "caveats": [
            "Acquisition is not scientific admission or model use.",
            "No absent historical vintage is relabeled or synthesized as actual.",
            "Exact publisher first-release coverage is currently unproven.",
            "Licensed and target-bearing sources remain blocked or quarantined.",
        ],
        "counts": counts,
        "definition_sha256": source_matrix_definition_sha256(rows),
        "field_order": list(MATRIX_FIELDS),
        "generated_at": generated_at,
        "rows": rows,
        "schema_version": "recession-monitor-v2.source-acquisition-matrix.v1",
    }
    preimage["matrix_content_sha256"] = sha256_bytes(
        canonical_json_bytes(preimage)
    )
    return preimage


def write_source_matrix(project_root, matrix):
    """Write JSON and CSV views atomically for human and agent readers."""
    output_root = Path(project_root) / "live_data" / "catalog"
    output_root.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=MATRIX_FIELDS,
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in matrix["rows"]:
        writer.writerow({field: _text(row[field]) for field in MATRIX_FIELDS})
    csv_bytes = buffer.getvalue().encode("utf-8")
    json_value = dict(matrix)
    json_value["csv_bytes"] = len(csv_bytes)
    json_value["csv_sha256"] = sha256_bytes(csv_bytes)
    json_bytes = pretty_json_bytes(json_value)
    # The JSON records the CSV's byte count + sha256, so the two files must be
    # published as a crash-consistent group: a writer killed between them must
    # not leave a JSON that disagrees with the CSV on disk (the 2026-08-01
    # incident). atomic_write_group stages both temps then commits back-to-back.
    atomic_write_group([
        (output_root / "source_matrix.v1.csv", csv_bytes),
        (output_root / "source_matrix.v1.json", json_bytes),
    ])
    return {
        "csv_bytes": len(csv_bytes),
        "csv_sha256": sha256_bytes(csv_bytes),
        "definition_sha256": matrix["definition_sha256"],
        "json_bytes": len(json_bytes),
        "json_path": str(output_root / "source_matrix.v1.json"),
        "json_sha256": sha256_bytes(json_bytes),
        "row_count": len(matrix["rows"]),
    }
