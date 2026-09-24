#!/usr/bin/env python3
"""Reproduce the frozen live-nowcast constants from the pinned information set.

The production module must not refit at runtime.  This offline harness instead
replays the original fit code against the immutable local archive plus the
publisher vintage of NFCI that was available when the constants were frozen.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HARNESS = REPO / "method_source" / "nowcast_harness.py"
LIVE = REPO / "method_source" / "nowcast_live.py"
MANIFEST = HERE / "reproduction_manifest.v1.json"
DEFAULT_ARCHIVE = REPO / "data_archive" / "current_revised_and_spatial"

BRIDGE_NAMES = (
    "B_CMRMT",
    "B_INDPRO",
    "B_PHILLY",
    "B_HOUST",
    "B_W875",
    "B_UNRATE",
)
REVISION_NAMES = ("INDPRO", "CMRMT", "W875", "NFCI")
VINTAGE_SERIES = {
    "INDPRO": "INDPRO",
    "CMRMT": "CMRMTSPL",
    "W875": "W875RX1",
    "NFCI": "NFCI",
}
CURRENT_SERIES = (
    "ICSA",
    "IURSA",
    "SAHMREALTIME",
    "UNRATE",
    "INDPRO",
    "CMRMTSPL",
    "TCU",
    "GACDFSA066MSFRBPHI",
    "NASDAQCOM",
    "BAA",
    "AAA",
    "BAA10Y",
    "VIXCLS",
    "HOUST",
    "PERMIT",
    "UMCSENT",
    "W875RX1",
    "GS10",
    "GS1",
    "USRECD",
    "RRSFS",
    "MORTGAGE30US",
    "PAYEMS",
    "CCSA",
    "DBAA",
    "DAAA",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _archive_paths(root: Path):
    paths = [root / (series_id + ".csv") for series_id in CURRENT_SERIES]
    for series_id in REVISION_NAMES:
        archive_id = VINTAGE_SERIES[series_id]
        paths.extend(sorted((root / "vintages").glob(archive_id + "_*.csv")))
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _archive_digest(root: Path):
    paths = _archive_paths(root)
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing reproduction inputs: " + ", ".join(missing))
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return len(paths), digest.hexdigest()


def _literal_assignments(path: Path):
    tree = ast.parse(path.read_text(), filename=str(path))
    wanted = set(BRIDGE_NAMES) | {"BHAT_END", "Z_CLIP"}
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in wanted:
            found[target.id] = ast.literal_eval(node.value)
    missing = wanted - set(found)
    if missing:
        raise ValueError("frozen assignments not found: " + ", ".join(sorted(missing)))
    return found


def _execute_fit(archive_root: Path, manifest):
    information_set = manifest["information_set_end"]
    snapshot = HERE / manifest["inputs"]["nfci_final_vintage"]["path"]
    source = HARNESS.read_text()
    end_line = (
        'END = max(max(S[k]) for k in '
        '("ICSA","NASDAQCOM","VIXCLS","NFCI","BAA10Y"))'
    )
    replacement = "END = dt.date.fromisoformat(%r)" % information_set
    if source.count(end_line) != 1:
        raise ValueError("nowcast harness END expression changed")
    source = source.replace(end_line, replacement)
    last_fit = "B_UNRATE = fit_unrate()"
    if last_fit not in source:
        raise ValueError("nowcast harness fit boundary changed")
    source = source[: source.index(last_fit) + len(last_fit)] + "\n"

    with tempfile.TemporaryDirectory(prefix="rmv2-nowcast-reproduction-") as tmp:
        root = Path(tmp)
        raw = root / "raw"
        raw.mkdir()
        for series_id in CURRENT_SERIES:
            (raw / (series_id + ".csv")).symlink_to(
                archive_root / (series_id + ".csv")
            )
        (raw / "NFCI.csv").symlink_to(snapshot)
        (raw / "vintages").symlink_to(archive_root / "vintages")
        synthetic_file = root / "nowcast_harness.py"
        namespace = {"__file__": str(synthetic_file), "__name__": "__reproduce__"}
        exec(compile(source, str(synthetic_file), "exec"), namespace)

    actual = {name: [float(value) for value in namespace[name]] for name in BRIDGE_NAMES}
    actual["BHAT_END"] = {
        name: float(namespace["BHAT"][name][-1]) for name in REVISION_NAMES
    }
    actual["Z_CLIP"] = float(namespace["Z_CLIP"])
    return actual, namespace["FIT_END"].isoformat(), namespace["END"].isoformat()


def reproduce(archive_root: Path):
    manifest = json.loads(MANIFEST.read_text())
    expected = _literal_assignments(LIVE)
    expected = {
        **{name: [float(value) for value in expected[name]] for name in BRIDGE_NAMES},
        "BHAT_END": {name: float(expected["BHAT_END"][name]) for name in REVISION_NAMES},
        "Z_CLIP": float(expected["Z_CLIP"]),
    }
    count, archive_sha = _archive_digest(archive_root)
    pins = manifest["inputs"]
    snapshot = HERE / pins["nfci_final_vintage"]["path"]
    pin_checks = {
        "archive_file_count": count == pins["archive_bundle"]["file_count"],
        "archive_bundle_sha256": archive_sha == pins["archive_bundle"]["sha256"],
        "harness_sha256": _sha256(HARNESS) == pins["nowcast_harness"]["sha256"],
        "nfci_vintage_sha256": _sha256(snapshot)
        == pins["nfci_final_vintage"]["sha256"],
    }
    actual, fit_end, information_set = _execute_fit(archive_root, manifest)
    exact = actual == expected
    pins_match = all(pin_checks.values())
    return {
        "schema_version": "recession-monitor-v2.nowcast-reproduction-report.v1",
        "status": "exact_match" if exact and pins_match else "mismatch",
        "fit_end": fit_end,
        "information_set_end": information_set,
        "input_pins_match": pins_match,
        "input_pin_checks": pin_checks,
        "expected": expected,
        "actual": actual,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    report = reproduce(args.archive_root.resolve())
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "exact_match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
