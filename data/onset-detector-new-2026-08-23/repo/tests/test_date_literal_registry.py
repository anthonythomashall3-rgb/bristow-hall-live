import ast
import json
import re
from pathlib import Path

from bh.params import SCIENCE_FILES


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "model_authority/parameters/date_literal_registry.v1.json"
ISO_DATE = re.compile(r"(?<!\d)(?:19|20)\d{2}-\d{2}-\d{2}(?!\d)")


def _literal_keys():
    keys = set()
    for relative in SCIENCE_FILES:
        path = ROOT / relative
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        for line_number, line in enumerate(lines, 1):
            for match in ISO_DATE.finditer(line):
                keys.add((relative, line_number, "iso_text", match.group(0)))
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
            if all(isinstance(value, int) for value in (year, month, day)):
                keys.add(
                    (
                        relative,
                        node.lineno,
                        "date_constructor",
                        f"{year:04d}-{month:02d}-{day:02d}",
                    )
                )
    return keys


def test_every_science_date_literal_is_classified_and_registered():
    document = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records = document["records"]
    registered = {
        (row["file"], row["line"], row["literal_kind"], row["value"])
        for row in records
    }
    assert registered == _literal_keys()
    assert len(records) == document["record_count"]
    assert all(row["classification"] != "UNCLASSIFIED" for row in records)
    assert all(row["authority"] for row in records)


def test_every_record_carries_provenance_and_controllers_are_retired():
    # B-GUARD-GAP-EXCL: every date literal now carries provenance; a boundary
    # that controls model output is retired, a documentary fact is not.
    document = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records = document["records"]
    assert all(r["provenance"] in {"retired", "documentary"} for r in records)
    for r in records:
        expected = "retired" if r["controls_model_output"] else "documentary"
        assert r["provenance"] == expected
    assert document["provenance_counts"] == {"documentary": 19, "retired": 73}


def test_information_boundaries_are_explicit_and_no_display_fabrication_remains():
    records = json.loads(REGISTRY.read_text(encoding="utf-8"))["records"]
    boundary_classes = {
        "information_set_boundary",
        "coverage_cutover_boundary",
        "evaluation_window_boundary",
        "grading_target_boundary",
    }
    assert sum(row["classification"] in boundary_classes for row in records) >= 20
    unsupported = [
        row for row in records
        if row["classification"] == "unsupported_display_claim"
    ]
    assert unsupported == []
