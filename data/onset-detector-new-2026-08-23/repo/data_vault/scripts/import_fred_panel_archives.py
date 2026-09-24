#!/usr/bin/env python3
"""Safely materialize authenticated official FRED-MD/FRED-QD archives."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import stat
import tempfile
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Mapping, Tuple


SCHEMA = "recession-monitor-v2.fred-panel-archive-import.v1"
CATALOG_PATH = "data_vault/catalog/fred_panel_archive_import.v1.json"
ARCHIVE_ROOT = "data_archive/additional_vintages"
MISSING_TOKENS = frozenset(("", ".", "NA", "NaN", "nan"))

ARCHIVES = (
    {
        "id": "fred_md_1999_2014",
        "sha256": "3434963f26fbf1aa2e6ff06fd43e1f7b2318ab1a529fa38ac28762f84736a9bb",
        "bytes": 46664359,
        "file_count": 187,
        "csv_count": 185,
        "pdf_count": 2,
        "uncompressed_bytes": 224084650,
        "first_vintage": "1999-08",
        "last_vintage": "2014-12",
        "vintage_count": 185,
        "family": "fred_md",
        "source_url": "https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/fred-md/historical_fred-md.zip?hash=8A23C5FAF7A0D743A353D77DF4704028&sc_lang=en",
    },
    {
        "id": "fred_md_2015_2024",
        "sha256": "f87e939a1f83984a2cc0f12da28b83819d34da59a6e5912d3965a79f75e760c9",
        "bytes": 32790285,
        "file_count": 120,
        "csv_count": 120,
        "pdf_count": 0,
        "uncompressed_bytes": 72967165,
        "first_vintage": "2015-01",
        "last_vintage": "2024-12",
        "vintage_count": 120,
        "family": "fred_md",
        "source_url": "https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/fred-md/historical-vintages-of-fred-md-2015-01-to-2024-12.zip?hash=831F98A7EC8D3809881DF067965B50FF&sc_lang=en",
    },
    {
        "id": "fred_qd_2018_2024",
        "sha256": "1e9e0b20edf64f9ef945f70ffad01ee4ee0806418a2470ec1eb7647d6eb2aa69",
        "bytes": 16922158,
        "file_count": 80,
        "csv_count": 80,
        "pdf_count": 0,
        "uncompressed_bytes": 38378332,
        "first_vintage": "2018-05",
        "last_vintage": "2024-12",
        "vintage_count": 80,
        "family": "fred_qd",
        "source_url": "https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/fred-md/historical-vintages-of-fred-qd-2018-05-to-2024-12.zip?hash=4088DF99A1CCB4F6ED49F5B88A7C636D&sc_lang=en",
    },
)

CURRENT_PANEL = {
    "id": "fred_md_2026_06",
    "sha256": "0003e85e0bbf56537223e0beed9bf579e3b13a9f260e366d2d33c6fa7d8662cf",
    "bytes": 666999,
    "vintage_id": "2026-06",
    "destination": (
        "data_archive/additional_vintages/"
        "fred_md_official/current/fred_md_2026-06.csv"
    ),
    "source_checkout": (
        "/Users/anthonyhall/.config/aegis/worktrees/"
        "RecessionMonitor/monitor-v2"
    ),
    "source_path": (
        "forecaster/artifacts/p4-panel-catalog-v1/"
        "fred_md_2026-06.csv"
    ),
    "source_commit_sample": "655deefda19e4fde7a7662ef8fe054f017b11071",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise ValueError("destination is not one regular file: %s" % path)
        if sha256_file(path) != sha256_bytes(payload):
            raise ValueError("existing destination has different bytes: %s" % path)
        return
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def month_span(first: str, last: str) -> List[str]:
    first_index = int(first[:4]) * 12 + int(first[5:7]) - 1
    last_index = int(last[:4]) * 12 + int(last[5:7]) - 1
    result = []
    for index in range(first_index, last_index + 1):
        year, month0 = divmod(index, 12)
        result.append("%04d-%02d" % (year, month0 + 1))
    return result


def vintage_id(name: str, family: str) -> str:
    filename = PurePosixPath(name).name
    if family == "fred_md":
        match = re.fullmatch(
            r"(?:FRED-MD_)?(\d{4})(?:-|m)(\d{2})\.csv",
            filename,
            flags=re.IGNORECASE,
        )
    else:
        match = re.fullmatch(
            r"FRED-QD_(\d{4})m(\d{1,2})\.csv",
            filename,
            flags=re.IGNORECASE,
        )
    if match is None:
        return ""
    return "%s-%02d" % (match.group(1), int(match.group(2)))


def panel_stats(payload: bytes) -> Mapping[str, object]:
    try:
        text = payload.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("panel was not UTF-8: %s" % exc)
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
        second_row = next(reader)
    except StopIteration:
        raise ValueError("panel was missing header rows")
    if not header or header[0].strip().lower() != "sasdate":
        raise ValueError("panel date column changed")
    factor_row = None
    if second_row and second_row[0].strip().lower() == "factors":
        factor_row = second_row
        try:
            transforms = next(reader)
        except StopIteration:
            raise ValueError("quarterly panel was missing transform row")
        if len(factor_row) != len(header):
            raise ValueError("panel factor row width changed")
        if any(item.strip() not in frozenset(("0", "1"))
               for item in factor_row[1:]):
            raise ValueError("panel factor flag was outside the documented domain")
    else:
        transforms = second_row
    if (
        not transforms or
        transforms[0].strip().lower() not in ("transform", "transform:")
    ):
        raise ValueError("panel transform row changed")
    if len(transforms) != len(header):
        raise ValueError("panel transform row width changed")
    schema_features = [item.strip() for item in header[1:]]
    if not schema_features or any(not item for item in schema_features):
        raise ValueError("panel feature identity was empty")
    if len(schema_features) != len(set(schema_features)):
        raise ValueError("panel feature identities were duplicated")
    transform_codes = [item.strip() for item in transforms[1:]]
    if any(code not in frozenset(("1", "2", "3", "4", "5", "6", "7"))
           for code in transform_codes):
        raise ValueError("panel transform code was outside the documented domain")
    dated_rows = 0
    nonmissing = 0
    previous_date = None
    seen_dates = set()
    data_header = header
    data_features = schema_features
    header_replacement_seen = False
    for row in reader:
        if not row or not row[0].strip():
            continue
        if row[0].strip().lower() == "sasdate":
            if dated_rows or header_replacement_seen:
                raise ValueError("panel contained a late or duplicate header")
            if len(row) != len(header):
                raise ValueError("panel replacement header width changed")
            replacement_features = [item.strip() for item in row[1:]]
            if (
                any(not item for item in replacement_features) or
                len(replacement_features) != len(set(replacement_features))
            ):
                raise ValueError("panel replacement feature identities were invalid")
            data_header = row
            data_features = replacement_features
            header_replacement_seen = True
            continue
        if len(row) != len(data_header):
            raise ValueError("panel row width changed")
        try:
            observation_date = dt.datetime.strptime(
                row[0].strip(),
                "%m/%d/%Y",
            ).date()
        except ValueError:
            try:
                observation_date = dt.datetime.strptime(
                    row[0].strip(),
                    "%Y-%m-%d",
                ).date()
            except ValueError:
                raise ValueError("panel observation date was not canonical")
        if observation_date in seen_dates:
            raise ValueError("panel observation date was duplicated")
        if previous_date is not None and observation_date <= previous_date:
            raise ValueError("panel observation dates were not increasing")
        seen_dates.add(observation_date)
        previous_date = observation_date
        dated_rows += 1
        for raw in row[1:len(data_features) + 1]:
            value = raw.strip()
            if value in MISSING_TOKENS:
                continue
            try:
                parsed = float(value)
            except ValueError:
                raise ValueError("panel value was not numeric")
            if not math.isfinite(parsed):
                raise ValueError("panel value was non-finite")
            nonmissing += 1
    return {
        "dated_row_count": dated_rows,
        "feature_count": len(data_features),
        "factor_row_sha256": (
            sha256_bytes(("\x1f".join(factor_row)).encode("utf-8"))
            if factor_row is not None else None
        ),
        "first_observation": (
            min(seen_dates).isoformat() if seen_dates else None
        ),
        "header_replacement_seen": header_replacement_seen,
        "header_sha256": sha256_bytes(
            ("\x1f".join(data_header)).encode("utf-8")
        ),
        "last_observation": (
            max(seen_dates).isoformat() if seen_dates else None
        ),
        "nonmissing_value_count": nonmissing,
        "transform_row_sha256": sha256_bytes(
            ("\x1f".join(transforms)).encode("utf-8")
        ),
        "transform_schema_header_sha256": sha256_bytes(
            ("\x1f".join(header)).encode("utf-8")
        ),
    }


def safe_member_path(name: str) -> PurePosixPath:
    if "\\" in name:
        raise ValueError("archive member used backslash path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("archive member path escaped root")
    normalized = PurePosixPath(*(
        unicodedata.normalize("NFC", part) for part in path.parts
    ))
    if normalized != path:
        raise ValueError("archive member path was not NFC")
    return path


def import_archive(
    root: Path,
    source_path: Path,
    contract: Mapping[str, object],
) -> Tuple[Mapping[str, object], List[Mapping[str, object]]]:
    if source_path.stat().st_size != contract["bytes"]:
        raise ValueError("%s byte count changed" % contract["id"])
    if sha256_file(source_path) != contract["sha256"]:
        raise ValueError("%s SHA-256 changed" % contract["id"])

    archive_destination = (
        root / ARCHIVE_ROOT /
        ("%s_official" % contract["family"]) /
        "archives" /
        ("%s.zip" % contract["id"])
    )
    atomic_write(archive_destination, source_path.read_bytes())

    rows = []
    seen_aliases = set()
    observed_vintages = []
    with zipfile.ZipFile(source_path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) != contract["file_count"]:
            raise ValueError("%s file count changed" % contract["id"])
        if sum(info.file_size for info in infos) != contract["uncompressed_bytes"]:
            raise ValueError("%s uncompressed byte count changed" % contract["id"])
        if sum(info.filename.lower().endswith(".csv") for info in infos) != contract["csv_count"]:
            raise ValueError("%s CSV count changed" % contract["id"])
        if sum(info.filename.lower().endswith(".pdf") for info in infos) != contract["pdf_count"]:
            raise ValueError("%s PDF count changed" % contract["id"])

        for info in infos:
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("archive member was a symlink")
            if info.flag_bits & 0x1:
                raise ValueError("archive member was encrypted")
            member = safe_member_path(info.filename)
            alias = member.as_posix().casefold()
            if alias in seen_aliases:
                raise ValueError("archive member path alias collision")
            seen_aliases.add(alias)
            if member.suffix.lower() not in (".csv", ".pdf"):
                raise ValueError("archive member type was not admitted")
            payload = archive.read(info)
            if len(payload) != info.file_size:
                raise ValueError("archive member size changed")
            output = (
                root / ARCHIVE_ROOT /
                ("%s_official" % contract["family"]) /
                "extracted" /
                str(contract["id"]) /
                Path(*member.parts)
            )
            atomic_write(output, payload)
            row = {
                "archive_id": contract["id"],
                "bytes": len(payload),
                "member_name": member.as_posix(),
                "output_path": output.relative_to(root).as_posix(),
                "sha256": sha256_bytes(payload),
                "vintage_id": "",
            }
            if member.suffix.lower() == ".csv":
                row["vintage_id"] = vintage_id(member.as_posix(), contract["family"])
                if not row["vintage_id"]:
                    raise ValueError("CSV member lacked a vintage identity")
                try:
                    row.update(panel_stats(payload))
                except ValueError as exc:
                    raise ValueError(
                        "%s member %s failed panel validation: %s" % (
                            contract["id"],
                            member.as_posix(),
                            exc,
                        )
                    )
                observed_vintages.append(row["vintage_id"])
            rows.append(row)

    expected_vintages = month_span(
        str(contract["first_vintage"]),
        str(contract["last_vintage"]),
    )
    if sorted(observed_vintages) != expected_vintages:
        raise ValueError("%s vintage month closure changed" % contract["id"])
    if len(observed_vintages) != contract["vintage_count"]:
        raise ValueError("%s vintage count changed" % contract["id"])
    return {
        "archive_id": contract["id"],
        "bytes": contract["bytes"],
        "csv_count": contract["csv_count"],
        "extracted_file_count": contract["file_count"],
        "family": contract["family"],
        "first_vintage": contract["first_vintage"],
        "last_vintage": contract["last_vintage"],
        "pdf_count": contract["pdf_count"],
        "raw_archive_path": archive_destination.relative_to(root).as_posix(),
        "sha256": contract["sha256"],
        "source_url": contract["source_url"],
        "uncompressed_bytes": contract["uncompressed_bytes"],
        "vintage_count": contract["vintage_count"],
    }, rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--md-early", required=True, type=Path)
    parser.add_argument("--md-late", required=True, type=Path)
    parser.add_argument("--qd", required=True, type=Path)
    parser.add_argument("--current-md", required=True, type=Path)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args()
    root = args.root.resolve()
    supplied = (args.md_early, args.md_late, args.qd)
    archive_rows = []
    member_rows = []
    for source_path, contract in zip(supplied, ARCHIVES):
        archive_row, members = import_archive(
            root,
            source_path.resolve(),
            contract,
        )
        archive_rows.append(archive_row)
        member_rows.extend(members)

    current_path = args.current_md.resolve()
    if (
        current_path.stat().st_size != CURRENT_PANEL["bytes"] or
        sha256_file(current_path) != CURRENT_PANEL["sha256"]
    ):
        raise ValueError("current FRED-MD panel identity changed")
    current_payload = current_path.read_bytes()
    current_output = root / str(CURRENT_PANEL["destination"])
    atomic_write(current_output, current_payload)
    current_stats = panel_stats(current_payload)

    payload = {
        "schema_version": SCHEMA,
        "artifact_name": "Recession Monitor V2",
        "captured_on": "2026-07-29",
        "official_catalog_url": (
            "https://www.stlouisfed.org/research/"
            "economists/mccracken/fred-databases"
        ),
        "information_set_mode": "provider_vintage_panel",
        "strict_publisher_first_release_proven": False,
        "scientific_model_admission": False,
        "archive_rows": archive_rows,
        "current_panel": dict(
            CURRENT_PANEL,
            **current_stats,
            output_path=current_output.relative_to(root).as_posix()
        ),
        "members": sorted(
            member_rows,
            key=lambda row: (row["archive_id"], row["member_name"]),
        ),
        "member_count": len(member_rows),
        "member_set_sha256": sha256_bytes(canonical_bytes(sorted(
            member_rows,
            key=lambda row: (row["archive_id"], row["member_name"]),
        ))),
        "totals": {
            "archive_bytes": sum(int(row["bytes"]) for row in archive_rows),
            "archive_count": len(archive_rows),
            "extracted_bytes": sum(int(row["bytes"]) for row in member_rows),
            "extracted_file_count": len(member_rows),
            "gross_dated_rows": sum(
                int(row.get("dated_row_count", 0))
                for row in member_rows
            ) + int(current_stats["dated_row_count"]),
            "gross_nonmissing_vintage_values": sum(
                int(row.get("nonmissing_value_count", 0))
                for row in member_rows
            ) + int(current_stats["nonmissing_value_count"]),
            "vintage_panel_count": sum(
                int(row["vintage_count"]) for row in archive_rows
            ) + 1,
        },
        "required_disclosures": [
            "Gross panel values repeat history across vintages and are not independent observations.",
            "These official provider panels support as-known and revision analysis but are not automatically publisher first releases.",
            "Schema-era aliases and transform-suffixed fields require a versioned canonical map before model use.",
            "Missingness or renamed-series flags may not be used as calendar-time proxies.",
            "The prior fitted strict-real-time model result was near chance and is negative evidence, not an adopted model.",
        ],
    }
    output = root / CATALOG_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(
        output,
        (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8"),
    )
    print(
        "WROTE %s panels=%d values=%d members=%d" % (
            CATALOG_PATH,
            payload["totals"]["vintage_panel_count"],
            payload["totals"]["gross_nonmissing_vintage_values"],
            payload["member_count"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
