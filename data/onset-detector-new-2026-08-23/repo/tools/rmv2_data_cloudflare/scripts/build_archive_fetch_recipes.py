#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.archive_fetch_recipes import build_archive_fetch_recipes  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert archive discovery output into candidate-only fetch recipes"
    )
    parser.add_argument("discovery", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    discovery = json.loads(args.discovery.read_text(encoding="utf-8"))
    document = build_archive_fetch_recipes(discovery)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"recipe_count": document["recipe_count"]}, indent=2))


if __name__ == "__main__":
    main()
