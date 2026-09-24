#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.gap_registry import build_registry, summarize_registry  # noqa: E402


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_planned(path: Path):
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        return value
    for key in ("sources", "planned_sources", "rows"):
        if isinstance(value.get(key), list):
            return value[key]
    raise ValueError("planned source file has no recognized row list")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--planned-sources", type=Path)
    parser.add_argument("--omit-strict-realtime", action="store_true")
    args = parser.parse_args()
    planned = read_planned(args.planned_sources) if args.planned_sources else None
    registry = build_registry(
        read_csv(args.catalog_root / "metric_catalog.csv"),
        read_csv(args.catalog_root / "local_series_inventory.csv"),
        read_csv(args.catalog_root / "dataset_catalog.csv"),
        read_csv(args.catalog_root / "external_source_registry.csv"),
        include_strict_realtime=not args.omit_strict_realtime,
        include_known_reservations=planned is None,
        planned_rows=planned,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summarize_registry(registry), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
