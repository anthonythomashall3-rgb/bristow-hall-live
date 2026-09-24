#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.collector import collect_recipes, recipe_from_mapping  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("recipes", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--include-disabled", action="store_true")
    args = parser.parse_args()
    doc = json.loads(args.recipes.read_text(encoding="utf-8"))
    rows = doc if isinstance(doc, list) else doc.get("recipes", [])
    selected = [row for row in rows if args.include_disabled or row.get("enabled", True)]
    receipts = collect_recipes([recipe_from_mapping(row) for row in selected], args.output_root, max_workers=args.workers)
    print(json.dumps({"count": len(receipts), "success": sum(r["status"] == "SUCCESS" for r in receipts), "failed": sum(r["status"] == "FAILED" for r in receipts)}, indent=2))
    if any(row["status"] != "SUCCESS" for row in receipts):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
