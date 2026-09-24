#!/usr/bin/env python3
"""Build a deterministic inventory of the retained Recession Monitor V2 corpus.

This script catalogs existing bytes. It does not download data, infer release
dates, or promote provider snapshots to publisher-first-release evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "recession-monitor-v2.local-byte-inventory.v1"
INVENTORY_CUTOFF = "2026-07-29"
PAYLOAD_ROOTS = ("data", "data_archive", "method_source")


def is_tree_noise(path: "Path") -> bool:
    """macOS/Python tree cruft that is never an inventory payload: .DS_Store,
    __pycache__ dirs, and *.pyc. Basename/parts match only (B-SAFE-1 §3.3)."""
    return (
        path.name == ".DS_Store"
        or "__pycache__" in path.parts
        or path.suffix == ".pyc"
    )
ALLOWED_UNLISTED = ("data_archive/README.md",)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COLON_DATE_RE = re.compile(r"^(?P<year>\d{4}):(?P<month>\d{2}):(?P<day>\d{2})$")
QUARTER_RE = re.compile(r"^(?P<year>\d{4})(?::)?Q(?P<quarter>[1-4])$")
YEAR_RE = re.compile(r"^(?P<year>\d{4})(?:\.0+)?$")
VINTAGE_FILE_RE = re.compile(r"^(?P<series>.+)_(?P<vintage>\d{4}-\d{2}-\d{2})$")
ROOT_SERIES_PREFIXES = ("_r_", "comp_", "probe_")
# B-HOUSE-2 (2026-08-06): macOS Finder-duplicate signature. When Finder copies a
# file it appends " 2" (" 3", ...) before the extension, so a real payload
# "DGS2.csv" spawns a junk twin "DGS2 2.csv". Provider/series identifiers never
# contain a space, so a stem ending in " <N>" is always the Finder artifact, not
# a distinct series. Such files still exist on disk (and stay in the frozen
# payload manifest, so they remain inventoried as *file* rows), but they must not
# be minted into phantom series ("DGS2 2", "USRECD 2") that leak through
# local_series_inventory -> metric_catalog -> the gap registry (CH-R25 finding).
FINDER_DUPLICATE_STEM_RE = re.compile(r" \d+$")

INVENTORY_FIELDS = (
    "path",
    "lane",
    "role",
    "series_id",
    "vintage_date",
    "extension",
    "content_kind",
    "byte_count",
    "sha256",
    "expected_sha256",
    "manifest_match",
    "row_count",
    "columns_json",
    "first_time_key",
    "last_time_key",
    "time_key_kind",
    "first_observation_date",
    "last_observation_date",
    "parse_status",
    "notes",
)

SERIES_FIELDS = (
    "series_id",
    "file_count",
    "lanes_json",
    "roles_json",
    "current_file_count",
    "vintage_file_count",
    "first_vintage_date",
    "last_vintage_date",
    "first_observation_date",
    "last_observation_date",
    "total_rows",
    "total_bytes",
    "parse_statuses_json",
    "paths_json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_json_bytes(value))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_expected_manifest(path: Path) -> Dict[str, str]:
    expected: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.rstrip("\n")
            if not line:
                continue
            try:
                digest, relative_path = line.split("  ", 1)
            except ValueError as exc:
                raise ValueError(f"invalid checksum record at line {line_number}") from exc
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"invalid SHA-256 at line {line_number}")
            if relative_path in expected:
                raise ValueError(f"duplicate checksum path: {relative_path}")
            expected[relative_path] = digest
    return expected


def lane_and_role(relative_path: str) -> Tuple[str, str]:
    parts = Path(relative_path).parts
    if parts[0] == "data":
        return "live_capture", "browser_runtime_artifact"
    if parts[0] == "method_source":
        return "method_source", "calculation_or_evidence_source"
    if parts[:2] == ("data_archive", "derived_original"):
        return "derived_original", "derived_artifact"
    if parts[:3] == ("data_archive", "additional_vintages", "ohw3"):
        return "point_in_time_candidate", "dense_provider_snapshot"
    if parts[:3] == ("data_archive", "additional_vintages", "bea_cache"):
        return "publisher_release_candidate", "bea_release_workbook"
    if parts[:3] == ("data_archive", "additional_vintages", "bea_extracted"):
        return "publisher_release_candidate", "bea_release_extraction"
    if parts[:3] == (
        "data_archive",
        "additional_vintages",
        "fred_md_official",
    ):
        return "provider_panel_vintage", "fred_md_official_vintage_panel"
    if parts[:3] == (
        "data_archive",
        "additional_vintages",
        "fred_qd_official",
    ):
        return "provider_panel_vintage", "fred_qd_official_vintage_panel"
    if parts[:3] == (
        "data_archive",
        "current_revised_and_spatial",
        "vintages",
    ):
        return "named_vintage_candidate", "provider_vintage_snapshot"
    if parts[:3] == (
        "data_archive",
        "current_revised_and_spatial",
        "quarantine",
    ):
        return "quarantine", "quarantined_source_candidate"
    if parts[:2] == ("data_archive", "current_revised_and_spatial"):
        if len(parts) == 3:
            return "current_revised", "national_or_reference_series"
        return "current_revised_spatial", f"spatial_dataset:{parts[2]}"
    return "unclassified", "unclassified"


def derive_series_id(relative_path: str, role: str) -> Tuple[str, str]:
    path = Path(relative_path)
    stem = path.stem
    if FINDER_DUPLICATE_STEM_RE.search(stem):
        # Finder-duplicate junk twin: keep the file inventoried but mint no series.
        return "", ""
    if role in ("provider_vintage_snapshot", "dense_provider_snapshot"):
        match = VINTAGE_FILE_RE.match(stem)
        if match:
            return match.group("series"), match.group("vintage")
    if role in ("national_or_reference_series", "quarantined_source_candidate"):
        if path.suffix.lower() != ".csv":
            return "", ""
        series = stem
        for prefix in ROOT_SERIES_PREFIXES:
            if series.startswith(prefix):
                series = series[len(prefix) :]
                break
        if series.endswith("_v"):
            series = series[:-2]
        return series, ""
    if role == "bea_release_extraction":
        return stem.split("_", 1)[0], ""
    return "", ""


def content_kind(path: Path, prefix: bytes) -> str:
    suffix = path.suffix.lower()
    lowered = prefix.lstrip().lower()
    if not prefix:
        return "empty"
    if lowered.startswith((b"<!doctype html", b"<html")):
        return "html"
    if suffix == ".csv":
        return "csv"
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in (".xls", ".xlsx"):
        return "spreadsheet"
    if suffix in (".py", ".js", ".html", ".md", ".txt", ".log", ".sh"):
        return suffix.lstrip(".")
    if suffix in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
        return "image"
    return "binary_or_unknown"


def normalize_time_key(value: str) -> Tuple[str, str]:
    candidate = value.strip()
    if DATE_RE.fullmatch(candidate):
        return candidate, "date"
    if len(candidate) >= 10 and DATE_RE.fullmatch(candidate[:10]):
        return candidate[:10], "timestamp"
    match = COLON_DATE_RE.fullmatch(candidate)
    if match:
        return (
            f"{match.group('year')}-{match.group('month')}-{match.group('day')}",
            "colon_date",
        )
    match = QUARTER_RE.fullmatch(candidate.replace(" ", ""))
    if match:
        quarter = int(match.group("quarter"))
        month = 1 + (quarter - 1) * 3
        return f"{match.group('year')}-{month:02d}-01", "quarter"
    match = YEAR_RE.fullmatch(candidate)
    if match:
        return f"{match.group('year')}-01-01", "year"
    return "", ""


def inspect_csv(path: Path) -> Dict[str, object]:
    row_count = 0
    columns: List[str] = []
    first_date = ""
    last_date = ""
    first_time_key = ""
    last_time_key = ""
    time_key_kinds = set()
    out_of_order = False
    previous_date = ""
    parse_status = "parsed"
    notes: List[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            columns = next(reader)
            for row in reader:
                if not row or not any(cell.strip() for cell in row):
                    continue
                row_count += 1
                candidate = row[0].strip()
                normalized, key_kind = normalize_time_key(candidate)
                if normalized:
                    if not first_time_key:
                        first_time_key = candidate
                    last_time_key = candidate
                    time_key_kinds.add(key_kind)
                    if not first_date:
                        first_date = normalized
                    if previous_date and normalized < previous_date:
                        out_of_order = True
                    previous_date = normalized
                    last_date = normalized
    except (UnicodeDecodeError, csv.Error, StopIteration, OSError) as exc:
        parse_status = f"csv_error:{type(exc).__name__}"
    if out_of_order:
        notes.append("first_column_dates_out_of_order")
    if columns and not first_date:
        notes.append("no_iso_date_in_first_column")
    return {
        "row_count": row_count,
        "columns_json": json.dumps(columns, ensure_ascii=False, separators=(",", ":")),
        "first_time_key": first_time_key,
        "last_time_key": last_time_key,
        "time_key_kind": (
            next(iter(time_key_kinds))
            if len(time_key_kinds) == 1
            else "mixed"
            if time_key_kinds
            else ""
        ),
        "first_observation_date": first_date,
        "last_observation_date": last_date,
        "parse_status": parse_status,
        "notes": ";".join(notes),
    }


def inspect_file(root: Path, relative_path: str, expected_sha: Optional[str]) -> Dict[str, object]:
    path = root / relative_path
    with path.open("rb") as handle:
        prefix = handle.read(4096)
    kind = content_kind(path, prefix)
    lane, role = lane_and_role(relative_path)
    series_id, vintage_date = derive_series_id(relative_path, role)
    digest = sha256_file(path)
    row: Dict[str, object] = {
        "path": relative_path,
        "lane": lane,
        "role": role,
        "series_id": series_id,
        "vintage_date": vintage_date,
        "extension": path.suffix.lower(),
        "content_kind": kind,
        "byte_count": path.stat().st_size,
        "sha256": digest,
        "expected_sha256": expected_sha or "",
        "manifest_match": (
            "true" if expected_sha == digest else "false" if expected_sha else "unlisted"
        ),
        "row_count": "",
        "columns_json": "[]",
        "first_time_key": "",
        "last_time_key": "",
        "time_key_kind": "",
        "first_observation_date": "",
        "last_observation_date": "",
        "parse_status": "not_applicable",
        "notes": "",
    }
    if kind == "csv":
        row.update(inspect_csv(path))
    elif path.suffix.lower() == ".csv" and kind == "html":
        row["parse_status"] = "html_masquerading_as_csv"
        row["notes"] = "quarantine_required"
    elif kind == "empty":
        row["parse_status"] = "empty_file"
    return row


def summarize_series(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        series_id = str(row["series_id"])
        if series_id:
            grouped[series_id].append(row)
    summaries: List[Dict[str, object]] = []
    for series_id in sorted(grouped):
        members = grouped[series_id]
        vintages = sorted(
            str(row["vintage_date"]) for row in members if row["vintage_date"]
        )
        observations = [
            (str(row["first_observation_date"]), str(row["last_observation_date"]))
            for row in members
            if row["first_observation_date"] and row["last_observation_date"]
        ]
        total_rows = sum(
            int(row["row_count"]) for row in members if str(row["row_count"]).isdigit()
        )
        summaries.append(
            {
                "series_id": series_id,
                "file_count": len(members),
                "lanes_json": json.dumps(
                    sorted({str(row["lane"]) for row in members}), separators=(",", ":")
                ),
                "roles_json": json.dumps(
                    sorted({str(row["role"]) for row in members}), separators=(",", ":")
                ),
                "current_file_count": sum(
                    row["lane"] == "current_revised" for row in members
                ),
                "vintage_file_count": len(vintages),
                "first_vintage_date": vintages[0] if vintages else "",
                "last_vintage_date": vintages[-1] if vintages else "",
                "first_observation_date": (
                    min(first for first, _ in observations) if observations else ""
                ),
                "last_observation_date": (
                    max(last for _, last in observations) if observations else ""
                ),
                "total_rows": total_rows,
                "total_bytes": sum(int(row["byte_count"]) for row in members),
                "parse_statuses_json": json.dumps(
                    sorted({str(row["parse_status"]) for row in members}),
                    separators=(",", ":"),
                ),
                "paths_json": json.dumps(
                    sorted(str(row["path"]) for row in members),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            }
        )
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Recession Monitor V2 root",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "data_vault"
    catalog_dir = output / "catalog"
    manifest_dir = output / "manifests"
    expected = load_expected_manifest(root / "DATA_SHA256SUMS")

    discovered = sorted(
        path.relative_to(root).as_posix()
        for payload_root in PAYLOAD_ROOTS
        for path in (root / payload_root).rglob("*")
        if path.is_file() and not is_tree_noise(path)
    )
    rows = [
        inspect_file(root, relative_path, expected.get(relative_path))
        for relative_path in discovered
    ]

    hash_groups: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        hash_groups[str(row["sha256"])].append(str(row["path"]))
    duplicate_groups = [
        {"sha256": digest, "count": len(paths), "paths": sorted(paths)}
        for digest, paths in sorted(hash_groups.items())
        if len(paths) > 1
    ]
    anomalies = [
        row
        for row in rows
        if row["manifest_match"] != "true"
        or row["parse_status"]
        in ("html_masquerading_as_csv", "empty_file")
        or str(row["parse_status"]).startswith("csv_error:")
        or row["notes"]
    ]

    missing_from_disk = sorted(set(expected) - set(discovered))
    all_unlisted_on_disk = sorted(set(discovered) - set(expected))
    allowed_unlisted_on_disk = sorted(set(all_unlisted_on_disk) & set(ALLOWED_UNLISTED))
    unlisted_on_disk = sorted(set(all_unlisted_on_disk) - set(ALLOWED_UNLISTED))
    lane_counts: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"files": 0, "bytes": 0}
    )
    for row in rows:
        lane = str(row["lane"])
        lane_counts[lane]["files"] += 1
        lane_counts[lane]["bytes"] += int(row["byte_count"])

    inventory_path = manifest_dir / "local_file_inventory.csv"
    series_path = catalog_dir / "local_series_inventory.csv"
    duplicate_path = manifest_dir / "duplicate_hash_groups.json"
    anomalies_path = manifest_dir / "local_inventory_anomalies.json"
    receipt_path = manifest_dir / "local_inventory_receipt.json"

    write_csv(inventory_path, INVENTORY_FIELDS, rows)
    write_csv(series_path, SERIES_FIELDS, summarize_series(rows))
    write_json(duplicate_path, duplicate_groups)
    write_json(anomalies_path, anomalies)

    output_records = {}
    for path in (inventory_path, series_path, duplicate_path, anomalies_path):
        output_records[path.relative_to(root).as_posix()] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "inventory_cutoff": INVENTORY_CUTOFF,
        "payload_roots": list(PAYLOAD_ROOTS),
        "source_manifest": {
            "path": "DATA_SHA256SUMS",
            "bytes": (root / "DATA_SHA256SUMS").stat().st_size,
            "sha256": sha256_file(root / "DATA_SHA256SUMS"),
            "records": len(expected),
        },
        "discovered_files": len(discovered),
        "discovered_bytes": sum(int(row["byte_count"]) for row in rows),
        "manifest_matches": sum(row["manifest_match"] == "true" for row in rows),
        "manifest_mismatches": sum(row["manifest_match"] == "false" for row in rows),
        "unlisted_on_disk": unlisted_on_disk,
        "allowed_unlisted_on_disk": allowed_unlisted_on_disk,
        "missing_from_disk": missing_from_disk,
        "lane_counts": dict(sorted(lane_counts.items())),
        "series_id_count": len({row["series_id"] for row in rows if row["series_id"]}),
        "duplicate_hash_group_count": len(duplicate_groups),
        "anomaly_count": len(anomalies),
        "outputs": output_records,
    }
    write_json(receipt_path, receipt)
    print(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True))
    return (
        0
        if not missing_from_disk
        and not unlisted_on_disk
        and not receipt["manifest_mismatches"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
