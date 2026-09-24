#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.repair_recipes import build_fred_repair_recipes  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("gap_registry", type=Path)
    parser.add_argument("metric_catalog", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    registry = json.loads(args.gap_registry.read_text(encoding="utf-8"))
    with args.metric_catalog.open(newline="", encoding="utf-8-sig") as handle:
        metrics = list(csv.DictReader(handle))
    doc = build_fred_repair_recipes(registry, metrics)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote %d candidate repair recipes" % len(doc["recipes"]))


if __name__ == "__main__":
    main()
