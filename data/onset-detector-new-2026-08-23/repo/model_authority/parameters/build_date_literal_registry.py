#!/usr/bin/env python3
"""Build the classified date-literal registry for the declared science path."""

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "model_authority/parameters/date_literal_registry.v1.json"
ISO_DATE = re.compile(r"(?<!\d)(?:19|20)\d{2}-\d{2}-\d{2}(?!\d)")
SCIENCE_FILES = (
    "method_source/index_v1.py",
    "method_source/forecaster_site.py",
    "method_source/nowcast_live.py",
    "method_source/alfred_replay.py",
    "method_source/energy_build.py",
    "method_source/watch_build.py",
    "method_source/census_build.py",
    "method_source/forecaster/features.py",
    "method_source/forecaster/models.py",
    "method_source/forecaster/backtest.py",
    "model_authority/temporal/build_realtime_coverage_manifest.py",
)


def _classification(relative, line, value):
    if relative == "method_source/alfred_replay.py" and 220 <= line <= 225:
        return "unsupported_display_claim"
    if (
        relative == "method_source/alfred_replay.py" and line == 138
    ) or (
        relative == "method_source/index_v1.py" and 116 <= line <= 117
    ) or (
        relative == "method_source/nowcast_live.py" and value == "2011-12-31"
    ):
        return "information_set_boundary"
    if (
        relative == "method_source/alfred_replay.py" and line == 172
    ) or (
        relative == "method_source/census_build.py" and line in (51, 159)
    ) or (
        relative == "method_source/energy_build.py" and line == 79
    ) or (
        relative == "method_source/index_v1.py" and line == 28
    ):
        return "coverage_cutover_boundary"
    if (
        relative == "method_source/alfred_replay.py" and 199 <= line <= 201
    ) or (
        relative == "method_source/census_build.py" and line == 179
    ):
        return "evaluation_window_boundary"
    if (
        relative == "method_source/index_v1.py" and 207 <= line <= 210
    ) or (
        relative == "method_source/energy_build.py" and 85 <= line <= 88
    ):
        return "grading_target_boundary"
    if relative == "method_source/census_build.py" and 43 <= line <= 47:
        return "external_calendar_fact"
    if value == "1970-01-01":
        return "calendar_coordinate"
    if value.startswith("2026-"):
        return "protocol_provenance_fact"
    if relative == "method_source/energy_build.py" and line == 14:
        return "derived_record_fact"
    return "UNCLASSIFIED"


# Provenance (B-GUARD-GAP-EXCL / owner ruling EFFN_ONLY). Every date literal that
# CONTROLS MODEL OUTPUT is an inherited scientific boundary — the owner ruling
# retires all inherited constants, so it enters `retired`: value+file:line kept for
# reproducibility, authority removed, NEW citations blocked. Date literals that do
# NOT control model output are documentary facts (calendar coordinates, dated audit
# annotations, a described historical maximum) — not fitted inputs, no derivation
# owed — and carry `documentary`. No value is changed here (§18.1).
PROVENANCE_CONTROLLING = "retired"
PROVENANCE_DOCUMENTARY = "documentary"

# Transitive-retirement tracking (B-GUARD-GAP-EXCL step: "add transitive-retirement
# tracking"). A retired boundary does not retire alone — everything downstream that
# reads it is transitively retired. Keyed by classification; documentary only, it
# NAMES the dependents and derives nothing (§22.4).
TRANSITIVE_DEPENDENTS = {
    "information_set_boundary": [
        "is_baseline() expansion baseline selection",
        "MU/SD/Z (mean, sd, z-score) for every member",
        "every channel score",
        "the headline reading",
    ],
    "coverage_cutover_boundary": [
        "source coverage/cadence selection at the cutover date",
    ],
    "evaluation_window_boundary": [
        "retrospective evaluation-window membership",
    ],
    "grading_target_boundary": [
        "onset-target grading window (instrument_onset_target_ledger)",
    ],
    "external_calendar_fact": [
        "NBER recession-date lookups feeding baseline exclusion and grading",
    ],
    "unsupported_display_claim": [
        "fabricated display claim (already blocker-flagged)",
    ],
}


AUTHORITY = {
    "information_set_boundary": (
        "model_authority/parameters/parameter_registry.v1.json science "
        "declarations; inherited boundary, not silently inferred"
    ),
    "coverage_cutover_boundary": (
        "declared source-coverage/cadence cutover retained from the method source"
    ),
    "evaluation_window_boundary": (
        "declared retrospective evaluation window; not a release-time fact"
    ),
    "grading_target_boundary": (
        "model_authority/target_ledger/instrument_onset_target_ledger.v1.json"
    ),
    "external_calendar_fact": "NBER published recession chronology",
    "calendar_coordinate": "Unix/calendar coordinate only; no fitted information set",
    "protocol_provenance_fact": (
        "dated method decision or audit annotation; documentary, not model input"
    ),
    "derived_record_fact": "derived historical maximum described by the build output",
    "unsupported_display_claim": (
        "blockers/FABRICATION__alfred_replay.py_220-225__837bc4e75696.json"
    ),
}


def _records():
    rows = []
    for relative in SCIENCE_FILES:
        path = ROOT / relative
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        for line_number, text in enumerate(lines, 1):
            for match in ISO_DATE.finditer(text):
                rows.append(
                    _record(relative, line_number, "iso_text", match.group(0), text)
                )
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if not (isinstance(function, ast.Attribute) and function.attr == "date"):
                continue
            try:
                year, month, day = [
                    ast.literal_eval(argument) for argument in node.args[:3]
                ]
            except (ValueError, TypeError, SyntaxError):
                continue
            if not all(isinstance(value, int) for value in (year, month, day)):
                continue
            value = "%04d-%02d-%02d" % (year, month, day)
            rows.append(
                _record(
                    relative,
                    node.lineno,
                    "date_constructor",
                    value,
                    lines[node.lineno - 1],
                )
            )
    return sorted(
        rows,
        key=lambda row: (
            row["file"], row["line"], row["literal_kind"], row["value"]
        ),
    )


def _record(relative, line, literal_kind, value, source_line):
    classification = _classification(relative, line, value)
    controls = classification in {
        "information_set_boundary",
        "coverage_cutover_boundary",
        "evaluation_window_boundary",
        "grading_target_boundary",
        "external_calendar_fact",
        "unsupported_display_claim",
    }
    return {
        "authority": AUTHORITY.get(classification, ""),
        "classification": classification,
        "controls_model_output": controls,
        "file": relative,
        "line": line,
        "literal_kind": literal_kind,
        "provenance": PROVENANCE_CONTROLLING if controls else PROVENANCE_DOCUMENTARY,
        "source_line_sha256": hashlib.sha256(
            source_line.strip().encode("utf-8")
        ).hexdigest(),
        "value": value,
    }


def build_document():
    records = _records()
    counts = {}
    provenance_counts = {}
    for row in records:
        name = row["classification"]
        counts[name] = counts.get(name, 0) + 1
        prov = row["provenance"]
        provenance_counts[prov] = provenance_counts.get(prov, 0) + 1
    transitive = []
    for row in records:
        if not row["controls_model_output"]:
            continue
        transitive.append({
            "key": "%s::%d::%s" % (row["file"], row["line"], row["value"]),
            "classification": row["classification"],
            "provenance": row["provenance"],
            "transitively_retires": TRANSITIVE_DEPENDENTS.get(
                row["classification"], []
            ),
        })
    return {
        "classification_counts": dict(sorted(counts.items())),
        "invariant": (
            "Every ISO date text and literal datetime.date constructor on the "
            "declared science path is classified and carries a provenance. New or "
            "moved literals fail the suite; a controlling boundary is retired and "
            "may gain NO new citation."
        ),
        "provenance_counts": dict(sorted(provenance_counts.items())),
        "record_count": len(records),
        "records": records,
        "schema_version": "recession-monitor-v2.date-literal-registry.v1",
        "science_files": list(SCIENCE_FILES),
        "scope": "bh.params.SCIENCE_FILES; comments and docstrings included",
        "transitive_retirement": transitive,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = (json.dumps(build_document(), indent=2, sort_keys=True) + "\n").encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != data:
            raise SystemExit("date literal registry is stale; rebuild it")
        return
    OUTPUT.write_bytes(data)


if __name__ == "__main__":
    main()
